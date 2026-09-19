# to run this test, use the command:
# python manage.py test operating.tests.test_order_variant_lines

"""A variant reads the same way on every line of an order.

The attribute values are a plain many-to-many with no ordering of its
own, so the database handed them back in whatever order it liked: one
line of order 303 said "cactus_green / 160 x 200 cm" and the next
"100 x 200 cm / cappuccino" — same two attributes, swapped. A reader
scanning the column could not compare colour with colour. They are now
sorted by the attribute's name, and the page prints one per line rather
than running them together with slashes.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import (
    Product, ProductVariant, ProductVariantAttribute,
    ProductVariantAttributeValue,
)
from operating.models import Order, OrderItem
from operating.views import _order_item_variant_lines


class OrderVariantLinesTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            title="Ready Made Curtain", sku="RMC", featured=False)
        self.colour = ProductVariantAttribute.objects.create(name="color")
        self.size = ProductVariantAttribute.objects.create(name="size")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-303", name="Oleg", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.user = get_user_model().objects.create_superuser(
            "firat_variant", "a@b.c", "pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()

    def _variant(self, sku, pairs):
        v = ProductVariant.objects.create(product=self.product, variant_sku=sku)
        for attr, value in pairs:
            row, _ = ProductVariantAttributeValue.objects.get_or_create(
                product_variant_attribute=attr,
                product_variant_attribute_value=value)
            v.product_variant_attribute_values.add(row)
        return v

    def _item(self, variant):
        order = Order.objects.create(current_account=self.account)
        return OrderItem.objects.create(
            order=order, product=self.product, product_variant=variant,
            quantity=Decimal("1"), price=Decimal("10"))

    # ── The order of the values ─────────────────────────────────────
    def test_the_colour_comes_before_the_size_whichever_way_it_was_added(self):
        """Added size-first or colour-first, both lines read alike."""
        colour_first = self._variant("V-1", ((self.colour, "cactus_green"),
                                             (self.size, "160 x 200 cm")))
        size_first = self._variant("V-2", ((self.size, "100 x 200 cm"),
                                           (self.colour, "cappuccino")))
        self.assertEqual(_order_item_variant_lines(self._item(colour_first)),
                         ["Cactus green", "160 x 200 cm"])
        self.assertEqual(_order_item_variant_lines(self._item(size_first)),
                         ["Cappuccino", "100 x 200 cm"])

    # ── How a value is spelled ──────────────────────────────
    def test_the_stored_underscores_are_not_shown_to_anyone(self):
        """Storage keeps the slug; the page reads like a sentence."""
        v = self._variant("V-SLUG", ((self.colour, "cactus_green"),))
        self.assertEqual(_order_item_variant_lines(self._item(v)),
                         ["Cactus green"])

    def test_a_width_prints_the_unit_it_is_measured_in(self):
        """Widths are stored bare ("250"). On a line of its own a bare
        number says nothing — a size beside it already reads
        "160 x 200 cm"."""
        width = ProductVariantAttribute.objects.create(name="width")
        v = self._variant("V-WIDTH", ((width, "250"),))
        self.assertEqual(_order_item_variant_lines(self._item(v)), ["250 cm"])

    def test_a_width_someone_typed_the_unit_into_is_left_alone(self):
        width = ProductVariantAttribute.objects.create(name="width")
        v = self._variant("V-WIDTH-CM", ((width, "150cm"),))
        self.assertEqual(_order_item_variant_lines(self._item(v)), ["150cm"])

    def test_a_line_with_no_variant_has_nothing_to_print(self):
        item = self._item(None)
        self.assertEqual(_order_item_variant_lines(item), [])

    # ── How the page prints them ────────────────────────────────────
    def test_the_page_puts_each_value_on_its_own_line(self):
        item = self._item(self._variant("V-3", ((self.colour, "cactus_green"),
                                                (self.size, "160 x 200 cm"))))
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("operating:order_detail", kwargs={"pk": item.order.pk}))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("<span>Cactus green</span><span>160 x 200 cm</span>", html)
        self.assertNotIn("cactus_green", html)
