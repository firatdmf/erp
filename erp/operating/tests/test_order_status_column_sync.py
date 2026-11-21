from django.db import connection
from django.test import TestCase

from operating.models import Order


class TheTwoStatusColumnsStayAlike(TestCase):
    """While the order_status column is renamed to status, both exist and
    a trigger keeps them equal, whichever one a release writes."""

    def columns(self, order):
        with connection.cursor() as c:
            c.execute("SELECT order_status, status FROM operating_order WHERE id = %s", [order.pk])
            return c.fetchone()

    def test_a_new_order_fills_both(self):
        order = Order.objects.create(status="packaging")
        self.assertEqual(self.columns(order), ("packaging", "packaging"))

    def test_a_change_through_the_model_reaches_both(self):
        order = Order.objects.create()
        Order.objects.filter(pk=order.pk).update(status="shipped")
        self.assertEqual(self.columns(order), ("shipped", "shipped"))

    def test_a_release_writing_the_other_column_reaches_both(self):
        order = Order.objects.create()
        with connection.cursor() as c:
            c.execute("UPDATE operating_order SET order_status = 'cancelled' WHERE id = %s", [order.pk])
        self.assertEqual(self.columns(order), ("cancelled", "cancelled"))
        order.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
