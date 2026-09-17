import json

from django.contrib.auth.models import User
from django.test import TestCase

from crm.models import Supplier


class GlobalSearchSupplierTests(TestCase):
    """The top-bar search finds suppliers alongside contacts and companies."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("search_admin", password="pw-for-test")
        cls.supplier = Supplier.objects.create(
            company_name="Şişe İplik", contact_name="Ahmet", email="satis@sise.example")

    def setUp(self):
        self.client.force_login(self.user)

    def _results(self, q, type_="all"):
        response = self.client.get("/search/", {"q": q, "type": type_})
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)["results"]

    def test_finds_a_supplier_by_name_ignoring_diacritics(self):
        for q, type_ in (("sise", "all"), ("iplik", "contacts"), ("ahmet", "all")):
            with self.subTest(q=q, type=type_):
                suppliers = [r for r in self._results(q, type_) if r["type"] == "Supplier"]
                self.assertEqual([r["url"] for r in suppliers],
                                 [f"/crm/supplier/detail/{self.supplier.pk}/"])

    def test_finds_a_supplier_by_email(self):
        names = [r["name"] for r in self._results("satis@") if r["type"] == "Supplier"]
        self.assertEqual(names, ["Şişe İplik"])

    def test_suppliers_stay_out_of_the_products_tab(self):
        self.assertNotIn("Supplier", {r["type"] for r in self._results("sise", "products")})
