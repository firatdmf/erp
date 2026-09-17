# to run this test, use the command:
# python manage.py test accounting.test_goods_receipt

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice, InvoiceItem
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


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
        self.user.member.books.add(self.book)
        self.current_account = CurrentAccount.objects.create(
            book=self.book, code="TST-001", name="Kızılırmak", type="supplier",
            default_currency=self.usd,
        )

        self.depot = Warehouse.objects.create(name="Fabrika",
                                              accounting_book=self.book)
        self.store = Warehouse.objects.create(name="Laleli",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        # Combined ("ortak") warehouses hold no stock of their own — nothing
        # can be received into one, so the picker must not offer it.
        self.virtual = Warehouse.objects.create(name="Hepsi",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0], kind="combined")

    def _purchase(self, warehouse=None, number="PO-1"):
        inv = Invoice.objects.create(
            current_account=self.current_account, book=self.book, series="ALS", number=number,
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
            WarehouseProductItem.objects.create(
                product=wp, quantity=Decimal("50.00"), barcode="KZL000001",
                purchase_invoice_item=item,
            )
        return inv

    # ── New ──────────────────────────────────────────────────────────
    def test_new_page_renders_with_a_warehouse_picker(self):
        r = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "accounts/goods_receipt_form.html")
        self.assertContains(r, 'id="npWarehouse"')
        self.assertContains(r, "Fabrika")
        self.assertNotContains(r, "Hepsi")          # combined view isn't intake-able

    def test_new_page_preselects_the_warehouse_it_was_opened_from(self):
        r = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}), {"warehouse": self.store.pk})
        self.assertContains(r, f'<option value="{self.store.pk}" selected')

    def test_new_page_offers_no_default_when_several_warehouses_exist(self):
        r = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}))
        self.assertIsNone(r.context["selected_warehouse_id"])

    def test_new_page_preselects_the_only_warehouse(self):
        self.store.delete()
        r = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}))
        self.assertEqual(r.context["selected_warehouse_id"], self.depot.pk)

    # ── Edit ─────────────────────────────────────────────────────────
    def test_edit_page_opens_on_the_purchase_warehouse(self):
        inv = self._purchase(self.store)
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["selected_warehouse_id"], self.store.pk)
        self.assertContains(r, inv.number)
        # Still pickable once stock exists: saving another warehouse moves
        # the rolls there (see accounting.test_received_purchase_edit).
        self.assertIsNotNone(r.context["edit_invoice"])
        self.assertNotRegex(r.content.decode(), r'id="npWarehouse"[^>]*disabled')

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
        r = self.client.get(reverse("accounts:purchase_order_list", kwargs={"book_id": self.book.pk}))
        self.assertContains(r, reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}))
        self.assertContains(r, reverse("accounts:goods_receipt_edit", args=[inv.pk]))

    def test_warehouse_page_sends_intake_to_the_form(self):
        r = self.client.get(reverse("operating:warehouse_detail", args=[self.depot.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(
            r, f'{reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk})}?warehouse={self.depot.pk}')
        # The sidebar it replaced is gone for good.
        self.assertNotContains(r, "newProductOverlay")


class GoodsReceiptTranslationTest(TestCase):
    """The page is used in Turkish — its own strings must be in the catalog."""

    def test_product_groups_follow_the_language(self):
        from marketing.models import ProductCategory
        from operating.views_warehouse import _product_category_choices

        ProductCategory.objects.get_or_create(name="fabric")
        for lang, label in (("en", "Fabric"), ("tr", "Kumaş")):
            with self.subTest(lang=lang), translation.override(lang):
                fabric = _product_category_choices()[0]
                self.assertEqual((fabric["name"], fabric["label"]), ("fabric", label))

    def test_pack_words_are_translated(self):
        from operating.views_warehouse import _pack_type_choices

        with translation.override("tr"):
            box = {c["value"]: c for c in _pack_type_choices()["choices"]}["box"]
            self.assertEqual((box["label"], box["one"], box["many"]), ("Kutu", "kutu", "kutu"))
            self.assertEqual(translation.gettext("Packed as"), "Ambalaj türü")
            self.assertEqual(translation.gettext("Add {item}"), "{Item} ekle")

    def test_new_strings_are_translated(self):
        with translation.override("tr"):
            self.assertEqual(translation.gettext("Goods receipt"), "Mal kabul")
            self.assertEqual(translation.gettext("New goods receipt"), "Yeni mal kabul")
            self.assertEqual(translation.gettext("Incoming delivery"), "Gelen sevkiyat")
            self.assertEqual(
                translation.gettext("Select the warehouse this delivery is received into."),
                "Bu sevkiyatın gireceği depoyu seçin.",
            )


class InlineAccountCarriesItsCurrencyTest(TestCase):
    """The goods-receipt page prices a delivery in the account's currency by
    default, so an account created or found from its search box has to say
    which currency that is."""

    def setUp(self):
        user = get_user_model().objects.create_superuser("acc_maker", "a@m.t", "pw")
        self.client.force_login(user)
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="TL")
        self.book = Book.objects.create(name="Demfirat")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()

    def _create(self, name, currency=None, status=200):
        import json
        body = {"name": name}
        if currency is not None:
            body["currency"] = currency
        r = self.client.post(reverse("operating:warehouse_account_create"),
                             data=json.dumps(body), content_type="application/json")
        self.assertEqual(r.status_code, status, r.content)
        return r.json()

    def test_an_existing_account_says_its_currency(self):
        """Found by name, it keeps its own currency — none is asked for."""
        CurrentAccount.objects.create(book=self.book, code="K-1", name="Kızılırmak",
                                      type="supplier", default_currency=self.try_)
        d = self._create("kizilirmak")
        self.assertEqual((d["created"], d["currency"]), (False, "TRY"))

    def test_a_new_account_is_kept_in_the_currency_chosen(self):
        d = self._create("Yeni Tedarikçi", currency="try")
        self.assertTrue(d["created"])
        self.assertEqual(d["currency"], "TRY")
        self.assertEqual(CurrentAccount.objects.get(pk=d["id"]).default_currency, self.try_)

    def test_a_new_account_needs_a_currency(self):
        for currency in (None, "", "XXX"):
            with self.subTest(currency=currency):
                d = self._create("Para Birimsiz", currency=currency, status=400)
                self.assertFalse(d["success"])
        self.assertFalse(CurrentAccount.objects.filter(name="Para Birimsiz").exists())
