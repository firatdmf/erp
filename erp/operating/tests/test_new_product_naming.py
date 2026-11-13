import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.attributes import WORDING_VALUE, forget_wordings
from marketing.models import CatalogWording, Product
from operating.models import Warehouse


class NewProductNamingTest(TestCase):
    """A new product on the goods receipt is what was typed for it: its SKU
    spelled as a code, its title as typed — or, with no name of its own, its
    SKU. A name may repeat; a SKU may not."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="naming_tester", password="pw", email="n@a.m")
        self.client.force_login(self.user)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Demfirat")
        self.account = CurrentAccount.objects.create(
            book=book, code="TST-KRV", name="Karven", type="supplier", default_currency=usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=book)

    def _receive(self, name, sku):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({"current_account_id": self.account.pk, "unit": "piece", "products": [{
                "main_product": {"mode": "new", "name": name, "sku": sku},
                "has_variants": True, "unit": "piece",
                "variants": [{"attributes": [{"name": "color", "value": "white"}],
                              "sku": f"{sku}.WHITE", "price": "3", "currency": "USD",
                              "tops": [{"qty": 4}]}],
            }]}),
            content_type="application/json")

    def test_the_typed_name_is_the_title_and_its_code_the_sku(self):
        r = self._receive("Duvet cover", "DUVETCOVER")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(sku="DUVETCOVER").title, "Duvet cover")

    def test_a_product_with_no_name_is_titled_by_its_sku(self):
        r = self._receive("", "2086")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(sku="2086").title, "2086")

    def test_a_name_may_repeat_but_a_sku_may_not(self):
        Product.objects.create(title="Duvet cover", sku="DUVETCOVER", featured=False)
        r = self._receive("Duvet cover", "DUVETCOVER")
        self.assertEqual(r.status_code, 400)
        r = self._receive("Duvet cover", "DC-200")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.filter(title="Duvet cover").count(), 2)

    def test_existing_variants_come_with_their_values_labelled(self):
        self._receive("Duvet cover", "DUVETCOVER")
        pid = Product.objects.get(sku="DUVETCOVER").pk
        r = self.client.get(reverse("operating:catalog_product_variants",
                                    args=[self.warehouse.pk, pid]))
        v = r.json()["results"][0]
        self.assertEqual(v["variant_sku"], "DUVETCOVER.WHITE")
        self.assertEqual(v["shown"], [{"name": "Color", "value": "White"}])

    def test_the_card_asks_whether_a_sku_is_free(self):
        Product.objects.create(title="Duvet cover", sku="DUVETCOVER", featured=False)
        url = reverse("operating:warehouse_product_sku_available")
        taken = self.client.get(url, {"sku": "duvetcover"}).json()
        self.assertEqual(taken, {"available": False, "used_by": "Duvet cover"})
        self.assertTrue(self.client.get(url, {"sku": "DC-200"}).json()["available"])


class VariantNameTest(TestCase):
    """The receipt card's variant name: its values as every page words them,
    in each catalog language."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="v", password="pw")
        self.client.force_login(self.user)
        CatalogWording.objects.create(kind=WORDING_VALUE, scope="color", key="gold+ecru",
                                      language="tr", text="Altın + Ekru")
        forget_wordings()
        self.addCleanup(forget_wordings)

    def test_names_in_each_language(self):
        r = self.client.get(reverse("marketing:variant_name"),
                            {"attrs": json.dumps([["color", "gold+ecru"], ["width", "320"]])})
        names = r.json()["names"]
        self.assertEqual(names["en"], "Gold + ecru 320 cm")
        self.assertEqual(names["tr"], "Altın + Ekru 320 cm")

    def test_nothing_to_read_is_an_empty_name(self):
        r = self.client.get(reverse("marketing:variant_name"), {"attrs": "not json"})
        self.assertEqual(r.json()["names"]["en"], "")
