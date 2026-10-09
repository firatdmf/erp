# to run this test, use the command:
# python manage.py test accounting.tests.test_purchase_for_order

"""A purchase bought for a customer.

A client asks for something the shelves don't have. The purchase is written
with the customer and a sale price per variant, and saving it creates the
customer's order too. Receiving the purchase reserves the arriving rolls for
that order — up to what it still needs — so they can't be packed into
another one first.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import (
    CurrentAccount, CurrentAccountMovement, Invoice, PurchaseChange,
)
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import (
    Order, OrderItem, OrderStockReservation, Warehouse, WarehouseProduct,
    WarehouseProductItem,
)


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class PurchaseForCustomerTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Ergene")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.other_wh = Warehouse.objects.create(name="Ergene depo",
                                                 accounting_book=self.other_book)
        self.customer = Contact.objects.create(name="Oleg Motuzenko")

        self.admin = get_user_model().objects.create_superuser(
            username="firat_po", password="pw", email="a@b.c")
        self.client.force_login(self.admin)

    def _plan(self, variants=None, customer=True, warehouse=None, product=None):
        main = ({"mode": "existing", "id": product.pk, "sku": product.sku}
                if product else {"mode": "new", "name": "K24644", "sku": "K24644"})
        return {
            "warehouse_id": (warehouse or self.wh).pk,
            "current_account_id": self.supplier.pk,
            "customer": ({"type": "contact", "pk": self.customer.pk} if customer else None),
            "unit": "mt",
            "date": "2026-09-17",
            "products": [{
                "main_product": main,
                "has_variants": True,
                "variants": variants if variants is not None else [self._variant()],
            }],
        }

    @staticmethod
    def _variant(name="G07", sku="K24644.G07", tops=(30, 25), sale="5.00"):
        return {"name": name, "sku": sku, "price": "3.50", "currency": "USD",
                "sale_price": sale,
                "tops": [{"qty": q, "barcode": ""} for q in tops]}

    def _save(self, plan, pk=None):
        url = (reverse("accounts:purchase_order_update", args=[pk]) if pk
               else reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}))
        return self.client.post(url, data=json.dumps(plan), content_type="application/json")

    def _confirm(self, inv_id):
        return self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))

    def _held(self, order):
        return list(OrderStockReservation.objects.filter(order=order)
                    .order_by("stock_item_id").values_list("quantity", flat=True))

    # ── Saving creates the customer's order ─────────────────────────
    def test_saving_creates_the_customers_order(self):
        r = self._save(self._plan())
        self.assertEqual(r.status_code, 200, r.content)
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        order = inv.for_order
        self.assertIsNotNone(order)
        self.assertEqual(order.contact, self.customer)
        self.assertEqual(order.order_status, "pending")
        self.assertEqual(order.current_account.book, self.wh.accounting_book)

        [line] = order.items.all()
        self.assertEqual(line.product_variant.variant_sku, "K24644.G07")
        self.assertEqual(line.quantity, Decimal("55.00"))       # 30 + 25
        self.assertEqual(line.price, Decimal("5.00"))

        # The product is in the catalog now; the stock and the debt are not.
        self.assertEqual(Product.objects.get().sku, "K24644")
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertIsNone(inv.posted_movement)
        # The saved plan names what was created, so receiving finds it.
        card = inv.intake_plan["products"][0]
        self.assertEqual(card["main_product"]["mode"], "existing")
        self.assertEqual(card["main_product"]["id"], line.product_id)

    def test_the_order_does_not_name_the_supplier(self):
        """The order prints for the customer, notes and all; who the goods
        were bought from is ours to know. The link is invoice.for_order."""
        r = self._save(self._plan())
        order = Invoice.objects.get(pk=r.json()["invoice_id"]).for_order
        self.assertFalse(order.notes)

    def test_an_auto_sku_is_fixed_at_save(self):
        r = self._save(self._plan(variants=[self._variant(sku="")]))
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        sku = inv.intake_plan["products"][0]["variants"][0]["sku"]
        self.assertTrue(sku)
        self.assertEqual(inv.for_order.items.get().product_variant.variant_sku, sku)

        self._confirm(inv.pk)
        self.assertEqual(ProductVariant.objects.count(), 1)
        self.assertEqual(WarehouseProduct.objects.get().sku, sku)

    def test_an_existing_product_can_be_bought_for_a_customer(self):
        product = Product.objects.create(title="Krep", sku="KRP1", featured=False)
        variant = ProductVariant.objects.create(product=product, variant_sku="KRP1.G07")
        r = self._save(self._plan(product=product,
                                  variants=[self._variant(sku="KRP1.G07")]))
        self.assertEqual(r.status_code, 200, r.content)
        order = Invoice.objects.get(pk=r.json()["invoice_id"]).for_order
        self.assertEqual(order.items.get().product_variant, variant)
        self.assertEqual(ProductVariant.objects.count(), 1)

    def test_a_purchase_for_stock_still_leaves_no_trace(self):
        r = self._save(self._plan(customer=False))
        self.assertIsNone(Invoice.objects.get(pk=r.json()["invoice_id"]).for_order)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Product.objects.exists())

    def test_an_unknown_customer_saves_nothing(self):
        plan = self._plan()
        plan["customer"]["pk"] = 999999
        r = self._save(plan)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Product.objects.exists())

    # ── The customer's price has to be stated ───────────────────────
    def test_a_row_without_a_sale_price_is_refused(self):
        """The sale price IS the order line's price, so a blank box opened
        the customer's order at 0.00 and said nothing about it."""
        r = self._save(self._plan(variants=[self._variant(sale="")]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("K24644 G07", r.json()["error"])      # it names the row
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Product.objects.exists())          # nor a catalog row

    def test_a_zero_sale_price_is_refused_too(self):
        r = self._save(self._plan(variants=[self._variant(sale="0")]))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_a_row_with_no_quantity_is_not_asked_for_one(self):
        """It is not going on the order, so it has nothing to be billed at."""
        r = self._save(self._plan(variants=[
            self._variant(),
            self._variant(name="G08", sku="K24644.G08", tops=(), sale=""),
        ]))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Order.objects.get().items.count(), 1)

    def test_a_purchase_for_stock_needs_no_sale_price(self):
        """Nobody is being billed — the rule is the customer order's."""
        r = self._save(self._plan(customer=False, variants=[self._variant(sale="")]))
        self.assertEqual(r.status_code, 200, r.content)

    def test_an_edit_that_blanks_the_price_leaves_the_order_as_it_was(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self._save(self._plan(variants=[self._variant(tops=(40,), sale="")],
                                  customer=False, product=Product.objects.get()),
                       pk=inv_id)
        self.assertEqual(r.status_code, 400)
        line = Order.objects.get().items.get()
        self.assertEqual(line.quantity, Decimal("55.00"))
        self.assertEqual(line.price, Decimal("5.00"))

    # ── Editing the draft keeps the order in step ───────────────────
    def test_editing_the_draft_updates_the_order(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        by_hand = OrderItem.objects.create(
            order=order, product=Product.objects.get(), quantity=Decimal("1"),
            price=Decimal("9"))

        # Reopened, the draft names the product it created as an existing one.
        plan = self._plan(variants=[self._variant(tops=(40,), sale="6.00")], customer=False,
                          product=Product.objects.get())
        r = self._save(plan, pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())

        self.assertEqual(Order.objects.count(), 1)
        lines = {it.product_variant.variant_sku if it.product_variant_id else None: it
                 for it in Order.objects.get().items.select_related("product_variant")}
        self.assertEqual(set(lines), {"K24644.G07", None})      # G08 dropped, hand line kept
        self.assertEqual(lines["K24644.G07"].quantity, Decimal("40.00"))
        self.assertEqual(lines["K24644.G07"].price, Decimal("6.00"))
        self.assertEqual(lines[None].pk, by_hand.pk)

    def test_an_order_being_packed_is_left_alone(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        Order.objects.update(order_status="packaging")
        r = self._save(self._plan(variants=[self._variant(tops=(5,))], customer=False,
                                  product=Product.objects.get()), pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(OrderItem.objects.get().quantity, Decimal("55.00"))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "already being packed")

    def test_moving_the_draft_to_another_books_warehouse_is_refused(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self._save(self._plan(warehouse=self.other_wh, customer=False), pk=inv_id)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=inv_id).intake_warehouse, self.wh)

    # ── Receiving holds the rolls ───────────────────────────────────
    def test_confirming_holds_the_rolls_for_the_order(self):
        inv_id = self._save(self._plan(variants=[self._variant(tops=(30, 25))])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        # The customer only wants 40 of the 55 coming in.
        order.items.update(quantity=Decimal("40"))

        r = self._confirm(inv_id)
        self.assertTrue(r.json()["success"], r.json())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "2 rolls reserved for order %s." % order.order_number)

        self.assertEqual(self._held(order), [Decimal("30.00"), Decimal("10.00")])
        # Same variant the order points at — nothing minted twice.
        self.assertEqual(ProductVariant.objects.count(), 1)
        # Held, not cut.
        self.assertEqual(
            sorted(WarehouseProductItem.objects.values_list("quantity_remaining", flat=True)),
            [Decimal("25.00"), Decimal("30.00")])
        # The debt is posted — for_order is not the sales `order` link.
        inv = Invoice.objects.get(pk=inv_id)
        self.assertIsNone(inv.order)
        self.assertIsNotNone(inv.posted_movement)

    def test_rolls_the_order_does_not_need_stay_free(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        OrderItem.objects.filter(order=order).update(outsourced_quantity=Decimal("55"))
        r = self._confirm(inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(self._held(order), [])
        self.assertTrue(any("Nothing was reserved" in w for w in r.json()["warnings"]))

    # ── Around it ───────────────────────────────────────────────────
    # ── The sale price is in the customer's currency ────────────────
    def _currency(self, customer_type, pk, warehouse=None):
        """The currency and account the endpoint names, which is what this
        screen asks it. It answers more than that now — a symbol, and
        whether it is the book's own currency, both for the order form's
        warning — so this picks out the two keys these tests are about."""
        r = self.client.get(
            reverse("operating:warehouse_customer_currency", args=[(warehouse or self.wh).pk]),
            {"type": customer_type, "pk": pk})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        return {"currency": d["currency"], "account": d["account"]}

    def test_a_customer_with_an_account_prices_in_its_currency(self):
        try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="₺")
        CurrentAccount.objects.create(book=self.book, code="C-OLG", name="Oleg",
                                      type="customer", contact=self.customer,
                                      default_currency=try_)
        self.assertEqual(self._currency("contact", self.customer.pk),
                         {"currency": "TRY", "account": "Oleg"})
        # In a book where they have no account yet, the one the order
        # would open is in the default currency.
        self.assertEqual(self._currency("contact", self.customer.pk, self.other_wh),
                         {"currency": "USD", "account": None})

    def test_a_contact_at_a_company_prices_in_the_companys_currency(self):
        """The order bills the company's account, not the person's."""
        from crm.models import Company
        eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        company = Company.objects.create(name="Motuzenko Ltd")
        self.customer.company = company
        self.customer.save()
        CurrentAccount.objects.create(book=self.book, code="C-MTZ", name="Motuzenko Ltd",
                                      type="customer", company=company, default_currency=eur)
        self.assertEqual(self._currency("contact", self.customer.pk)["currency"], "EUR")
        self.assertEqual(self._currency("company", company.pk)["currency"], "EUR")

    def test_an_unknown_customer_has_no_currency(self):
        r = self.client.get(reverse("operating:warehouse_customer_currency", args=[self.wh.pk]),
                            {"type": "contact", "pk": 999999})
        self.assertEqual(r.status_code, 404)

    def test_a_reopened_order_states_its_orders_currency(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertEqual(r.context["for_order_currency"], "USD")

    def test_the_order_page_lists_its_purchases(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertEqual(r.status_code, 200)
        [p] = r.context["supplier_purchases"]
        self.assertEqual(p.pk, inv_id)
        self.assertContains(r, "Awaiting delivery")

    def test_a_line_added_on_the_order_says_no_purchase_covers_it(self):
        """Nobody has been asked to supply it — without the chip that only
        shows up when the delivery arrives short."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        extra = OrderItem.objects.create(order=order, product=Product.objects.get(),
                                         quantity=Decimal("3"), price=Decimal("9"))
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        flagged = {it.pk: it.not_on_purchase for it in r.context["order_items_sorted"]}
        self.assertTrue(flagged.pop(extra.pk))
        self.assertFalse(any(flagged.values()))
        self.assertContains(r, "not on the purchase")

    def test_an_order_with_no_live_purchase_flags_nothing(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertFalse(any(it.not_on_purchase for it in r.context["order_items_sorted"]))
        self.assertNotContains(r, "not on the purchase")

    def test_the_form_reopens_with_the_customer(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["for_order"], Invoice.objects.get(pk=inv_id).for_order)
        self.assertContains(r, "Oleg Motuzenko")
        # Where the customer is changed: on the order, not here.
        self.assertContains(r, "change the customer on the order")
        self.assertEqual(r.context["intake_plan"]["products"][0]["variants"][0]["sale_price"],
                         "5.00")

    def test_cancelling_the_draft_leaves_an_order_being_packed_alone(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        # Being packed from stock: the packing floor owns it now.
        Order.objects.update(order_status="packaging")
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        self.assertEqual(order.order_status, "packaging")
        self.assertEqual(order.items.count(), 1)
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "is already being packed")

    # ── Both cancel confirmations say how far packing has got ────────
    # Cancelling either document reaches the other, and what happens
    # there turns on whether packing has started — so it is said before
    # anyone confirms, not after.

    def _cancel_warning(self, inv_id):
        """What the purchase page's cancel confirmation will say about the
        order — read off the context, since the page carries it inside a
        script string, escaped."""
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "const orderWarning")
        return page.context["cancel_order_warning"]

    def test_the_purchase_cancel_says_packing_has_not_started(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertEqual(
            self._cancel_warning(inv_id),
            "Order %s: packing has not started. All its lines come from this purchase, "
            "so the order is cancelled too." % order.order_number)
        # With a line of its own the order outlives the purchase.
        stock = Product.objects.create(title="Stock cloth", sku="STK0001", price=1)
        OrderItem.objects.create(order=order, product=stock, quantity=Decimal("10"), price=Decimal("2"))
        self.assertIn("Its 1 line(s) from this purchase are removed", self._cancel_warning(inv_id))

    def test_the_purchase_cancel_says_packing_has_started(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        Order.objects.update(order_status="packaging")
        self.assertEqual(
            self._cancel_warning(inv_id),
            "Order %s: packing HAS started (Packaging, 0 roll(s) held). The order is left "
            "as it is — check it after cancelling." % order.order_number)

    def test_a_cancelled_purchase_warns_about_no_order(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertEqual(self._cancel_warning(inv_id), "")

    def test_the_order_cancel_says_how_far_packing_has_got(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        inv = Invoice.objects.get(pk=inv_id)
        url = reverse("operating:order_detail", args=[inv.for_order.pk])
        page = self.client.get(url)
        self.assertContains(page, "Packing has not started on this order")
        self.assertContains(page, "Purchase %s (Karven) is cancelled with the order" % inv.number)
        Order.objects.update(order_status="packaging")
        page = self.client.get(url)
        self.assertContains(page, "Packing has started on this order (Packaging, 0 rolls held).")
        self.assertNotContains(page, "Packing has not started on this order")

    def test_an_order_with_no_purchase_gets_no_packing_warning(self):
        account = CurrentAccount.objects.create(
            book=self.book, code="C-OLEG", name="Oleg", type="customer",
            contact=self.customer, default_currency=self.usd)
        order = Order.objects.create(contact=self.customer, current_account=account)
        page = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertContains(page, 'id="odCancelModal"')
        self.assertNotContains(page, 'id="odx-packing"')

    # ── The customer's bill waits for the goods ──────────────────────
    # A purchase for a customer says what they will owe, not what they
    # owe: nothing has been sold until the supplier delivers. The order
    # cannot be completed before then, and its sale posts on completion.

    def _sale(self, order):
        return CurrentAccountMovement.objects.filter(movement_type="order_sale",
                                                     source_id=order.pk)

    def _complete(self, order):
        from operating.views_warehouse import apply_order_status_change
        order.refresh_from_db()
        return apply_order_status_change(order, "shipped", user=self.admin)

    def test_the_customer_is_not_billed_until_the_goods_arrive(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertFalse(self._sale(order).exists())
        self.assertEqual(order.current_account.cached_balance, 0)
        # Editing the order meanwhile doesn't sneak the bill in either.
        line = order.items.get()
        line.quantity = Decimal("40")
        line.save()
        self.assertFalse(self._sale(order).exists())

        self.assertTrue(self._confirm(inv_id).json()["success"])
        # In, but not sold: the order is still open.
        self.assertFalse(self._sale(order).exists())
        self.assertEqual(self._complete(order), (True, None))
        [sale] = self._sale(order)
        self.assertEqual(sale.amount, Decimal("200.00"))        # 40 × 5.00
        self.assertEqual(sale.current_account, order.current_account)

    def test_a_second_purchase_still_on_its_way_keeps_the_bill_waiting(self):
        first = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=first).for_order
        second = Invoice.objects.create(
            type="purchase", status="draft", for_order=order, series="PUR", number="2",
            current_account=self.supplier, book=self.book, currency=self.usd,
            date=order.order_date, due_date=order.order_date)
        self.assertTrue(self._confirm(first).json()["success"])
        self.assertEqual(self._complete(order), (False, "goods_not_received"))
        self.assertFalse(self._sale(order).exists())
        # Cancelling the straggler means nothing more is coming.
        r = self.client.post(reverse("accounts:purchase_cancel", args=[second.pk]))
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(self._complete(order), (True, None))
        self.assertTrue(self._sale(order).exists())

    def test_cancelling_the_only_draft_bills_what_else_the_order_holds(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        stock = Product.objects.create(title="Stock cloth", sku="STK0001", price=1)
        OrderItem.objects.create(order=order, product=stock, quantity=Decimal("10"), price=Decimal("2"))
        self.assertFalse(self._sale(order).exists())
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertEqual(self._complete(order), (True, None))
        # The purchased line went with the purchase; the stock line bills.
        [sale] = self._sale(order)
        self.assertEqual(sale.amount, Decimal("20.00"))         # 10 × 2.00

    # ── Nor can the order be completed ───────────────────────────────

    def test_the_order_cannot_be_completed_until_the_goods_arrive(self):
        from operating.views_warehouse import apply_order_status_change
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertEqual(apply_order_status_change(order, "shipped", user=self.admin),
                         (False, "goods_not_received"))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "pending")

        self.assertTrue(self._confirm(inv_id).json()["success"])
        self.assertEqual(apply_order_status_change(order, "shipped", user=self.admin),
                         (True, None))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "shipped")

    def test_the_order_page_refuses_to_complete_and_says_why(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        url = reverse("operating:order_detail", args=[order.pk])
        page = self.client.get(url)
        self.assertContains(page, 'id="od-complete-btn" class="ord-btn primary" data-status="shipped"\n                        disabled')
        self.assertContains(page, "can be completed once the goods")
        r = self.client.post(url, {"action": "update_status", "order_status": "shipped"}, follow=True)
        self.assertContains(r, "Receive the purchase first, or cancel it.")
        order.refresh_from_db()
        self.assertEqual(order.order_status, "pending")

    def test_the_order_page_says_the_bill_is_waiting(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        inv = Invoice.objects.get(pk=inv_id)
        url = reverse("operating:order_detail", args=[inv.for_order.pk])
        page = self.client.get(url)
        self.assertContains(page, "Not billed yet")
        self.assertContains(page, inv.number)
        self._confirm(inv_id)
        # Received, still open: still not billed.
        self.assertContains(self.client.get(url), "Not billed yet")
        self.assertEqual(self._complete(inv.for_order), (True, None))
        self.assertNotContains(self.client.get(url), "Not billed yet")

    # ── The order and the purchase move together ─────────────────────
    # A line changed or removed on the order changes the draft purchase;
    # a purchase cancelled takes its lines off the order; either document
    # cancelled cancels the other when nothing is left on it. Both logs
    # say what the other side did.

    def _purchase_log(self, inv_id):
        return list(PurchaseChange.objects.filter(invoice_id=inv_id).order_by("pk")
                    .values_list("action", "field", "origin", "old_value", "new_value"))

    def _order_log(self, order):
        return list(order.change_logs.order_by("pk").values_list("action", "field", "new_value"))

    @staticmethod
    def _tops(inv):
        return [Decimal(str(t["qty"])) for t in inv.intake_plan["products"][0]["variants"][0]["tops"]]

    def test_a_quantity_changed_on_the_order_changes_the_purchase(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        line = order.items.get()
        line.quantity, line.price = Decimal("40"), Decimal("6")
        line.save()

        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(self._tops(inv), [Decimal("30"), Decimal("10")])      # trimmed from the last roll
        self.assertEqual(Decimal(inv.intake_plan["products"][0]["variants"][0]["sale_price"]), 6)
        self.assertEqual(inv.total, Decimal("140.00"))                          # 40 × 3.50
        self.assertEqual(inv.items.get().quantity, Decimal("40.000"))
        self.assertIn(("item_updated", "quantity", "order", "55", "40"), self._purchase_log(inv_id))
        self.assertIn(("item_updated", "sale_price", "order", "5", "6"), self._purchase_log(inv_id))
        # Nothing bounced back onto the order.
        self.assertEqual(order.items.get().quantity, Decimal("40.00"))

    def test_more_on_the_order_adds_a_roll_to_the_purchase(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        line = Invoice.objects.get(pk=inv_id).for_order.items.get()
        line.quantity = Decimal("70")
        line.save()
        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(self._tops(inv), [Decimal("30"), Decimal("25"), Decimal("15")])
        self.assertEqual(inv.total, Decimal("245.00"))

    def test_a_line_removed_from_the_order_leaves_the_rest_on_the_purchase(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(20,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        order.items.get(product_variant__variant_sku="K24644.G08").delete()
        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.status, "draft")
        self.assertEqual([v["sku"] for v in inv.intake_plan["products"][0]["variants"]], ["K24644.G07"])
        self.assertEqual(inv.total, Decimal("192.50"))
        self.assertEqual([c for c in self._purchase_log(inv_id) if c[0] == "item_removed"][0][2], "order")

    def test_a_line_removed_from_the_order_cancels_a_purchase_left_empty(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        order.items.get().delete()
        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.status, "cancelled")
        # What it was for still reads on the cancelled purchase.
        self.assertEqual(len(inv.intake_plan["products"][0]["variants"]), 1)
        self.assertIn(("status", "status", "order", "draft", "cancelled"), self._purchase_log(inv_id))
        self.assertIn(("field", "purchase", "%s cancelled — nothing left on it to buy" % inv.number),
                      self._order_log(order))
        order.refresh_from_db()
        self.assertEqual(order.order_status, "pending")

    def test_cancelling_the_order_cancels_its_draft_purchase(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.post(reverse("operating:order_detail", args=[order.pk]),
                             {"action": "update_status", "order_status": "cancelled",
                              "cancel_reason": "Customer took stock instead"})
        self.assertEqual(r.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.order_status, "cancelled")
        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.status, "cancelled")
        self.assertIn(("status", "status", "order", "draft", "cancelled"), self._purchase_log(inv_id))
        self.assertIn(("field", "purchase", "%s cancelled with the order" % inv.number),
                      self._order_log(order))

    # ── A received purchase is out of the order's reach ──────────────
    # Once the goods are in, the purchase is a fact: the stock is on the
    # shelf and the supplier is owed for it, whatever becomes of the
    # customer's order. Cancelling the order, deleting it or rewriting
    # its lines releases the rolls it held and leaves everything else
    # about the purchase exactly as the receipt left it.

    def _received(self):
        """A purchase saved for the customer and received, with what it
        looks like at that moment."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.assertTrue(self._confirm(inv_id).json()["success"])
        return inv_id, self._purchase_facts(inv_id)

    def _purchase_facts(self, inv_id):
        inv = Invoice.objects.get(pk=inv_id)
        return {
            "status": inv.status,
            "total": inv.total,
            "plan": inv.intake_plan,
            "lines": list(inv.items.order_by("line_no")
                          .values_list("description", "quantity", "unit_price")),
            "debt": inv.posted_movement_id,
            "supplier_balance": CurrentAccount.objects.get(pk=self.supplier.pk).cached_balance,
            "rolls": sorted(WarehouseProductItem.objects
                            .filter(purchase_invoice_item__invoice_id=inv_id)
                            .values_list("barcode", "quantity", "quantity_remaining")),
            "log": self._purchase_log(inv_id),
        }

    def test_cancelling_the_order_leaves_a_received_purchase_alone(self):
        inv_id, before = self._received()
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertEqual(len(self._held(order)), 2)
        r = self.client.post(reverse("operating:order_detail", args=[order.pk]),
                             {"action": "update_status", "order_status": "cancelled",
                              "cancel_reason": "Customer changed their mind"})
        self.assertEqual(r.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.order_status, "cancelled")
        self.assertEqual(before["status"], "issued")
        self.assertEqual(self._purchase_facts(inv_id), before)
        self.assertEqual(Invoice.objects.get(pk=inv_id).for_order, order)
        # The rolls it held are free stock again — still on the shelf.
        self.assertEqual(self._held(order), [])
        self.assertEqual(len(before["rolls"]), 2)

    def test_a_purchase_whose_order_was_cancelled_is_edited_as_stock(self):
        """The form drops the customer and with it the sale-price boxes:
        there is nobody left to charge, so the purchase price can be
        corrected without one."""
        inv_id, _before = self._received()
        order = Invoice.objects.get(pk=inv_id).for_order
        url = reverse("accounts:goods_receipt_edit", args=[inv_id])
        self.assertEqual(self.client.get(url).context["for_order"], order)

        self.client.post(reverse("operating:order_detail", args=[order.pk]),
                         {"action": "update_status", "order_status": "cancelled",
                          "cancel_reason": "Customer changed their mind"})
        r = self.client.get(url)
        self.assertIsNone(r.context["for_order"])
        self.assertEqual(r.context["cancelled_order"], order)
        self.assertContains(r, "which was cancelled")
        # What puts the page in for-customer mode, and so asks for prices.
        self.assertContains(r, "const on = !!npCustomer || false;")
        # The link stays as the record of why the goods were bought.
        self.assertEqual(Invoice.objects.get(pk=inv_id).for_order, order)
        # And the purchase's own page says what became of that order.
        self.assertContains(
            self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id])),
            "The order was cancelled")

    def test_deleting_the_order_leaves_a_received_purchase_alone(self):
        inv_id, before = self._received()
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.post(reverse("operating:delete_order", args=[order.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(self._purchase_facts(inv_id), before)
        # Only the link goes, with the order it pointed at.
        self.assertIsNone(Invoice.objects.get(pk=inv_id).for_order)
        self.assertFalse(OrderStockReservation.objects.exists())

    # ── Deleting the order takes its draft purchases with it ─────────
    # Like cancelling: goods still on their way in for an order that no
    # longer exists are not wanted. The purchase's own log says the order
    # was deleted, since the order's log goes with the order.

    def test_deleting_the_order_cancels_its_draft_purchase(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        inv = Invoice.objects.get(pk=inv_id)
        order = inv.for_order
        r = self.client.post(reverse("operating:delete_order", args=[order.pk]), follow=True)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        inv.refresh_from_db()
        self.assertEqual(inv.status, "cancelled")
        self.assertIsNone(inv.for_order)
        self.assertIn(("status", "status", "order", "draft", "cancelled"), self._purchase_log(inv_id))
        self.assertIn(("field", "order", "order", None,
                       "Order %s deleted — this purchase was cancelled with it" % order.order_number),
                      self._purchase_log(inv_id))
        self.assertContains(r, "cancelled with it: %s" % inv.number)

    def test_bulk_deleting_orders_cancels_their_draft_purchases(self):
        first = self._save(self._plan()).json()["invoice_id"]
        second = self._save(self._plan(variants=[self._variant(name="G08", sku="K24644.G08")],
                                       product=Product.objects.get())).json()["invoice_id"]
        orders = [Invoice.objects.get(pk=pk).for_order.pk for pk in (first, second)]
        r = self.client.post(reverse("operating:bulk_delete_orders"), {"order_ids[]": orders})
        self.assertEqual(r.json()["deleted"], 2, r.json())
        self.assertEqual(r.json()["purchases_cancelled"],
                         [Invoice.objects.get(pk=pk).number for pk in (first, second)])
        self.assertEqual(set(Invoice.objects.filter(pk__in=[first, second])
                             .values_list("status", flat=True)), {"cancelled"})
        self.assertFalse(Order.objects.exists())

    def test_the_order_list_names_the_purchases_a_delete_would_cancel(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        inv = Invoice.objects.get(pk=inv_id)
        url = reverse("operating:order_list_scoped", args=[self.book.pk])
        self.assertContains(self.client.get(url), 'data-draft-purchases="%s"' % inv.number)
        self._confirm(inv_id)
        page = self.client.get(url)
        self.assertContains(page, 'data-draft-purchases=""')
        self.assertNotContains(page, 'data-draft-purchases="%s"' % inv.number)

    def test_editing_the_order_leaves_a_received_purchase_alone(self):
        inv_id, before = self._received()
        order = Invoice.objects.get(pk=inv_id).for_order
        OrderStockReservation.objects.filter(order=order).delete()
        line = order.items.get()
        line.quantity, line.price = Decimal("10"), Decimal("9")
        line.save()
        self.assertEqual(self._purchase_facts(inv_id), before)
        line.delete()
        self.assertEqual(self._purchase_facts(inv_id), before)

    def test_the_cancel_dialog_says_a_received_purchase_stays(self):
        inv_id, _before = self._received()
        inv = Invoice.objects.get(pk=inv_id)
        page = self.client.get(reverse("operating:order_detail", args=[inv.for_order.pk]))
        self.assertContains(page, "Purchase %s was already received" % inv.number)
        self.assertNotContains(page, "is cancelled with the order")

    def test_cancelling_the_purchase_takes_its_lines_off_the_order(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(20,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        stock = Product.objects.create(title="Stock cloth", sku="STK0001", price=1)
        OrderItem.objects.create(order=order, product=stock, quantity=Decimal("10"), price=Decimal("2"))
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual([it.product.sku for it in order.items.select_related("product")], ["STK0001"])
        order.refresh_from_db()
        self.assertEqual(order.order_status, "pending")
        inv = Invoice.objects.get(pk=inv_id)
        self.assertIn(("field", "purchase", "%s cancelled — 2 line(s) removed" % inv.number),
                      self._order_log(order))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "were removed from order %s" % order.order_number)

    def test_cancelling_the_purchase_cancels_an_order_left_empty(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        self.assertEqual(order.order_status, "cancelled")
        self.assertFalse(order.items.exists())
        inv = Invoice.objects.get(pk=inv_id)
        self.assertIn(("field", "cancel_reason", "Purchase %s cancelled" % inv.number),
                      self._order_log(order))
        self.assertFalse(self._sale(order).exists())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "was cancelled too")

    def test_editing_the_purchase_is_logged_on_both_sides(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertIn(("created", None, "purchase", None, "for order %s" % order.order_number),
                      self._purchase_log(inv_id))
        self.assertEqual([c[0] for c in self._purchase_log(inv_id) if c[0] == "item_added"], ["item_added"])
        r = self._save(self._plan(variants=[self._variant(tops=(40,), sale="5.50")],
                                  customer=False, product=Product.objects.get()), pk=inv_id)
        self.assertEqual(r.status_code, 200, r.content)
        log = self._purchase_log(inv_id)
        self.assertIn(("item_updated", "quantity", "purchase", "55", "40"), log)
        self.assertIn(("item_updated", "sale_price", "purchase", "5", "5.5"), log)
        self.assertIn(("field", "purchase", "1 line(s) changed from purchase %s"
                       % Invoice.objects.get(pk=inv_id).number), self._order_log(order))
        # The order's own item log has the quantity row too.
        self.assertIn(("item_updated", "quantity", "40.00"), self._order_log(order))

    def test_receiving_is_logged(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.assertTrue(self._confirm(inv_id).json()["success"])
        self.assertIn(("status", "status", "purchase", "draft", "issued"), self._purchase_log(inv_id))

    def test_the_purchase_page_lists_its_changes(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "Purchase changes")
        self.assertContains(page, "Item added")
        self.assertContains(page, "K24644.G07")
