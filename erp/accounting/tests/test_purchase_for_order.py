# to run this test, use the command:
# python manage.py test accounting.tests.test_purchase_for_order

"""A purchase bought for a customer.

A client asks for something the shelves don't have. The purchase is written
with the customer and a sale price per variant, and saving it creates the
customer's order too. Receiving the purchase reserves the arriving rolls for
that order — each one whole — so they can't be packed into another one
first.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

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
from operating.order_purchases import syncing


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
            "unit": "m",
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

    # ── What a line still on its way in costs ───────────────────────
    def _priced_purchase(self, price, currency="USD", rates=None):
        product = Product.objects.create(title="Krep", sku="KRP1", featured=False)
        ProductVariant.objects.create(product=product, variant_sku="KRP1.G07",
                                      variant_cost=Decimal("2.00"))
        variant = {**self._variant(sku="KRP1.G07"), "price": price, "currency": currency}
        plan = self._plan(product=product, variants=[variant])
        if rates:
            plan["rates"] = rates
        r = self._save(plan)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["invoice_id"], Invoice.objects.get(pk=r.json()["invoice_id"]).for_order

    def test_a_line_on_its_way_costs_what_its_purchase_pays(self):
        """Order 460: MT-1015 bought at $2.60 showed $2.45 and $2.70, the
        last costs on record, until the goods arrived."""
        inv_id, order = self._priced_purchase("2.60")
        line = order.items.get()
        self.assertEqual(line.unit_cost(), Decimal("2.6000"))
        self.assertEqual(Order.objects.get(pk=order.pk).total_cost(), Decimal("143.00"))  # 55 m

        # Received, the rolls carry the same cost.
        self.assertTrue(self._confirm(inv_id).json()["success"])
        self.assertEqual(OrderItem.objects.get(pk=line.pk).unit_cost(), Decimal("2.6000"))

    def test_a_purchase_in_another_currency_is_costed_in_base(self):
        _inv_id, order = self._priced_purchase("2.00", currency="EUR", rates={"EUR": "1.10"})
        self.assertEqual(order.items.get().unit_cost(), Decimal("2.2000"))

    def test_a_line_longer_than_its_purchase_costs_the_rest_at_catalog(self):
        _inv_id, order = self._priced_purchase("3.00")
        line = order.items.get()
        OrderItem.objects.filter(pk=line.pk).update(quantity=Decimal("110"))  # 55 bought
        self.assertEqual(OrderItem.objects.get(pk=line.pk).unit_cost(), Decimal("2.5000"))

    def _hold_costed_roll(self, item, meters, cost):
        wp, _ = WarehouseProduct.objects.get_or_create(
            warehouse=self.wh, sku=item.product_variant.variant_sku,
            defaults={"name": "Shelf", "quantity": meters,
                      "catalog_variant": item.product_variant})
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=meters, quantity_remaining=meters, status="in_stock",
            unit_cost_base=Decimal(cost))
        OrderStockReservation.objects.create(order=item.order, order_item=item,
                                             stock_item=roll, warehouse_product=wp,
                                             quantity=meters)
        return roll

    def test_a_line_costs_its_held_rolls_not_the_variants_average(self):
        """The variant's other stock (here a $5.00 roll) is not what this
        order sends; the roll held for it is."""
        order = Order.objects.create(contact=self.customer)
        line = self._stock_line(order)                                  # 50 m
        self._hold_costed_roll(line, Decimal("30"), "1.00")
        self._hold_costed_roll(line, Decimal("20"), "2.00")
        WarehouseProductItem.objects.create(
            product=WarehouseProduct.objects.get(sku="STK0001.1"), quantity=Decimal("40"),
            quantity_remaining=Decimal("40"), status="in_stock", unit_cost_base=Decimal("5.00"))
        self.assertEqual(OrderItem.objects.get(pk=line.pk).unit_cost(), Decimal("1.4000"))

        # Shipped, the holds are spent and the cost stays what went out.
        OrderStockReservation.objects.filter(order_item=line).update(consumed=True)
        WarehouseProductItem.objects.filter(reservations__order_item=line).update(
            status="consumed", quantity_remaining=0)
        self.assertEqual(OrderItem.objects.get(pk=line.pk).unit_cost(), Decimal("1.4000"))

    def test_a_held_roll_and_a_purchase_share_a_line_by_quantity(self):
        _inv_id, order = self._priced_purchase("3.00")                  # 55 m coming
        line = order.items.get()
        OrderItem.objects.filter(pk=line.pk).update(quantity=Decimal("75"))
        self._hold_costed_roll(OrderItem.objects.get(pk=line.pk), Decimal("20"), "1.50")
        # 20 × 1.50 + 55 × 3.00 = 195 over 75 m
        self.assertEqual(OrderItem.objects.get(pk=line.pk).unit_cost(), Decimal("2.6000"))
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

    def test_an_edit_that_blanks_the_price_keeps_the_orders(self):
        """The order prices a line it already has; the purchase follows."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self._save(self._plan(variants=[self._variant(tops=(40,), sale="")],
                                  customer=False, product=Product.objects.get()),
                       pk=inv_id)
        self.assertEqual(r.status_code, 200, r.content)
        line = Order.objects.get().items.get()
        self.assertEqual(line.quantity, Decimal("40.00"))
        self.assertEqual(line.price, Decimal("5.00"))
        plan = Invoice.objects.get(pk=inv_id).intake_plan
        self.assertEqual(plan["products"][0]["variants"][0]["sale_price"], "5.00")

    # ── Editing the draft keeps the order in step ───────────────────
    def test_editing_the_draft_updates_the_order(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        product = Product.objects.get()
        by_hand = OrderItem.objects.create(
            order=order, product=product, quantity=Decimal("1"), price=Decimal("9"),
            product_variant=ProductVariant.objects.create(
                product=product, variant_sku="K24644.G99"))

        # Reopened, the draft names the product it created as an existing one.
        plan = self._plan(variants=[self._variant(tops=(40,), sale="6.00")], customer=False,
                          product=Product.objects.get())
        r = self._save(plan, pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())

        self.assertEqual(Order.objects.count(), 1)
        lines = {it.product_variant.variant_sku: it
                 for it in Order.objects.get().items.select_related("product_variant")}
        self.assertEqual(set(lines), {"K24644.G07", "K24644.G99"})  # G08 dropped, hand line kept
        self.assertEqual(lines["K24644.G07"].quantity, Decimal("40.00"))
        # The sale price is the order's: the purchase's 6.00 doesn't move it.
        self.assertEqual(lines["K24644.G07"].price, Decimal("5.00"))
        self.assertEqual(lines["K24644.G99"].pk, by_hand.pk)

    def test_an_order_being_packed_still_follows_the_purchase(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        Order.objects.update(order_status="packaging")
        r = self._save(self._plan(variants=[self._variant(tops=(5,))], customer=False,
                                  product=Product.objects.get()), pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(OrderItem.objects.get().quantity, Decimal("5.00"))

    def test_a_shipped_order_is_left_alone(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        Order.objects.update(order_status="shipped")
        r = self._save(self._plan(variants=[self._variant(tops=(5,))], customer=False,
                                  product=Product.objects.get()), pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(OrderItem.objects.get().quantity, Decimal("55.00"))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "has already shipped")

    def _hold_shelf_roll(self, item, meters=Decimal("50"), barcode=None):
        """A roll off the shelf held for `item`, as the order form does."""
        wp = WarehouseProduct.objects.create(warehouse=self.wh, name="Shelf", sku="SHELF",
                                             quantity=meters)
        roll = WarehouseProductItem.objects.create(unit_cost_base=Decimal("1"),
            product=wp, quantity=meters, quantity_remaining=meters, status="in_stock",
            barcode=barcode)
        OrderStockReservation.objects.create(order=item.order, order_item=item,
                                             stock_item=roll, warehouse_product=wp,
                                             quantity=meters)

    def _stock_line(self, order):
        stock = Product.objects.create(title="Stock cloth", sku="STK0001", price=1)
        return OrderItem.objects.create(order=order, product=stock, quantity=Decimal("50"),
                                        price=Decimal("2"),
                                        product_variant=ProductVariant.objects.create(
                                            product=stock, variant_sku="STK0001.1"))

    def test_a_roll_held_for_another_line_does_not_freeze_the_purchases_lines(self):
        """Order 351: shelf rolls held for its other lines kept the line
        of 3009 ecru 320 when the purchase turned it to 330 — the arriving
        roll then matched nothing and sat on the shelf."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self._hold_shelf_roll(self._stock_line(order))

        r = self._save(self._plan(variants=[self._variant(name="G08", sku="K24644.G08")],
                                  customer=False, product=Product.objects.get(sku="K24644")),
                       pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(sorted(order.items.values_list("product_variant__variant_sku", flat=True)),
                         ["K24644.G08", "STK0001.1"])
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertNotContains(page, "rolls are already held for")

        # And the roll that comes in lands on the line.
        self.assertTrue(self._confirm(inv_id).json()["success"])
        self.assertEqual(
            sorted(OrderStockReservation.objects.filter(order=order)
                   .values_list("order_item__product_variant__variant_sku", flat=True)),
            ["K24644.G08", "K24644.G08", "STK0001.1"])

    def _two_row_purchase(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        return inv_id, Invoice.objects.get(pk=inv_id).for_order

    def _resave(self, inv_id, variants):
        r = self._save(self._plan(variants=variants, customer=False,
                                  product=Product.objects.get(sku="K24644")), pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        return [str(m) for m in page.context["messages"]]

    def test_a_quantity_change_reaches_a_line_with_rolls_reserved(self):
        inv_id, order = self._two_row_purchase()
        self._hold_shelf_roll(order.items.get(product_variant__variant_sku="K24644.G07"))
        said = self._resave(inv_id, [self._variant(tops=(5,)),
                                     self._variant(name="G08", sku="K24644.G08", tops=(20,))])
        self.assertEqual(dict(order.items.values_list("product_variant__variant_sku", "quantity")),
                         {"K24644.G07": Decimal("5.00"), "K24644.G08": Decimal("20.00")})
        # Whole rolls go with the order: the reserved roll stays.
        self.assertEqual(self._held(order), [Decimal("50.00")])
        self.assertIn("Order %s changed with this purchase: K24644.G07 55 → 5; "
                      "K24644.G08 10 → 20." % order.order_number, said)

    def test_a_row_replaced_keeps_the_old_line_on_its_warehouse_roll(self):
        """A new row in place of one removed (no SKU it was loaded with):
        the purchase's 55 m come off the old line, but the 50 m roll from
        the warehouse reserved for it stays, and so does the line."""
        inv_id, order = self._two_row_purchase()
        line = order.items.get(product_variant__variant_sku="K24644.G07")
        self._hold_shelf_roll(line, barcode="SHELF01")
        said = self._resave(inv_id, [self._variant(name="G09", sku="K24644.G09"),
                                     self._variant(name="G08", sku="K24644.G08", tops=(10,))])
        self.assertEqual(dict(order.items.values_list("product_variant__variant_sku", "quantity")),
                         {"K24644.G07": Decimal("50.00"), "K24644.G08": Decimal("10.00"),
                          "K24644.G09": Decimal("55.00")})
        self.assertEqual(list(OrderStockReservation.objects.filter(order=order)
                              .values_list("order_item_id", flat=True)), [line.pk])
        self.assertIn("Order %s changed with this purchase: K24644.G09 added, 55; "
                      "K24644.G07 stays on the order with roll(s) SHELF01 already reserved "
                      "for it; K24644.G07 55 → 50." % order.order_number, said)

    def test_a_row_replaced_with_nothing_reserved_leaves_the_order(self):
        inv_id, order = self._two_row_purchase()
        said = self._resave(inv_id, [self._variant(name="G09", sku="K24644.G09"),
                                     self._variant(name="G08", sku="K24644.G08", tops=(10,))])
        self.assertEqual(sorted(order.items.values_list("product_variant__variant_sku", flat=True)),
                         ["K24644.G08", "K24644.G09"])
        self.assertIn("Order %s changed with this purchase: K24644.G09 added, 55; "
                      "K24644.G07 removed." % order.order_number, said)

    def test_a_corrected_sku_keeps_the_line_and_its_reserved_rolls(self):
        """A SKU mistyped on the purchase and put right: the same order
        line takes the right SKU, and the roll reserved for it stays."""
        inv_id, order = self._two_row_purchase()
        line = order.items.get(product_variant__variant_sku="K24644.G07")
        self._hold_shelf_roll(line, barcode="SHELF04")
        fixed = dict(self._variant(name="G09", sku="K24644.G09", tops=(60,)),
                     orig_sku="K24644.G07")
        said = self._resave(inv_id, [fixed, self._variant(name="G08", sku="K24644.G08",
                                                          tops=(10,))])
        line.refresh_from_db()
        self.assertEqual(line.product_variant.variant_sku, "K24644.G09")
        self.assertEqual(line.quantity, Decimal("60.00"))
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(list(OrderStockReservation.objects.filter(order=order)
                              .values_list("order_item_id", flat=True)), [line.pk])
        self.assertIn("Order %s changed with this purchase: K24644.G07 → K24644.G09, same line; "
                      "K24644.G09 55 → 60." % order.order_number, said)
        self.assertTrue(order.change_logs.filter(field="product", old_value="K24644.G07",
                                                 new_value="K24644.G09").exists())
        # The SKU the page loaded is not kept in the plan.
        self.assertNotIn("orig_sku", Invoice.objects.get(pk=inv_id)
                         .intake_plan["products"][0]["variants"][0])

    def test_a_corrected_sku_renames_the_drafts_own_variant(self):
        """The draft made K24644.G07 and nothing else uses it: putting the
        SKU right renames it, so the catalog keeps no unused copy."""
        inv_id, order = self._two_row_purchase()
        line = order.items.get(product_variant__variant_sku="K24644.G07")
        variant_id = line.product_variant_id
        self._hold_shelf_roll(line, barcode="SHELF05")
        said = self._resave(inv_id, [dict(self._variant(name="G09", sku="K24644.G09"),
                                          orig_sku="K24644.G07"),
                                     self._variant(name="G08", sku="K24644.G08", tops=(10,))])
        self.assertEqual(ProductVariant.objects.get(pk=variant_id).variant_sku, "K24644.G09")
        self.assertFalse(ProductVariant.objects.filter(variant_sku="K24644.G07").exists())
        line.refresh_from_db()
        self.assertEqual(line.product_variant_id, variant_id)
        self.assertEqual(list(OrderStockReservation.objects.filter(order=order)
                              .values_list("order_item_id", flat=True)), [line.pk])
        self.assertIn("Order %s changed with this purchase: K24644.G07 → K24644.G09, same line."
                      % order.order_number, said)
        self.assertTrue(order.change_logs.filter(field="product", old_value="K24644.G07",
                                                 new_value="K24644.G09").exists())

    def test_a_corrected_sku_on_a_shared_variant_asks_first(self):
        """K24644.G07 is on another order too: the save does not guess
        between renaming it for both and making a separate one."""
        inv_id, order = self._two_row_purchase()
        line = order.items.get(product_variant__variant_sku="K24644.G07")
        other = Order.objects.create(contact=self.customer)
        OrderItem.objects.create(order=other, product=line.product,
                                 product_variant=line.product_variant,
                                 quantity=Decimal("3"), price=Decimal("5"))
        self._hold_shelf_roll(line, barcode="SHELF06")
        fixed = dict(self._variant(name="G09", sku="K24644.G09"), orig_sku="K24644.G07")
        plan = self._plan(variants=[fixed, self._variant(name="G08", sku="K24644.G08",
                                                         tops=(10,))],
                          customer=False, product=Product.objects.get(sku="K24644"))
        r = self._save(plan, pk=inv_id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("used outside this purchase too", r.json()["error"])

        # "Separate": a new variant, and the same line moves onto it.
        said = self._resave(inv_id, [dict(fixed, sku_choice="separate"),
                                     self._variant(name="G08", sku="K24644.G08", tops=(10,))])
        line.refresh_from_db()
        self.assertEqual(line.product_variant.variant_sku, "K24644.G09")
        self.assertTrue(ProductVariant.objects.filter(variant_sku="K24644.G07").exists())
        self.assertEqual(list(OrderStockReservation.objects.filter(order=order)
                              .values_list("order_item_id", flat=True)), [line.pk])
        self.assertIn("Order %s changed with this purchase: K24644.G07 → K24644.G09, same line."
                      % order.order_number, said)

    def test_a_corrected_product_name_renames_the_drafts_own_product(self):
        """The card cleared and typed anew: the product the draft made is
        put right rather than a second one made beside it."""
        inv_id, order = self._two_row_purchase()
        product = Product.objects.get(sku="K24644")
        plan = self._plan(variants=[self._variant(),
                                    self._variant(name="G08", sku="K24644.G08", tops=(10,))],
                          customer=False)
        plan["products"][0]["main_product"] = {"mode": "new", "name": "Linen K24645",
                                               "sku": "K24645", "orig_product_id": product.pk}
        r = self._save(plan, pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.filter(variants__isnull=False).distinct().count(), 1)
        product.refresh_from_db()
        self.assertEqual((product.sku, product.title), ("K24645", "Linen K24645"))
        self.assertEqual(set(order.items.values_list("product_id", flat=True)), {product.pk})
        stored = Invoice.objects.get(pk=inv_id).intake_plan["products"][0]["main_product"]
        self.assertEqual((stored["mode"], stored["id"]), ("existing", product.pk))

    def test_the_drafts_edit_page_says_which_rows_may_rename(self):
        inv_id, order = self._two_row_purchase()
        other = Order.objects.create(contact=self.customer)
        g08 = ProductVariant.objects.get(variant_sku="K24644.G08")
        OrderItem.objects.create(order=other, product=g08.product, product_variant=g08,
                                 quantity=Decimal("3"), price=Decimal("5"))
        page = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        rows = {v["sku"]: v for v in page.context["intake_plan"]["products"][0]["variants"]}
        self.assertEqual((rows["K24644.G07"]["sku_follows"], rows["K24644.G07"]["sku_uses"]),
                         (True, []))
        self.assertFalse(rows["K24644.G08"]["sku_follows"])
        self.assertEqual(len(rows["K24644.G08"]["sku_uses"]), 1)

    def test_a_preview_says_what_the_save_would_do_and_writes_nothing(self):
        inv_id, order = self._two_row_purchase()
        plan_before = Invoice.objects.get(pk=inv_id).intake_plan
        changes_before = order.change_logs.count()
        plan = self._plan(variants=[self._variant(tops=(5,))], customer=False,
                          product=Product.objects.get(sku="K24644"))
        plan["preview"] = True
        r = self._save(plan, pk=inv_id)
        self.assertEqual(r.json(), {"success": True, "order": order.order_number,
                                    "preview": ["K24644.G07 55 → 5", "K24644.G08 removed"]})
        self.assertEqual(dict(order.items.values_list("product_variant__variant_sku", "quantity")),
                         {"K24644.G07": Decimal("55.00"), "K24644.G08": Decimal("10.00")})
        self.assertEqual(Invoice.objects.get(pk=inv_id).intake_plan, plan_before)
        self.assertEqual(order.change_logs.count(), changes_before)

    def test_a_row_deleted_while_a_warehouse_roll_covers_its_line(self):
        """The warehouse had the 10 m and it was reserved for the line, so
        the row is deleted from the purchase: the line stays, on that roll."""
        inv_id, order = self._two_row_purchase()
        self._hold_shelf_roll(order.items.get(product_variant__variant_sku="K24644.G08"),
                              meters=Decimal("10"), barcode="SHELF02")
        said = self._resave(inv_id, [self._variant()])
        self.assertEqual(dict(order.items.values_list("product_variant__variant_sku", "quantity")),
                         {"K24644.G07": Decimal("55.00"), "K24644.G08": Decimal("10.00")})
        self.assertEqual(self._held(order), [Decimal("10.00")])
        self.assertIn("Order %s changed with this purchase: K24644.G08 stays on the order with "
                      "roll(s) SHELF02 already reserved for it." % order.order_number, said)

    def test_cancelling_the_purchase_keeps_lines_on_their_warehouse_rolls(self):
        inv_id, order = self._two_row_purchase()
        self._stock_line(order)
        self._hold_shelf_roll(order.items.get(product_variant__variant_sku="K24644.G07"),
                              barcode="SHELF03")
        self.assertEqual(
            self._cancel_warning(inv_id),
            "Order %s: its 1 line(s) from this purchase are removed; the order stays open "
            "with the rest. Lines with roll(s) SHELF03 already reserved for them stay, "
            "with those rolls." % order.order_number)

        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]),
                             {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(dict(order.items.values_list("product_variant__variant_sku", "quantity")),
                         {"STK0001.1": Decimal("50.00"), "K24644.G07": Decimal("50.00")})
        self.assertEqual(self._held(order), [Decimal("50.00")])
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "Lines with roll(s) SHELF03 already reserved for them stay, "
                                  "with those rolls.")

    def test_a_received_purchase_cancel_names_the_order_holding_its_rolls(self):
        """Its rolls were reserved for the order it was bought for on
        arrival: the refusal says which rolls and which order, not
        "another order"."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.assertTrue(self._confirm(inv_id).json()["success"])
        order = Invoice.objects.get(pk=inv_id).for_order
        codes = list(WarehouseProductItem.objects
                     .filter(purchase_invoice_item__invoice_id=inv_id)
                     .order_by("pk").values_list("barcode", flat=True))
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]),
                             {"reason": "Wrong supplier"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"],
                         "Rolls from this purchase are on an order — %s reserved for order %s. "
                         "Take them off the order first, then cancel."
                         % (", ".join(codes), order.order_number))

    def test_moving_the_draft_to_another_books_warehouse_is_refused(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self._save(self._plan(warehouse=self.other_wh, customer=False), pk=inv_id)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=inv_id).intake_warehouse, self.wh)

    # ── Receiving holds the rolls ───────────────────────────────────
    def test_confirming_holds_the_rolls_for_the_order(self):
        inv_id = self._save(self._plan(variants=[self._variant(tops=(30, 25))])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        # The customer asked for about 40; all 55 bought for them is theirs.
        order.items.update(quantity=Decimal("40"))

        r = self._confirm(inv_id)
        self.assertTrue(r.json()["success"], r.json())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "2 rolls reserved for order %s." % order.order_number)

        self.assertEqual(self._held(order), [Decimal("30.00"), Decimal("25.00")])
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

    def test_each_roll_is_held_on_the_line_of_its_variant(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertTrue(self._confirm(inv_id).json()["success"])
        held = {(r.order_item.product_variant.variant_sku, r.quantity)
                for r in OrderStockReservation.objects.filter(order=order)
                .select_related("order_item__product_variant")}
        self.assertEqual(held, {("K24644.G07", Decimal("30.00")),
                                ("K24644.G07", Decimal("25.00")),
                                ("K24644.G08", Decimal("10.00"))})

    def test_rolls_matching_no_line_of_the_order_stay_free(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        # Both lines taken off the order without touching the purchase,
        # which leaves it one for a variant the purchase does not bring.
        with syncing():
            OrderItem.objects.filter(order=order).delete()
        product = Product.objects.get()
        OrderItem.objects.create(order=order, product=product,
                                 product_variant=ProductVariant.objects.create(
                                     product=product, variant_sku="K24644.G99"),
                                 quantity=Decimal("1"), price=Decimal("9"))
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
        CurrentAccount.objects.create(book=self.book, code="C-OLG", name=self.customer.name,
                                      type="customer", contact=self.customer,
                                      default_currency=try_)
        self.assertEqual(self._currency("contact", self.customer.pk),
                         {"currency": "TRY", "account": self.customer.name})
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

    def test_a_line_names_the_purchase_that_brings_it_in(self):
        """A line from the purchase links to it; one added on the order
        names no purchase."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        invoice = Invoice.objects.get(pk=inv_id)
        order = invoice.for_order
        product = Product.objects.get()
        extra = OrderItem.objects.create(order=order, product=product,
                                         product_variant=ProductVariant.objects.create(
                                             product=product, variant_sku="K24644.G99"),
                                         quantity=Decimal("3"), price=Decimal("9"))
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        named = {it.pk: [p.pk for p in it.purchases] for it in r.context["order_items_sorted"]}
        self.assertEqual(named.pop(extra.pk), [])
        self.assertEqual(list(named.values()), [[inv_id]])
        # Its goods not in yet, the rolls coming name it once, over them;
        # the line doesn't.
        self.assertContains(r, 'class="od-po-chip" href="%s" target="_blank"'
                            % reverse("accounts:purchase_order_detail", args=[inv_id]), count=1)
        self.assertEqual([it.line_purchases for it in r.context["order_items_sorted"]], [[], []])
        self.assertNotContains(r, "not on the purchase")

    def test_a_line_awaiting_its_purchase_opens_onto_the_rolls_coming(self):
        """The plan's two rolls (30 + 25 m), each on its own, not a bare
        "no rolls"."""
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        [line] = r.context["order_items_sorted"]
        self.assertEqual(line.expected_label, "2 rolls · 55 m")
        self.assertContains(r, "≈ 2 rolls · 55 m expected")
        self.assertEqual([(e["qty"], e["unit"]) for e in line.expected_rolls],
                         [(Decimal("30"), "m"), (Decimal("25"), "m")])
        self.assertContains(r, 'class="od-row-toggle" data-toggle-tops="%s"' % line.pk)
        self.assertContains(r, '<span class="m">≈ 30 m</span>')
        self.assertContains(r, '<span class="m">≈ 25 m</span>')

    def test_a_line_shows_what_it_holds_beside_what_is_still_coming(self):
        """One purchase in, another for the same variant on its way: the
        held rolls and the expected one, each pill naming its purchase."""
        first = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=first).for_order
        self.assertTrue(self._confirm(first).json()["success"])
        plan = self._plan(variants=[self._variant(tops=(40,))])
        second = Invoice.objects.create(
            type="purchase", status="ordered", for_order=order, series="PUR", number="2",
            current_account=self.supplier, book=self.book, currency=self.usd,
            date=order.order_date, due_date=order.order_date,
            intake_warehouse=self.wh, intake_plan=plan)
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        [line] = r.context["order_items_sorted"]
        self.assertEqual([e["purchase"].pk for e in line.expected_rolls], [second.pk])
        # The purchase whose goods are in is named on the line.
        self.assertEqual([p.pk for p in line.line_purchases], [first])
        self.assertContains(r, "≈ 1 roll · 40 m expected")
        self.assertContains(r, '<span class="m">≈ 40 m</span>')
        self.assertEqual(len(self._held(order)), 2)
        self.assertContains(r, 'class="od-top-pill"', count=2)
        self.assertContains(r, 'href="%s" target="_blank"'
                            % reverse("accounts:purchase_order_detail", args=[second.pk]))

    def test_complete_lists_every_purchase_still_on_its_way(self):
        """Two purchases not in yet: Complete's dialog lists each with its
        supplier and what it brings, not a footer button apiece."""
        first = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=first).for_order
        second = Invoice.objects.create(
            type="purchase", status="ordered", for_order=order, series="PUR", number="2",
            current_account=self.supplier, book=self.book, currency=self.usd,
            date=order.order_date, due_date=order.order_date, intake_warehouse=self.wh,
            intake_plan=self._plan(variants=[self._variant(tops=(40,))]))
        page = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertContains(page, 'class="odw-list"')
        for inv_id in (first, second.pk):
            self.assertContains(page, '<li><a href="%s">'
                                % reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, '<span class="odw-brings">2 rolls · ≈ 55 m</span>')
        self.assertContains(page, '<span class="odw-brings">1 roll · ≈ 40 m</span>')
        self.assertNotContains(page, "fa-file-invoice\"></i> Open ")

    def test_a_cancelled_purchase_is_named_on_no_line(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertFalse(any(it.purchases for it in r.context["order_items_sorted"]))
        self.assertNotContains(r, 'class="od-po-chip"')

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

    def test_cancelling_the_draft_takes_its_lines_off_an_order_being_packed(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self._stock_line(order)
        Order.objects.update(order_status="packaging")
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        self.assertEqual(order.order_status, "packaging")
        self.assertEqual(list(order.items.values_list("product_variant__variant_sku", flat=True)),
                         ["STK0001.1"])

    # ── The cancel confirmation says what happens to the order ───────
    # Cancelling the purchase reaches the order — so it is said before
    # anyone confirms, not after.

    def _cancel_warning(self, inv_id):
        """What the purchase page's cancel dialog will say about the order,
        read off the context and checked to be on the page."""
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        warning = page.context["cancel_order_warning"]
        if warning:
            self.assertContains(page, '<p class="po-dlg-warn">%s</p>' % escape(warning))
        return warning

    def test_the_purchase_cancel_says_what_happens_to_the_order(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        self.assertEqual(
            self._cancel_warning(inv_id),
            "Order %s: all its lines come from this purchase, so the order is "
            "cancelled too." % order.order_number)
        # With a line of its own the order outlives the purchase.
        self._stock_line(order)
        self.assertIn("its 1 line(s) from this purchase are removed", self._cancel_warning(inv_id))

    def test_the_purchase_cancel_says_the_same_while_packing(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        Order.objects.update(order_status="packaging")
        self.assertEqual(
            self._cancel_warning(inv_id),
            "Order %s: all its lines come from this purchase, so the order is "
            "cancelled too." % order.order_number)

    def test_a_cancelled_purchase_warns_about_no_order(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
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
            type="purchase", status="ordered", for_order=order, series="PUR", number="2",
            current_account=self.supplier, book=self.book, currency=self.usd,
            date=order.order_date, due_date=order.order_date)
        self.assertTrue(self._confirm(first).json()["success"])
        self.assertEqual(self._complete(order), (False, "goods_not_received"))
        self.assertFalse(self._sale(order).exists())
        # Cancelling the straggler means nothing more is coming.
        r = self.client.post(reverse("accounts:purchase_cancel", args=[second.pk]), {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(self._complete(order), (True, None))
        self.assertTrue(self._sale(order).exists())

    def test_cancelling_the_only_draft_bills_what_else_the_order_holds(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        stock = Product.objects.create(title="Stock cloth", sku="STK0001", price=1)
        OrderItem.objects.create(order=order, product=stock, quantity=Decimal("10"), price=Decimal("2"),
                                 product_variant=ProductVariant.objects.create(
                                     product=stock, variant_sku="STK0001.1"))
        self.assertFalse(self._sale(order).exists())
        self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
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
        # The button answers with a dialog saying why and what to do
        # instead — ship part, or open the purchase — not a dead press.
        self.assertContains(page, 'id="od-complete-btn" class="ord-btn primary" data-status="shipped"\n                        data-waits')
        self.assertContains(page, 'id="odWaitsModal"')
        self.assertContains(page, reverse("operating:order_ship_part", args=[order.pk]))
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
        self.assertEqual(inv.status, "ordered")
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
        self.assertIn(("status", "status", "order", "ordered", "cancelled"), self._purchase_log(inv_id))
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
        self.assertIn(("status", "status", "order", "ordered", "cancelled"), self._purchase_log(inv_id))
        self.assertIn(("field", "purchase", "%s cancelled with the order" % inv.number),
                      self._order_log(order))
        self.assertEqual(inv.cancel_reason,
                         "Order %s was cancelled" % (order.order_number or order.pk))

    def test_a_purchase_is_not_cancelled_without_a_reason(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        for reason in ({}, {"reason": "   "}):
            r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), reason)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(Invoice.objects.get(pk=inv_id).status, "ordered")

    def test_the_reason_is_kept_and_logged(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]),
                             {"reason": "  Supplier ran out  "})
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Invoice.objects.get(pk=inv_id).cancel_reason, "Supplier ran out")
        self.assertIn(("field", "cancel_reason", "purchase", None, "Supplier ran out"),
                      self._purchase_log(inv_id))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "Supplier ran out")

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
        self.assertEqual(before["status"], "received")
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
        self.assertIn(("status", "status", "order", "ordered", "cancelled"), self._purchase_log(inv_id))
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
        # What arrived stays what arrived. Only what the customer pays
        # follows the order, so the two never disagree about it.
        inv_id, before = self._received()
        order = Invoice.objects.get(pk=inv_id).for_order
        OrderStockReservation.objects.filter(order=order).delete()
        line = order.items.get()
        line.quantity, line.price = Decimal("10"), Decimal("9")
        line.save()
        after = self._purchase_facts(inv_id)
        row = after["plan"]["products"][0]["variants"][0]
        self.assertEqual(row["sale_price"], "9")
        row["sale_price"] = before["plan"]["products"][0]["variants"][0]["sale_price"]
        self.assertEqual(len(after.pop("log")), len(before["log"]) + 1)
        self.assertEqual(after, {k: v for k, v in before.items() if k != "log"})
        after = self._purchase_facts(inv_id)
        line.delete()
        self.assertEqual(self._purchase_facts(inv_id), after)

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
        OrderItem.objects.create(order=order, product=stock, quantity=Decimal("10"), price=Decimal("2"),
                                 product_variant=ProductVariant.objects.create(
                                     product=stock, variant_sku="STK0001.1"))
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
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
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
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

    def _other_half(self, order, with_goods=True):
        """Split `order` across books: a sibling half in the other book."""
        import uuid
        order.split_group = uuid.uuid4()
        order.save(update_fields=["split_group"])
        account = CurrentAccount.objects.create(
            book=self.other_book, code="C-ERG", name="Oleg (Ergene)", type="customer",
            contact=self.customer, default_currency=self.usd)
        half = Order.objects.create(current_account=account, contact=self.customer,
                                    currency=order.currency, split_group=order.split_group)
        if with_goods:
            tul = Product.objects.create(title="Tul", sku="TUL01", price=1)
            OrderItem.objects.create(order=half, quantity=Decimal("10"), price=Decimal("2"),
                                     product=tul,
                                     product_variant=ProductVariant.objects.create(
                                         product=tul, variant_sku="TUL01.1"))
        return half

    @patch("operating.order_notifications.send_order_event_email")
    def test_a_half_left_empty_is_cancelled_alone_and_the_rest_goes_ahead(self, send):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        order.notify_customer = True
        order.save(update_fields=["notify_customer"])
        half = self._other_half(order)
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        half.refresh_from_db()
        self.assertEqual(order.order_status, "cancelled")
        self.assertEqual(half.order_status, "pending")
        self.assertTrue(half.items.exists())
        # The customer's order is still on: nobody is told it was cancelled.
        send.assert_not_called()
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "The rest of the split order stays open.")

    def test_a_half_left_empty_beside_an_empty_half_cancels_the_whole_order(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        half = self._other_half(order, with_goods=False)
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]), {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        half.refresh_from_db()
        self.assertEqual((order.order_status, half.order_status), ("cancelled", "cancelled"))

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
        # The typed 5.50 gave way to the order's price, so no price change.
        self.assertFalse([c for c in log if c[:2] == ("item_updated", "sale_price")])
        self.assertIn(("field", "purchase", "1 line(s) changed from purchase %s"
                       % Invoice.objects.get(pk=inv_id).number), self._order_log(order))
        # The order's own item log has the quantity row too.
        self.assertIn(("item_updated", "quantity", "40.00"), self._order_log(order))

    def test_the_orders_history_shows_the_purchases_history(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        inv = Invoice.objects.get(pk=inv_id)
        order = inv.for_order
        self._save(self._plan(variants=[self._variant(tops=(40,))], customer=False,
                              product=Product.objects.get()), pk=inv_id)
        purchase_rows = PurchaseChange.objects.filter(invoice=inv, origin="purchase").count()
        self.assertGreaterEqual(purchase_rows, 3)   # created, row added, quantity

        page = self.client.get(reverse("operating:order_changes", args=[order.pk]))
        rows = page.context["changes"]
        self.assertEqual(len([c for c in rows if getattr(c, "purchase", None)]), purchase_rows)
        self.assertEqual(len(rows), order.change_logs.count() + purchase_rows)
        # Newest first, both logs interleaved.
        self.assertEqual([c.created_at for c in rows],
                         sorted((c.created_at for c in rows), reverse=True))
        self.assertContains(page, 'class="ch-po"')
        self.assertContains(page, inv.number)
        self.assertContains(page, "Purchase created")
        # The filters reach the purchase's rows too.
        page = self.client.get(reverse("operating:order_changes", args=[order.pk]),
                               {"action": "item_updated", "q": "quantity"})
        self.assertTrue(any(getattr(c, "purchase", None) and c.field == "quantity"
                            for c in page.context["changes"]))

        page = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertTrue(any(getattr(c, "purchase", None)
                            for c in page.context["order_changes_preview"]))
        self.assertEqual(page.context["order_changes_count"],
                         order.change_logs.count() + purchase_rows)

    def test_a_sales_rep_does_not_see_the_purchases_history(self):
        from authentication.models import Permission
        from operating.views import _purchase_changes_for_order
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        rep = get_user_model().objects.create_user("rep_po", password="pw")
        rep.member.permissions.add(Permission.objects.get_or_create(name="sales_rep")[0])
        self.assertEqual(_purchase_changes_for_order(order, rep), [])
        self.assertTrue(_purchase_changes_for_order(order, self.admin))

    def test_receiving_is_logged(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        self.assertTrue(self._confirm(inv_id).json()["success"])
        self.assertIn(("status", "status", "purchase", "ordered", "received"), self._purchase_log(inv_id))

    def test_the_purchase_page_lists_its_changes(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "Purchase changes")
        self.assertContains(page, "Item added")
        self.assertContains(page, "K24644.G07")
