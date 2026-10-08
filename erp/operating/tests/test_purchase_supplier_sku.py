# to run this test, use the command:
# python manage.py test operating.tests.test_purchase_supplier_sku

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, CurrentAccount
from marketing.models import ProductVariant, SupplierItem
from marketing.supplier_items import find_variant
from operating.models import Warehouse, WarehouseProduct


class PurchaseRecordsTheSupplierSkuTest(TestCase):
    """A purchase row carries two codes. OURS is the variant's SKU, and the
    warehouse row's — the two are the same string, which is what "synced"
    means. THEIRS is what the supplier prints on the invoice; it is kept
    against their account, so one of our variants can be bought from several
    mills that each call it something else (Sable ecru was on the shelf
    twice, once under each mill's code, because there was only one box).
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="buyer", password="pw", email="b@u.y")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.karven = self._account("SUP-KRV", "Karven")
        self.lazik = self._account("SUP-LZK", "Lazik")
        self.warehouse = Warehouse.objects.create(name="Laleli", accounting_book=self.book)

    def _account(self, code, name):
        return CurrentAccount.objects.create(
            book=self.book, code=code, name=name, type="supplier", default_currency=self.usd)

    def _receive(self, account, main, *, supplier_sku=None, price="1.60",
                 sku="SABLE.ECRU"):
        row = {"name": "Ecru", "sku": sku, "price": price, "currency": "USD",
               "tops": [{"qty": 30}]}
        if supplier_sku is not None:
            row["supplier_sku"] = supplier_sku
        r = self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({"current_account_id": account.pk, "unit": "mt",
                             "products": [{"main_product": main, "has_variants": True,
                                           "variants": [row]}]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["success"], r.json())
        return r.json()

    def _first(self, **kw):
        return self._receive(self.karven, {"mode": "new", "name": "Sable", "sku": "SABLE"}, **kw)

    def _again(self, account, **kw):
        variant = ProductVariant.objects.get(variant_sku="SABLE.ECRU")
        return self._receive(account, {"mode": "existing", "id": variant.product_id}, **kw)

    def test_their_code_is_kept_against_their_account(self):
        self._first(supplier_sku="3002")
        item = SupplierItem.objects.get()
        self.assertEqual((item.current_account, item.variant.variant_sku, item.supplier_sku),
                         (self.karven, "SABLE.ECRU", "3002"))
        self.assertEqual((item.last_unit_price, item.last_price_currency),
                         (Decimal("1.6000"), "USD"))
        self.assertIsNotNone(item.last_purchased_at)

    def test_the_shelf_and_the_catalog_carry_ours_not_theirs(self):
        self._first(supplier_sku="3002")
        row = WarehouseProduct.objects.get()
        self.assertEqual(row.sku, "SABLE.ECRU")
        self.assertEqual(row.catalog_variant.variant_sku, "SABLE.ECRU")
        self.assertFalse(ProductVariant.objects.filter(variant_sku="3002").exists())

    def test_a_second_mill_is_a_second_code_on_the_same_variant(self):
        self._first(supplier_sku="3002")
        self._again(self.lazik, supplier_sku="LZK0000120", price="1.75")
        self.assertEqual(WarehouseProduct.objects.count(), 1)
        self.assertEqual(ProductVariant.objects.count(), 1)
        self.assertEqual(
            sorted(SupplierItem.objects.values_list("current_account__name", "supplier_sku")),
            [("Karven", "3002"), ("Lazik", "LZK0000120")])
        self.assertEqual(find_variant(self.lazik, "lzk0000120").variant_sku, "SABLE.ECRU")
        self.assertIsNone(find_variant(self.karven, "LZK0000120"))

    def test_a_purchase_without_their_code_still_says_who_sells_it(self):
        self._first()
        item = SupplierItem.objects.get()
        self.assertEqual((item.supplier_sku, item.last_unit_price), ("", Decimal("1.6000")))

    def test_a_later_purchase_without_the_field_keeps_their_code(self):
        self._first(supplier_sku="3002")
        self._again(self.karven, price="1.70")
        item = SupplierItem.objects.get()
        self.assertEqual((item.supplier_sku, item.last_unit_price), ("3002", Decimal("1.7000")))

    def test_many_variants_may_wait_for_their_code(self):
        self._first()
        self._receive(self.karven, {"mode": "new", "name": "Tergal", "sku": "TERGAL"},
                      sku="TERGAL.ECRU")
        self.assertEqual(SupplierItem.objects.filter(supplier_sku="").count(), 2)

    def _try(self, account, main, **row):
        row = {"name": "Ecru", "price": "1.60", "currency": "USD", "tops": [{"qty": 30}], **row}
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({"current_account_id": account.pk, "unit": "mt",
                             "products": [{"main_product": main, "has_variants": True,
                                           "variants": [row]}]}),
            content_type="application/json")

    def test_a_code_they_use_for_another_variant_is_refused(self):
        """One of their codes means one of our variants. This used to be a
        warning on a receipt that went in anyway, with the code dropped."""
        self._first(supplier_sku="3002")
        r = self._try(self.karven, {"mode": "new", "name": "Tergal", "sku": "TERGAL"},
                      sku="TERGAL.ECRU", supplier_sku="3002")
        self.assertEqual(r.status_code, 409, r.content)
        self.assertIn("SABLE.ECRU", r.json()["error"])
        # Nothing of the refused delivery was written.
        self.assertFalse(WarehouseProduct.objects.filter(sku="TERGAL.ECRU").exists())
        self.assertFalse(ProductVariant.objects.filter(variant_sku="TERGAL.ECRU").exists())
        self.assertEqual(SupplierItem.objects.count(), 1)

    def test_another_supplier_may_use_the_same_code_for_something_else(self):
        self._first(supplier_sku="3002")
        self._receive(self.lazik, {"mode": "new", "name": "Tergal", "sku": "TERGAL"},
                      sku="TERGAL.ECRU", supplier_sku="3002")
        self.assertEqual(find_variant(self.lazik, "3002").variant_sku, "TERGAL.ECRU")
        self.assertEqual(find_variant(self.karven, "3002").variant_sku, "SABLE.ECRU")

    def test_one_purchase_cannot_put_a_code_on_two_variants(self):
        r = self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({"current_account_id": self.karven.pk, "unit": "mt", "products": [{
                "main_product": {"mode": "new", "name": "Sable", "sku": "SABLE"},
                "has_variants": True,
                "variants": [
                    {"name": "Ecru", "sku": "SABLE.ECRU", "supplier_sku": "3002",
                     "price": "1", "currency": "USD", "tops": [{"qty": 5}]},
                    {"name": "White", "sku": "SABLE.WHITE", "supplier_sku": "3002",
                     "price": "1", "currency": "USD", "tops": [{"qty": 5}]}]}]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 409, r.content)
        self.assertFalse(WarehouseProduct.objects.exists())

    def test_a_draft_order_is_refused_the_same_way(self):
        self._first(supplier_sku="3002")
        r = self.client.post(
            reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
            data=json.dumps({
                "warehouse_id": self.warehouse.pk, "current_account_id": self.karven.pk,
                "products": [{"main_product": {"mode": "new", "name": "Tergal", "sku": "TERGAL"},
                              "has_variants": True,
                              "variants": [{"name": "Ecru", "sku": "TERGAL.ECRU",
                                            "supplier_sku": "3002", "price": "1",
                                            "currency": "USD", "tops": [{"qty": 5}]}]}]}),
            content_type="application/json")
        self.assertEqual(r.status_code, 409, r.content)

    def test_the_page_is_given_only_the_chosen_accounts_codes(self):
        self._first(supplier_sku="3002")
        self._again(self.lazik, supplier_sku="LZK0000120")
        url = reverse("operating:supplier_codes", args=[self.warehouse.pk])
        codes = self.client.get(url, {"account": self.karven.pk}).json()["codes"]
        self.assertEqual([(c["supplier_sku"], c["variant_sku"]) for c in codes],
                         [("3002", "SABLE.ECRU")])

    def test_their_code_finds_the_product(self):
        self._first(supplier_sku="3002")
        url = reverse("operating:catalog_base_search", args=[self.warehouse.pk])
        found = self.client.get(url, {"q": "3002", "account": self.karven.pk}).json()["results"]
        self.assertEqual([p["sku"] for p in found], ["SABLE"])
        # ...only for the account whose code it is.
        self.assertEqual(
            self.client.get(url, {"q": "3002", "account": self.lazik.pk}).json()["results"], [])

    def test_a_code_is_put_right_on_the_product_page(self):
        self._first(supplier_sku="3002")
        self._receive(self.karven, {"mode": "new", "name": "Tergal", "sku": "TERGAL"},
                      sku="TERGAL.ECRU", supplier_sku="5005")
        sable = SupplierItem.objects.get(variant__variant_sku="SABLE.ECRU")
        tergal = SupplierItem.objects.get(variant__variant_sku="TERGAL.ECRU")
        post = lambda item, body: self.client.post(
            reverse("marketing:supplier_item_update", args=[item.pk]),
            data=json.dumps(body), content_type="application/json")
        # Taken: refused, and says by what.
        r = post(tergal, {"supplier_sku": "3002"})
        self.assertEqual(r.status_code, 409)
        self.assertIn("SABLE.ECRU", r.json()["error"])
        # Taken off the one, it can go on the other.
        self.assertTrue(post(sable, {"supplier_sku": ""}).json()["success"])
        self.assertTrue(post(tergal, {"supplier_sku": "3002"}).json()["success"])
        self.assertEqual(find_variant(self.karven, "3002").variant_sku, "TERGAL.ECRU")
        self.assertTrue(post(sable, {"remove": True}).json()["removed"])
        self.assertFalse(SupplierItem.objects.filter(pk=sable.pk).exists())

    def test_the_product_page_lists_its_suppliers(self):
        self._first(supplier_sku="3002")
        variant = ProductVariant.objects.get()
        r = self.client.get(reverse("marketing:product_detail", args=[variant.product_id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([(row.current_account.name, row.supplier_sku)
                          for row in r.context["product_suppliers"]], [("Karven", "3002")])
        self.assertContains(r, 'value="3002"')

    def test_the_purchase_page_is_told_who_else_sells_a_variant(self):
        self._first(supplier_sku="3002")
        self._again(self.lazik, supplier_sku="LZK0000120", price="1.75")
        variant = ProductVariant.objects.get()
        r = self.client.get(reverse("operating:catalog_product_variants",
                                    args=[self.warehouse.pk, variant.product_id]))
        suppliers = r.json()["results"][0]["suppliers"]
        self.assertEqual(
            sorted((s["account"], s["supplier_sku"], s["last_price"], s["currency"])
                   for s in suppliers),
            [("Karven", "3002", 1.6, "USD"), ("Lazik", "LZK0000120", 1.75, "USD")])
