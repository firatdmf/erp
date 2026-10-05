"""A sample given to a client is a marketing cost, not the cost of a sale.

Run with:
    python manage.py test accounting.tests.test_sample_stock_out
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_ledger import JournalEntry
from accounting.services_ledger import balance_sheet, ensure_chart
from crm.models import Contact
from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


class SampleStockOut(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.warehouse = Warehouse.objects.create(name="Ergene Fabrika", accounting_book=self.book)
        self.product = WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="seta", sku="S1",
            quantity=Decimal("100"), cost_usd=Decimal("3.00"))
        # A stock item: a roll here, but the same holds for a box of sets.
        self.item = WarehouseProductItem.objects.create(
            product=self.product, quantity=Decimal("100"),
            quantity_remaining=Decimal("100"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4.00"))
        self.user = get_user_model().objects.create_user(username="wh", password="pw")
        self.client.force_login(self.user)

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def _post(self, **data):
        url = reverse("operating:warehouse_stock_out",
                      kwargs={"warehouse_pk": self.warehouse.pk, "product_pk": self.product.pk})
        return self.client.post(url, data)

    # ── posting ──────────────────────────────────────────────────
    def test_a_sample_goes_to_marketing_at_the_items_cost(self):
        StockMovement.objects.create(
            product=self.product, stock_item=self.item, movement_type="out",
            purpose="sample", quantity=Decimal("3"), reason="Sample for Georgiana")
        b = self._balances()
        self.assertEqual(b["5110"], Decimal("12.00"))      # 3 x 4.00, the item's cost
        self.assertEqual(b["1300"], Decimal("-12.00"))
        self.assertNotIn("5000", {k for k, v in b.items() if v})
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_an_ordinary_stock_out_is_still_cost_of_goods_sold(self):
        StockMovement.objects.create(
            product=self.product, stock_item=self.item, movement_type="out",
            quantity=Decimal("3"), reason="Sold")
        b = self._balances()
        self.assertEqual(b["5000"], Decimal("12.00"))
        self.assertFalse(b.get("5110"))

    # ── the stock-out form ───────────────────────────────────────
    def test_a_sample_is_recorded_against_its_item_and_client(self):
        georgiana = Contact.objects.create(name="Georgiana")
        r = self._post(amount="3", purpose="sample", stock_item_id=self.item.pk,
                       client_type="contact", client_pk=georgiana.pk,
                       reason="for the new collection")
        self.assertEqual(r.status_code, 200, r.content)
        mv = StockMovement.objects.get()
        self.assertEqual((mv.purpose, mv.stock_item, mv.reference), ("sample", self.item, "Georgiana"))
        self.assertEqual(mv.contact, georgiana)
        self.assertEqual(mv.reason, "Sample for Georgiana — for the new collection")
        self.item.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(self.item.quantity_remaining, Decimal("97"))
        self.assertEqual(self.product.quantity, Decimal("97"))
        self.assertEqual(self._balances()["5110"], Decimal("12.00"))

    def test_a_sample_needs_the_item_it_came_from(self):
        r = self._post(amount="3", purpose="sample", reference="Georgiana")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StockMovement.objects.exists())

    def test_a_sample_needs_its_client(self):
        r = self._post(amount="3", purpose="sample", stock_item_id=self.item.pk)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StockMovement.objects.exists())

    def test_a_typed_name_is_not_a_client(self):
        r = self._post(amount="3", purpose="sample", stock_item_id=self.item.pk,
                       reference="Georgiana")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StockMovement.objects.exists())

    def test_an_unknown_purpose_is_refused(self):
        r = self._post(amount="3", purpose="gift", stock_item_id=self.item.pk)
        self.assertEqual(r.status_code, 400)

    def test_any_stock_out_needs_the_item_it_came_from(self):
        """The shelves are valued item by item: taken off the product alone,
        the stock would leave the ledger and stay on every item."""
        r = self._post(amount="5", reason="damaged")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StockMovement.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, Decimal("100"))

    def test_the_item_picked_on_the_old_form_field_is_used(self):
        """The form sent the item as roll_id while the view read
        stock_item_id, so the item never lost its quantity."""
        r = self._post(amount="5", roll_id=self.item.pk, reason="damaged")
        self.assertEqual(r.status_code, 200, r.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity_remaining, Decimal("95"))
        self.assertEqual(StockMovement.objects.get().stock_item, self.item)
        self.assertEqual(JournalEntry.objects.get().lines.get(account__code="5000").debit, Decimal("20.00"))


class TakeOutLivesOnTheItem(TestCase):
    """Stock-out is recorded from the item's own pop-up, which speaks the
    product's packaging — a box of curtain sets is not a roll of metres.
    It is asked for when the item's quantity is changed there, not laid out
    beside it (test_roll_change_reason)."""

    def setUp(self):
        from operating.tests.test_stock_unit import _stock
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.shop = Warehouse.objects.create(name="Ready-made Shop", accounting_book=self.book)
        self.wp = _stock(self.shop, name="Floral white", sku="RN1337.GW9",
                         quantity=Decimal("18"), unit="pack", pack_type="box")
        WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("18"), quantity_remaining=Decimal("18"),
            barcode="BOX-167", lot_number="167", status="in_stock",
            unit_cost_base=Decimal("26.50"))
        user = get_user_model().objects.create_user("wh", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _page(self):
        r = self.client.get(reverse("operating:warehouse_product_detail",
                                    kwargs={"warehouse_pk": self.shop.pk, "product_pk": self.wp.pk}))
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_the_pop_up_speaks_boxes_not_rolls(self):
        html = self._page()
        for phrase in ("Edit box", "(this box)", "(the whole box, as received)",
                       "Delete box"):
            self.assertIn(phrase, html)
        for phrase in ("Edit roll", "(this roll)", "Total length (m)", "Delete roll"):
            self.assertNotIn(phrase, html)

    def test_stock_out_is_no_longer_offered_from_the_product_header(self):
        html = self._page()
        self.assertNotIn('id="soOverlay"', html)
        self.assertNotIn("Record stock out", html)
        self.assertIn('id="reReason"', html)
