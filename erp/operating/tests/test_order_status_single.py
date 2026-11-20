from decimal import Decimal

from django.test import TestCase

from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem


class OneOrderStatusTest(TestCase):
    """An order has one status, status. Its lines' production
    statuses no longer roll up into a second one, so a line edit leaves
    the order alone, and nothing reads the retired field."""

    def setUp(self):
        self.order = Order.objects.create()
        product = Product.objects.create(title="LINE", sku="LINE")
        self.line = OrderItem.objects.create(
            order=self.order, product=product,
            product_variant=ProductVariant.objects.create(product=product, variant_sku="LINE.WHITE"),
            quantity=Decimal("2"), price=Decimal("5"))

    def test_a_finished_line_does_not_touch_the_order(self):
        before = Order.objects.get(pk=self.order.pk)
        self.line.status = "completed"
        self.line.save()
        after = Order.objects.get(pk=self.order.pk)
        self.assertEqual(after.status, before.status)
        self.assertEqual(after.updated_at, before.updated_at)
        self.assertEqual(after.status, "pending")

    def test_the_rollup_is_gone(self):
        self.assertFalse(hasattr(Order, "update_status_from_items"))
