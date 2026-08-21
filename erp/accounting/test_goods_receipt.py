# to run this test, use the command:
# python manage.py test accounting.test_goods_receipt

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, Invoice, InvoiceItem
from operating.models import Warehouse, WarehouseProduct, WarehouseProductRoll


class GoodsReceiptPageTest(TestCase):
    """Mal kabul — the intake form's own page, reached from the purchases
    list instead of the warehouse sidebar it used to live in."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="receipt_tester", password="pw"
        )
        self.client.force_login(self.user)

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Kızılırmak", type="supplier",
            default_currency=self.usd,
        )

        self.depot = Warehouse.objects.create(name="Fabrika")
        self.store = Warehouse.objects.create(name="Laleli")
        # Combined ("ortak") warehouses hold no stock of their own — nothing
        # can be received into one, so the picker must not offer it.
        self.virtual = Warehouse.objects.create(name="Hepsi", kind="combined")

    def _purchase(self, warehouse=None, number="PO-1"):
        inv = Invoice.objects.create(
            cari=self.cari, book=self.book, series="ALS", number=number,
            type="purchase", status="issued", date=date(2026, 8, 1),
            due_date=date(2026, 8, 31), currency=self.usd,
            total=Decimal("100.00"),
        )
        item = InvoiceItem.objects.create(
            invoice=inv, line_no=1, description="GREK Beyaz",
            quantity=Decimal("50.000"), unit="mt", unit_price=Decimal("2.00"),
        )
        if warehouse is not None:
            wp = WarehouseProduct.objects.create(
                warehouse=warehouse, name="GREK Beyaz", sku="KZL001-BEYAZ",
                quantity=Decimal("50.00"),
            )
            WarehouseProductRoll.objects.create(
                product=wp, meters=Decimal("50.00"), barcode="KZL000001",
                purchase_invoice_item=item,
            )
        return inv

    # ── New ──────────────────────────────────────────────────────────
    def test_new_page_renders_with_a_warehouse_picker(self):
        r = self.client.get(reverse("accounts:goods_receipt"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "accounts/goods_receipt_form.html")
        self.assertContains(r, 'id="npWarehouse"')
        self.assertContains(r, "Fabrika")
        self.assertNotContains(r, "Hepsi")          # combined view isn't intake-able

    def test_new_page_preselects_the_warehouse_it_was_opened_from(self):
        r = self.client.get(reverse("accounts:goods_receipt"), {"warehouse": self.store.pk})
        self.assertContains(r, f'<option value="{self.store.pk}" selected')

    def test_new_page_offers_no_default_when_several_warehouses_exist(self):
        r = self.client.get(reverse("accounts:goods_receipt"))
        self.assertIsNone(r.context["selected_warehouse_id"])

    def test_new_page_preselects_the_only_warehouse(self):
        self.store.delete()
        r = self.client.get(reverse("accounts:goods_receipt"))
        self.assertEqual(r.context["selected_warehouse_id"], self.depot.pk)

    # ── Edit ─────────────────────────────────────────────────────────
    def test_edit_page_opens_on_the_purchase_warehouse(self):
        inv = self._purchase(self.store)
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["selected_warehouse_id"], self.store.pk)
        self.assertContains(r, inv.number)
        # Identity is fixed once stock exists — the warehouse can't change.
        self.assertIsNotNone(r.context["edit_invoice"])
        self.assertRegex(r.content.decode(), r'id="npWarehouse"[^>]*disabled')

    def test_edit_is_refused_when_the_stock_links_are_gone(self):
        inv = self._purchase(warehouse=None)
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv.pk]))
        self.assertRedirects(r, reverse("accounts:purchase_order_detail", args=[inv.pk]))

    def test_edit_is_refused_for_a_cancelled_purchase(self):
        inv = self._purchase(self.store, number="PO-2")
        inv.status = "cancelled"
        inv.save(update_fields=["status"])
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv.pk]))
        self.assertRedirects(r, reverse("accounts:purchase_order_detail", args=[inv.pk]))

    # ── Entry points ────────────────────────────────────────────────
    def test_purchases_list_links_to_the_form(self):
        inv = self._purchase(self.store, number="PO-3")
        r = self.client.get(reverse("accounts:purchase_order_list"))
        self.assertContains(r, reverse("accounts:goods_receipt"))
        self.assertContains(r, reverse("accounts:goods_receipt_edit", args=[inv.pk]))

    def test_warehouse_page_sends_intake_to_the_form(self):
        r = self.client.get(reverse("operating:warehouse_detail", args=[self.depot.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, f'{reverse("accounts:goods_receipt")}?warehouse={self.depot.pk}')
        # The sidebar it replaced is gone for good.
        self.assertNotContains(r, "newProductOverlay")


class GoodsReceiptTranslationTest(TestCase):
    """The page is used in Turkish — its own strings must be in the catalog."""

    def test_new_strings_are_translated(self):
        with translation.override("tr"):
            self.assertEqual(translation.gettext("Goods receipt"), "Mal kabul")
            self.assertEqual(translation.gettext("New goods receipt"), "Yeni mal kabul")
            self.assertEqual(translation.gettext("Incoming delivery"), "Gelen sevkiyat")
            self.assertEqual(
                translation.gettext("Select the warehouse this delivery is received into."),
                "Bu sevkiyatın gireceği depoyu seçin.",
            )
