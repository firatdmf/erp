"""A catalogue price or cost is never below zero.

Product.price/.cost and ProductVariant.variant_price/.variant_cost took any
number, negatives included. None exist in production (checked 2026-09-12:
0 of 1008 products, 0 of 2156 variants, every brand schema), so this is a
guard, not a cleanup. Zero stays allowed; 2 products and 4 variants use it.

Two layers, because most price writes never call full_clean():

* a MinValueValidator on each field, so the product form puts the message
  on the field;
* a CHECK constraint on each column, which is what holds for the variant
  JSON (bulk_update), group margin repricing (bulk_update), and the
  warehouse catalogue sync.

Each of those three writers now checks first, so a bad value is a readable
error rather than an IntegrityError halfway through a save.

Run with:
    python manage.py test marketing.tests.test_non_negative_prices
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from marketing.forms import _skus_with_negative_money
from marketing.models import Product, ProductCategory, ProductVariant


class TheFieldsRefuseANegativeValue(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="Linen", sku="LIN1")

    def test_a_negative_product_price_or_cost_fails_validation_on_that_field(self):
        for field in ("price", "cost"):
            product = Product(title="Bad", sku=f"BAD-{field}", **{field: Decimal("-0.01")})
            with self.assertRaises(ValidationError) as caught:
                product.full_clean()
            self.assertIn(field, caught.exception.message_dict)

    def test_a_negative_variant_price_or_cost_fails_validation_on_that_field(self):
        for field in ("variant_price", "variant_cost"):
            variant = ProductVariant(product=self.product, variant_sku=f"V-{field}",
                                     **{field: Decimal("-5")})
            with self.assertRaises(ValidationError) as caught:
                variant.full_clean()
            self.assertIn(field, caught.exception.message_dict)

    def test_zero_and_blank_are_still_fine(self):
        Product(title="Free", sku="FREE", price=Decimal("0"), cost=Decimal("0")).full_clean()
        Product(title="Unpriced", sku="UNPRICED", price=None, cost=None).full_clean()
        ProductVariant(product=self.product, variant_sku="V0",
                       variant_price=Decimal("0"), variant_cost=None).full_clean()


class TheDatabaseRefusesItWithoutFullClean(TestCase):
    """bulk_update and .save() skip validators entirely; the constraint does not."""

    def setUp(self):
        self.product = Product.objects.create(title="Linen", sku="LIN1")
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="LIN1-A")

    def assert_refused(self, write):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                write()

    def test_product_price_and_cost(self):
        for field in ("price", "cost"):
            setattr(self.product, field, Decimal("-1"))
            self.assert_refused(lambda: Product.objects.bulk_update([self.product], [field]))
            setattr(self.product, field, None)

    def test_variant_price_and_cost(self):
        for field in ("variant_price", "variant_cost"):
            setattr(self.variant, field, Decimal("-1"))
            self.assert_refused(lambda: self.variant.save(update_fields=[field]))
            setattr(self.variant, field, None)


class TheProductFormChecksItsVariantsFirst(TestCase):
    """Variants ride in the POST as JSON and are written after the product.
    The form has to catch a negative one before either is saved."""

    def test_it_names_each_variant_with_a_negative_price_or_cost(self):
        payload = json.dumps({"product_variant_list": [
            {"variant_sku": "OK-1", "variant_price": "12.50", "variant_cost": 4},
            {"variant_sku": "BAD-PRICE", "variant_price": "-3"},
            {"variant_sku": "BAD-COST", "variant_cost": -0.01},
            {"variant_sku": "ZERO", "variant_price": 0},
        ]})
        self.assertEqual(_skus_with_negative_money(payload), {"BAD-PRICE", "BAD-COST"})

    def test_the_form_itself_refuses_them_before_saving(self):
        from marketing.forms import ProductForm

        payload = json.dumps([{"variant_sku": "BAD-PRICE", "variant_price": "-3"}])
        form = ProductForm(data={"title": "Drape", "sku": "DRP9", "variants_json": payload})

        self.assertFalse(form.is_valid())
        self.assertIn("BAD-PRICE", " ".join(form.non_field_errors()))
        self.assertFalse(Product.objects.filter(sku="DRP9").exists())

    def test_the_form_is_quiet_when_the_variants_are_fine(self):
        from marketing.forms import ProductForm

        payload = json.dumps([{"variant_sku": "OK", "variant_price": "3"}])
        form = ProductForm(data={"title": "Drape", "sku": "DRP9", "variants_json": payload})
        form.is_valid()

        self.assertEqual(list(form.non_field_errors()), [])

    def test_it_accepts_the_bare_list_shape_too(self):
        payload = json.dumps([{"variant_sku": "BAD", "variant_price": -1}])
        self.assertEqual(_skus_with_negative_money(payload), {"BAD"})

    def test_blank_and_junk_values_are_left_to_the_existing_handling(self):
        for payload in (None, "", "[]", "not json", json.dumps({"x": 1}),
                        json.dumps([{"variant_sku": "A", "variant_price": ""},
                                    {"variant_sku": "B", "variant_price": "abc"},
                                    "not-a-dict"])):
            self.assertEqual(_skus_with_negative_money(payload), set(), payload)


class GroupRepricingRefusesAMarginThatGoesBelowZero(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="pricer", password="x")
        self.client.force_login(user)
        self.group = ProductCategory.objects.create(name="Curtains", profit_margin=Decimal("40"))
        self.product = Product.objects.create(
            title="Drape", sku="DRP1", category=self.group,
            cost=Decimal("10"), price=Decimal("14"))
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="DRP1-A",
            variant_cost=Decimal("20"), variant_price=Decimal("28"))

    def apply(self):
        return self.client.post(
            reverse("marketing:product_group_detail", args=[self.group.pk]),
            {"action": "apply_margin"})

    def test_a_normal_margin_still_reprices(self):
        self.group.profit_margin = Decimal("50")
        self.group.save()

        response = self.apply()

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("15.00"))
        self.assertEqual(self.variant.variant_price, Decimal("30.00"))

    def test_minus_one_hundred_prices_at_zero_which_is_allowed(self):
        self.group.profit_margin = Decimal("-100")
        self.group.save()

        self.assertEqual(self.apply().status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("0.00"))

    def test_below_minus_one_hundred_is_refused_and_nothing_is_written(self):
        self.product.profit_margin = Decimal("-150")   # the product's own override
        self.product.save()

        response = self.apply()

        self.assertEqual(response.status_code, 400)
        self.assertIn("DRP1", response.json()["error"])
        self.product.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("14"))
        self.assertEqual(self.variant.variant_price, Decimal("28"))

    def test_a_bad_margin_on_a_product_with_no_cost_blocks_nothing(self):
        """It would never be repriced, so it is not a reason to stop."""
        Product.objects.create(title="Uncosted", sku="NOCOST", category=self.group,
                               profit_margin=Decimal("-500"))

        self.assertEqual(self.apply().status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("14.00"))


class TheWarehouseSyncDoesNotMirrorANegativeCost(TestCase):
    def test_the_variant_is_still_created_just_without_the_cost(self):
        from operating.catalog_sync import sync_roll_to_catalog

        _, variant, _, created = sync_roll_to_catalog(
            base_name="K1245", attribute_name="color", attribute_value="blue",
            variant_sku="K1245.G13", cost="-7.50")

        self.assertTrue(created)
        self.assertIsNone(variant.variant_cost)

    def test_a_real_cost_still_comes_through(self):
        from operating.catalog_sync import sync_roll_to_catalog

        _, variant, _, _ = sync_roll_to_catalog(
            base_name="K1246", attribute_name="color", attribute_value="red",
            variant_sku="K1246.G14", cost="7.50")

        self.assertEqual(variant.variant_cost, Decimal("7.50"))
