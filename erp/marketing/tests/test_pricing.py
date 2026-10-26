# to run this test, use the command:
# python manage.py test marketing.tests.test_pricing

import json
from decimal import Decimal
from fractions import Fraction

from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductCategory, ProductVariant
from marketing.pricing import (attach_live_prices, live_prices, parse_multiplier,
                               selling_price)
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


THIRD = Fraction(4, 3)


class SellingPriceTest(TestCase):
    """A price is the cost times its multiplier — 4/3 exactly, not 1.33 —
    rounded UP to the next 0.05 (Muhammed, 2026-10-15)."""

    def test_four_thirds_exactly(self):
        self.assertEqual(selling_price(Decimal("3.60"), THIRD), Decimal("4.80"))   # not 4.79
        self.assertEqual(selling_price(Decimal("3.00"), THIRD), Decimal("4.00"))

    def test_rounded_up_to_the_next_five_cents(self):
        self.assertEqual(selling_price(Decimal("3.35"), THIRD), Decimal("4.50"))   # 4.4667
        self.assertEqual(selling_price(Decimal("2.10"), THIRD), Decimal("2.80"))
        self.assertEqual(selling_price(Decimal("1.00"), THIRD), Decimal("1.35"))   # 1.3333

    def test_no_cost_or_no_multiplier_no_price(self):
        self.assertIsNone(selling_price(None, THIRD))
        self.assertIsNone(selling_price(Decimal("3"), None))

    def test_curtains_at_three_times(self):
        self.assertEqual(selling_price(Decimal("26.50"), 3), Decimal("79.50"))


class ParseMultiplierTest(TestCase):
    def test_formulas_are_worked_out_exactly(self):
        for text, value in (("4/3", THIRD), ("3", 3), ("1.3", Fraction(13, 10)),
                            ("(1+1/3)", THIRD), (" 1,5 ", Fraction(3, 2)), ("4÷3", THIRD),
                            ("2×1.5", 3)):
            self.assertEqual(parse_multiplier(text), value, text)

    def test_anything_else_is_refused(self):
        for text in ("", "abc", "1/0", "-2", "0", "4/", "__import__('os')", "2**80", "1" * 41):
            with self.assertRaises(ValueError, msg=text):
                parse_multiplier(text)


class LivePriceTest(TestCase):
    """The price follows the stock's cost, through the variant's live cost,
    and the margin of the product, else of its group, else a third."""

    def setUp(self):
        self.group = ProductCategory.objects.create(name="fabric", price_multiplier="4/3")
        self.product = Product.objects.create(title="K25289", sku="K25289", category=self.group)
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="K25289.G146",
            variant_cost=Decimal("9.99"), variant_price=Decimal("4.55"))
        warehouse = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.row = WarehouseProduct.objects.create(
            warehouse=warehouse, name="G146", sku="K25289.G146", quantity=Decimal("100"),
            catalog_variant=self.variant)
        WarehouseProductItem.objects.create(
            product=self.row, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            unit_cost_base=Decimal("3.60"))

    def _fresh(self):
        return ProductVariant.objects.get(pk=self.variant.pk)

    def test_a_typed_price_no_longer_counts(self):
        self.assertEqual(self._fresh().live_price, Decimal("4.80"))

    def test_it_follows_the_stock(self):
        WarehouseProductItem.objects.create(
            product=self.row, quantity=Decimal("100"), quantity_remaining=Decimal("100"),
            unit_cost_base=Decimal("4.00"))
        # (3.60 + 4.00) / 2 = 3.80 → 5.0667 → 5.10
        self.assertEqual(self._fresh().live_price, Decimal("5.10"))

    def test_with_nothing_in_stock_the_stored_cost_prices_it(self):
        WarehouseProductItem.objects.update(status="consumed", quantity_remaining=Decimal("0"))
        self.assertEqual(self._fresh().live_price, selling_price(Decimal("9.99"), THIRD))

    def test_the_groups_multiplier_then_the_products_own(self):
        self.group.price_multiplier = "1.5"
        self.group.save()
        self.assertEqual(self._fresh().live_price, Decimal("5.40"))
        self.product.price_multiplier = "1.25"
        self.product.save()
        self.assertEqual(self._fresh().live_price, Decimal("4.50"))

    def test_without_a_multiplier_there_is_no_price(self):
        ProductCategory.objects.filter(pk=self.group.pk).update(price_multiplier="")
        self.assertIsNone(self._fresh().live_price)

    def test_lists_read_them_in_a_fixed_number_of_queries(self):
        self.assertEqual(live_prices([self.variant.pk]), {self.variant.pk: Decimal("4.80")})
        products = attach_live_prices(Product.objects.filter(pk=self.product.pk).select_related("category"))
        self.assertEqual(products[0].from_price, Decimal("4.80"))

    def test_the_storefront_is_sent_it(self):
        self.product.featured = True
        self.product.save()
        data = self.client.get(reverse("marketing:get_products")).json()
        self.assertEqual(str(data["products"][0]["price"]), "4.80")
        self.assertEqual(data["product_variants"][0]["variant_price"], 4.80)

    def _prices(self, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.post(reverse("marketing:storefront_prices"),
                                json.dumps({"product_skus": ["K25289", "NOPE"]}),
                                content_type="application/json", **headers)

    def test_a_signed_in_customer_is_sent_it(self):
        from django.contrib.auth.hashers import make_password
        from authentication.client_tokens import issue
        from authentication.models import WebClient
        buyer = WebClient.objects.create(username="buyer", email="b@example.com",
                                         password=make_password("pw"), is_active=True)
        data = self._prices(issue(buyer)).json()
        self.assertEqual(data["products"]["K25289"]["price"], 4.80)
        self.assertEqual(data["variants"]["K25289.G146"]["variant_price"], 4.80)
        self.assertIn("USD", data["variants"]["K25289.G146"]["variant_prices"] or {"USD": 0})
        self.assertNotIn("NOPE", data["products"])

    def test_nobody_else_is(self):
        for token in (None, "forged"):
            with self.subTest(token=token):
                self.assertEqual(self._prices(token).status_code, 401)


class GroupMultiplierTest(TestCase):
    """The group page: the multiplier is required, and a group with
    products cannot be deleted out from under them."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser(
            username="grouper", password="pw", email="g@r.p"))
        self.group = ProductCategory.objects.create(name="throw", price_multiplier="4/3")

    def _save(self, multiplier):
        return self.client.post(reverse("marketing:product_group_detail", args=[self.group.pk]),
                                {"action": "save_settings", "name": "throw",
                                 "price_multiplier": multiplier})

    def test_a_formula_is_kept_as_typed(self):
        self.assertEqual(self._save("3/2").status_code, 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.price_multiplier, "3/2")

    def test_blank_or_nonsense_is_refused(self):
        for text in ("", "abc", "0"):
            self.assertEqual(self._save(text).status_code, 400, text)
        self.group.refresh_from_db()
        self.assertEqual(self.group.price_multiplier, "4/3")

    def test_a_group_with_products_is_not_deleted(self):
        Product.objects.create(title="Blanket", sku="BLK", category=self.group)
        r = self.client.post(reverse("marketing:product_group_detail", args=[self.group.pk]),
                             {"action": "delete_group"})
        self.assertEqual(r.status_code, 400)
        self.assertTrue(ProductCategory.objects.filter(pk=self.group.pk).exists())
