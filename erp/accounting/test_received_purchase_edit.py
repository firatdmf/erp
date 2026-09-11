# to run this test, use the command:
# python manage.py test accounting.test_received_purchase_edit

"""A received purchase is edited with the same form as a draft order, and
all of it can be corrected.

The form reloads the purchase as its own payload, with the id of every line
and roll the purchase already has; these tests post that payload back the
way the page does, changed one thing at a time. What stays refused is what
an order depends on: a reserved roll can't be removed or become another
variant."""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import (CurrentAccount, Invoice, Payment,
                                        PaymentAllocation)
from marketing.models import Product, ProductCategory
from operating.models import (Order, OrderItem, OrderStockReservation,
                              Warehouse, WarehouseProduct, WarehouseProductItem)


class ReceivedPurchaseEditTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.karven = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.admin = get_user_model().objects.create_superuser(
            username="received_edit", password="pw", email="r@e.t")
        self.client.force_login(self.admin)

        order = self.client.post(
            reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
            data=json.dumps({
                "warehouse_id": self.wh.pk, "current_account_id": self.karven.pk,
                "unit": "mt", "date": "2026-08-21", "delivery_date": "2026-09-01",
                "notes": "first note",
                "products": [{
                    "main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                    "has_variants": True,
                    "variants": [{"name": "G07", "sku": "K24644.G07", "price": "3.50",
                                  "currency": "USD",
                                  "tops": [{"qty": 30, "barcode": "KRV-A"},
                                           {"qty": 20, "barcode": "KRV-B"}]}],
                }],
            }), content_type="application/json")
        self.invoice_id = order.json()["invoice_id"]
        confirm = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.invoice_id]))
        self.assertTrue(confirm.json()["success"], confirm.json())

    # ── helpers ─────────────────────────────────────────────────────
    def _invoice(self):
        return Invoice.objects.get(pk=self.invoice_id)

    def _roll(self, barcode):
        return WarehouseProductItem.objects.get(barcode=barcode)

    def _edit_url(self, warehouse=None):
        return reverse("operating:warehouse_purchase_edit",
                       args=[(warehouse or self.wh).pk, self.invoice_id])

    def _form(self):
        """What the page posts when nothing has been touched: the loaded
        purchase, plus the header fields npOrderPayload adds."""
        loaded = self.client.get(self._edit_url(),
                                 headers={"x-requested-with": "XMLHttpRequest"}).json()
        self.assertTrue(loaded["success"], loaded)
        inv = self._invoice()
        return {
            "warehouse_id": self.wh.pk,
            "current_account_id": loaded["current_account_id"],
            "unit": loaded["unit"],
            "date": inv.date.isoformat(),
            "delivery_date": inv.delivery_date.isoformat() if inv.delivery_date else "",
            "notes": inv.notes,
            "products": loaded["products"],
        }

    def _variant(self, form, card=0, row=0):
        return form["products"][card]["variants"][row]

    def _save(self, form, warehouse=None):
        return self.client.post(self._edit_url(warehouse), data=json.dumps(form),
                                content_type="application/json")

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def _reserve(self, barcode, qty, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        roll = self._roll(barcode)
        product = Product.objects.create(
            title="Order product", sku=f"ORD-{barcode}", price=10,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        order = Order.objects.create(order_number=f"DK-{barcode}", order_status="pending")
        item = OrderItem.objects.create(order=order, product=product, quantity=qty, price=10)
        return OrderStockReservation.objects.create(
            order=order, order_item=item, stock_item=roll,
            warehouse_product=roll.product, quantity=Decimal(qty))

    # ── Loading ─────────────────────────────────────────────────────
    def test_it_loads_as_the_forms_own_payload(self):
        form = self._form()
        card = form["products"][0]
        self.assertEqual(card["main_product"]["mode"], "existing")
        self.assertEqual(card["main_product"]["sku"], "K24644")
        v = card["variants"][0]
        self.assertEqual((v["name"], v["sku"], v["price"]), ("G07", "K24644.G07", "3.5"))
        self.assertEqual([t["qty"] for t in v["tops"]], ["30", "20"])
        self.assertTrue(all(t["stock_item_id"] for t in v["tops"]))

    def test_the_page_opens_with_nothing_locked(self):
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[self.invoice_id]))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        for field in ("npWarehouse", "npOrderDate", "npDeliveryDate", "npUnit"):
            self.assertNotRegex(body, rf'id="{field}"[^>]*disabled')
        self.assertContains(r, 'value="2026-08-21"')    # its own date, not today's

    # ── Nothing changed ─────────────────────────────────────────────
    def test_saving_it_untouched_changes_nothing(self):
        before = self._invoice()
        rolls_before = sorted(WarehouseProductItem.objects.values_list(
            "pk", "barcode", "quantity", "product_id", "purchase_invoice_item_id"))
        items_before = list(before.items.values_list("pk", "description", "quantity", "unit_price"))

        r = self._save(self._form())
        self.assertEqual(r.status_code, 200, r.content)

        after = self._invoice()
        self.assertEqual(sorted(WarehouseProductItem.objects.values_list(
            "pk", "barcode", "quantity", "product_id", "purchase_invoice_item_id")), rolls_before)
        self.assertEqual(list(after.items.values_list("pk", "description", "quantity", "unit_price")),
                         items_before)
        self.assertEqual((after.number, after.total, after.due_date),
                         (before.number, before.total, before.due_date))
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(WarehouseProduct.objects.count(), 1)

    # ── The document ────────────────────────────────────────────────
    def test_dates_and_notes(self):
        form = self._form()
        form.update(date="2026-08-25", delivery_date="2026-09-10", notes="arrived damaged")
        self.assertEqual(self._save(form).status_code, 200)
        inv = self._invoice()
        self.assertEqual(str(inv.date), "2026-08-25")
        self.assertEqual(str(inv.delivery_date), "2026-09-10")
        self.assertEqual(inv.notes, "arrived damaged")
        self.assertEqual(str(inv.due_date), "2026-09-24")              # 30-day term follows the date
        self.assertEqual(str(inv.posted_movement.date), "2026-08-25")

    def test_moving_it_to_another_account_moves_the_debt(self):
        other = CurrentAccount.objects.create(
            book=self.book, code="C-MRK", name="Markiss", type="customer",
            default_currency=self.usd)
        form = self._form()
        form["current_account_id"] = other.pk
        r = self._save(form)
        self.assertEqual(r.status_code, 200, r.content)

        inv = self._invoice()
        self.assertEqual(inv.current_account, other)
        self.assertEqual(inv.posted_movement.current_account, other)
        self.karven.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.karven.cached_balance, Decimal("0.00"))
        self.assertEqual(other.cached_balance, Decimal("-175.00"))     # 50 m × 3.50
        self.assertEqual(other.type, "both")                          # bought from, now

    def test_an_account_in_another_book_takes_the_invoice_there(self):
        ergene = Book.objects.create(name="Ergene Fabric")
        other = CurrentAccount.objects.create(
            book=ergene, code="C-ERG", name="Ergene Mill", type="supplier",
            default_currency=self.usd)
        form = self._form()
        form["current_account_id"] = other.pk
        self.assertEqual(self._save(form).status_code, 200)
        inv = self._invoice()
        self.assertEqual(inv.book, ergene)
        self.assertEqual(inv.posted_movement.book, ergene)
        # Numbered in the book it now belongs to.
        from accounting.models_accounts import CurrentAccountSettings
        self.assertEqual(CurrentAccountSettings.for_book(ergene).next_invoice_seq, 2)

    def test_the_account_stays_put_once_payments_are_allocated(self):
        other = CurrentAccount.objects.create(
            book=self.book, code="C-MRK", name="Markiss", type="supplier",
            default_currency=self.usd)
        payment = Payment.objects.create(
            book=self.book, current_account=self.karven, type="payment",
            date="2026-08-30", amount=Decimal("50"), currency=self.usd, number="PAY-T-1")
        PaymentAllocation.objects.create(payment=payment, invoice=self._invoice(),
                                         amount=Decimal("50"))
        form = self._form()
        form["current_account_id"] = other.pk
        r = self._save(form)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._invoice().current_account, self.karven)

    # ── Lines and prices ────────────────────────────────────────────
    def test_a_corrected_price_is_what_was_paid(self):
        form = self._form()
        self._variant(form)["price"] = "4"
        self.assertEqual(self._save(form).status_code, 200)

        inv = self._invoice()
        self.assertEqual(inv.total, Decimal("200.00"))
        self.assertEqual(inv.posted_movement.amount, Decimal("-200.00"))
        self.karven.refresh_from_db()
        self.assertEqual(self.karven.cached_balance, Decimal("-200.00"))
        for roll in WarehouseProductItem.objects.all():
            self.assertEqual(roll.unit_cost_base, Decimal("4"))
        self.assertEqual(WarehouseProduct.objects.get().purchase_price, Decimal("4"))

    def test_renaming_a_variant_renames_it(self):
        form = self._form()
        self._variant(form)["name"] = "G07 Krem"
        self.assertEqual(self._save(form).status_code, 200)
        wp = WarehouseProduct.objects.get()
        self.assertEqual(wp.name, "K24644 G07 Krem")
        self.assertEqual(self._invoice().items.get().description, "K24644 G07 Krem")
        self.assertEqual(WarehouseProductItem.objects.filter(product=wp).count(), 2)

    def test_a_different_variant_takes_the_rolls_with_it(self):
        form = self._form()
        v = self._variant(form)
        v["name"], v["sku"] = "G08", "K24644.G08"
        r = self._save(form)
        self.assertEqual(r.status_code, 200, r.content)

        old = WarehouseProduct.objects.get(sku="K24644.G07")
        new = WarehouseProduct.objects.get(sku="K24644.G08")
        self.assertEqual(old.quantity, Decimal("0"))
        self.assertEqual(new.quantity, Decimal("50.00"))
        self.assertEqual(self._roll("KRV-A").product, new)
        line = self._invoice().items.get()
        self.assertEqual(line.variant, new.catalog_variant)
        self.assertIsNotNone(new.catalog_variant)

    def test_a_reserved_roll_cannot_become_another_variant(self):
        self._reserve("KRV-A", "10")
        form = self._form()
        v = self._variant(form)
        v["name"], v["sku"] = "G08", "K24644.G08"
        r = self._save(form)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["blocked"][0]["barcode"], "KRV-A")
        self.assertEqual(self._roll("KRV-A").product.sku, "K24644.G07")
        self.assertFalse(WarehouseProduct.objects.filter(sku="K24644.G08").exists())

    def test_the_unit(self):
        form = self._form()
        form["unit"] = "piece"
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._invoice().items.get().unit, "piece")
        # Every roll on it came in on this purchase, so the product follows.
        self.assertEqual(WarehouseProduct.objects.get().unit, "piece")

    # ── Rolls ───────────────────────────────────────────────────────
    def test_a_roll_can_be_re_measured(self):
        form = self._form()
        self._variant(form)["tops"][0]["qty"] = "28.5"
        self.assertEqual(self._save(form).status_code, 200)
        roll = self._roll("KRV-A")
        self.assertEqual((roll.quantity, roll.quantity_remaining), (Decimal("28.50"), Decimal("28.50")))
        self.assertEqual(WarehouseProduct.objects.get().quantity, Decimal("48.50"))
        line = self._invoice().items.get()
        self.assertEqual(line.quantity, Decimal("48.50"))
        self.assertEqual(self._invoice().total, Decimal("169.75"))

    def test_shortening_a_reserved_roll_trims_the_hold_and_says_so(self):
        hold = self._reserve("KRV-B", "20")
        form = self._form()
        self._variant(form)["tops"][1]["qty"] = "18"
        r = self._save(form)
        self.assertEqual(r.status_code, 200, r.content)
        hold.refresh_from_db()
        self.assertEqual(hold.quantity, Decimal("18.00"))
        self.assertEqual(r.json()["reservations_trimmed"][0]["now"], 18.0)

    def test_a_roll_cannot_be_shorter_than_what_went_out(self):
        roll = self._roll("KRV-A")
        roll.quantity_remaining = Decimal("5")       # 25 m already shipped
        roll.status = "partial"
        roll.save()
        form = self._form()
        self._variant(form)["tops"][0]["qty"] = "20"
        form["notes"] = "must not stick"
        r = self._save(form)
        self.assertEqual(r.status_code, 422)     # a roll that went out is locked outright
        self.assertEqual(self._roll("KRV-A").quantity, Decimal("30.00"))
        self.assertEqual(self._invoice().notes, "first note")    # all or nothing

    def test_a_roll_can_be_relabelled_but_not_onto_a_taken_code(self):
        other_wp = WarehouseProduct.objects.create(warehouse=self.wh, name="Other", sku="OTH")
        WarehouseProductItem.objects.create(product=other_wp, quantity=5, barcode="TAKEN-1")

        form = self._form()
        self._variant(form)["tops"][0]["barcode"] = "TAKEN-1"
        self.assertEqual(self._save(form).status_code, 400)

        form = self._form()
        self._variant(form)["tops"][0]["barcode"] = "KRV-A2"
        self.assertEqual(self._save(form).status_code, 200)
        self.assertTrue(WarehouseProductItem.objects.filter(barcode="KRV-A2").exists())

    def test_a_removed_roll_leaves_stock(self):
        form = self._form()
        self._variant(form)["tops"].pop(1)
        self.assertEqual(self._save(form).status_code, 200)
        self.assertFalse(WarehouseProductItem.objects.filter(barcode="KRV-B").exists())
        self.assertEqual(WarehouseProduct.objects.get().quantity, Decimal("30.00"))
        self.assertEqual(self._invoice().total, Decimal("105.00"))

    def test_a_reserved_roll_cannot_be_removed(self):
        self._reserve("KRV-B", "5")
        form = self._form()
        self._variant(form)["tops"].pop(1)
        r = self._save(form)
        self.assertEqual(r.status_code, 422)
        self.assertTrue(WarehouseProductItem.objects.filter(barcode="KRV-B").exists())

    def test_dropping_a_whole_line(self):
        form = self._form()
        form["products"][0]["variants"].append({
            "name": "G09", "sku": "K24644.G09", "price": "3", "currency": "USD",
            "tops": [{"qty": 10, "barcode": ""}]})
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._invoice().items.count(), 2)

        form = self._form()
        form["products"][0]["variants"].pop(0)          # G07 and both its rolls
        self.assertEqual(self._save(form).status_code, 200)
        inv = self._invoice()
        self.assertEqual(list(inv.items.values_list("description", flat=True)), ["K24644 G09"])
        self.assertEqual(inv.total, Decimal("30.00"))
        self.assertFalse(WarehouseProductItem.objects.filter(barcode__in=["KRV-A", "KRV-B"]).exists())

    # ── Adding ──────────────────────────────────────────────────────
    def test_rolls_variants_and_products_can_be_added(self):
        form = self._form()
        self._variant(form)["tops"].append({"qty": 12, "barcode": ""})
        form["products"].append({
            "main_product": {"mode": "new", "name": "N1464T", "sku": "N1464T"},
            "has_variants": False,
            "variants": [{"name": "", "sku": "", "price": "2", "currency": "USD",
                          "tops": [{"qty": 40, "barcode": "N-1"}]}],
        })
        r = self._save(form)
        self.assertEqual(r.status_code, 200, r.content)

        inv = self._invoice()
        self.assertEqual(inv.items.count(), 2)
        self.assertEqual(inv.total, Decimal("297.00"))         # 62 × 3.50 + 40 × 2
        self.assertEqual(Product.objects.get(sku="N1464T").title, "N1464T")
        new_roll = WarehouseProductItem.objects.get(barcode="N-1")
        self.assertEqual(new_roll.purchase_invoice_item.invoice_id, self.invoice_id)
        self.assertEqual(new_roll.product.sku, "N1464T")
        self.assertEqual(WarehouseProductItem.objects.filter(
            purchase_invoice_item__invoice_id=self.invoice_id).count(), 4)

        # ...and the simple product reloads as one.
        again = self._form()
        self.assertFalse(again["products"][1]["has_variants"])
        self.assertEqual(self._save(again).status_code, 200)
        self.assertEqual(self._invoice().total, Decimal("297.00"))

    # ── Warehouse ───────────────────────────────────────────────────
    def test_another_warehouse_of_the_same_book_takes_the_rolls(self):
        hold = self._reserve("KRV-A", "10")
        depot = Warehouse.objects.create(name="Depo 2", accounting_book=self.book)
        form = self._form()
        form["warehouse_id"] = depot.pk
        r = self._save(form, warehouse=depot)
        self.assertEqual(r.status_code, 200, r.content)

        moved = WarehouseProduct.objects.get(warehouse=depot, sku="K24644.G07")
        self.assertEqual(moved.quantity, Decimal("50.00"))
        self.assertEqual(WarehouseProduct.objects.get(warehouse=self.wh).quantity, Decimal("0"))
        hold.refresh_from_db()
        self.assertEqual(hold.warehouse_product, moved)             # the hold travels
        self.assertEqual(self._invoice().intake_warehouse, depot)

    def test_never_into_another_books_warehouse(self):
        depot = Warehouse.objects.create(
            name="Ergene", accounting_book=Book.objects.create(name="Ergene Fabric"))
        form = self._form()
        form["warehouse_id"] = depot.pk
        r = self._save(form, warehouse=depot)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.json().get("cross_book"))
        self.assertEqual(self._roll("KRV-A").product.warehouse, self.wh)

    # ── What it is not ──────────────────────────────────────────────
    def test_an_order_is_edited_as_an_order(self):
        draft = self.client.post(
            reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
            data=json.dumps({
                "warehouse_id": self.wh.pk, "current_account_id": self.karven.pk, "unit": "mt",
                "products": [{"main_product": {"mode": "new", "name": "X1"},
                              "variants": [{"name": "A", "price": "1", "tops": [{"qty": 1}]}]}],
            }), content_type="application/json").json()["invoice_id"]
        r = self.client.post(
            reverse("operating:warehouse_purchase_edit", args=[self.wh.pk, draft]),
            data=json.dumps(self._form()), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_it_needs_the_receiving_permission(self):
        plain = get_user_model().objects.create_user(username="plain_edit", password="pw")
        form = self._form()
        self.client.force_login(plain)
        self.assertEqual(self._save(form).status_code, 403)
