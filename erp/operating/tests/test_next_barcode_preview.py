# to run this test, use the command:
# python manage.py test operating.tests.test_next_barcode_preview

"""The label a roll will carry, shown before it is saved.

The goods-receipt page fills every blank barcode box with the code that
row is about to be given, so what is printed is visible while the delivery
is still being typed. The codes come from the same minter the save uses.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class NextBarcodePreviewTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Laleli Fabric")
        self.wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.user = get_user_model().objects.create_superuser(
            username="firat_bc", password="pw", email="a@b.c")
        self.client.force_login(self.user)

    def _ask(self, prefix):
        r = self.client.get(reverse("operating:warehouse_next_barcode", args=[self.wh.pk]),
                            {"prefix": prefix})
        self.assertEqual(r.status_code, 200)
        return r.json()["barcode"]

    def test_the_first_code_of_an_unused_prefix(self):
        self.assertEqual(self._ask("KZL"), "KZL000001")

    def test_it_carries_on_from_the_codes_already_in_stock(self):
        wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="Krep", sku="KZL001", quantity=Decimal("0"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("30"), quantity_remaining=Decimal("30"),
            barcode="KZL000007", status="in_stock")
        self.assertEqual(self._ask("KZL"), "KZL000008")

    def test_a_prefix_is_upper_cased_and_kept_short(self):
        self.assertEqual(self._ask("kzl"), "KZL000001")
        self.assertTrue(self._ask("abcdefghij").startswith("ABCDEF"))

    def test_no_prefix_falls_back_to_the_house_code(self):
        self.assertRegex(self._ask(""), r"^[A-Z]+\d{6}$")
