# to run this test, use the command:
# python manage.py test operating.tests.test_pre_order_label

"""An order sold ahead of its goods is a pre-order.

When a client asks for something the shelves don't have, the purchase is
written with the customer on it and the customer's order is created beside
it (accounting.Invoice.for_order). Until that purchase is confirmed there
is no stock and no roll to pack — the order is sold ahead of the goods. It
used to read "Pending", the same word an ordinary untouched order gets, so
the floor could not tell the two apart. Confirming the purchase ends the
pre-order by itself: the rolls arrive and the label goes back to Pending.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderItem


class PreOrderLabelTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer_account = CurrentAccount.objects.create(
            book=self.book, code="C-OLG", name="Oleg", type="customer",
            default_currency=self.usd,
        )
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.customer = Contact.objects.create(name="Oleg Motuzenko")
        self.product = Product.objects.create(title="Krep", sku="KRP", featured=False)

    def _order(self, status="pending"):
        order = Order.objects.create(contact=self.customer,
                                     current_account=self.customer_account,
                                     order_status=status)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("55"), price=Decimal("5"))
        return order

    def _purchase(self, order, status="draft"):
        return Invoice.objects.create(
            book=self.book, current_account=self.supplier, type="purchase",
            status=status, number="P-1", currency=self.usd,
            date=date(2026, 9, 17), due_date=date(2026, 9, 17), for_order=order,
        )

    # ── What the badge says ─────────────────────────────────────────
    def test_an_order_waiting_on_a_draft_purchase_is_a_pre_order(self):
        order = self._order()
        self._purchase(order)
        self.assertTrue(order.is_pre_order)
        self.assertEqual(str(order.status_label), "Pre-order")

    def test_an_ordinary_order_is_still_pending(self):
        order = self._order()
        self.assertFalse(order.is_pre_order)
        self.assertEqual(str(order.status_label), "Pending")

    def test_confirming_the_purchase_ends_the_pre_order(self):
        order = self._order()
        invoice = self._purchase(order)
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        self.assertFalse(Order.objects.get(pk=order.pk).is_pre_order)
        self.assertEqual(str(Order.objects.get(pk=order.pk).status_label), "Pending")

    def test_a_packed_order_keeps_its_own_status(self):
        order = self._order(status="packaging")
        self._purchase(order)
        self.assertFalse(order.is_pre_order)
        self.assertEqual(str(order.status_label), "Packaging")

    # ── What the screens render ─────────────────────────────────────
    def _login(self):
        user = get_user_model().objects.create_user("firat_pre", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def test_the_list_gives_a_pre_order_its_own_badge(self):
        self._login()
        order = self._order()
        self._purchase(order)
        r = self.client.get(reverse("operating:order_list_scoped",
                                    kwargs={"book_id": self.book.pk}))
        self.assertContains(r, "Pre-order")
        self.assertContains(r, 'class="ord-status pre_order"')

    def test_the_detail_page_gives_a_pre_order_its_own_badge(self):
        self._login()
        order = self._order()
        self._purchase(order)
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertContains(r, "Pre-order")
        self.assertContains(r, 'class="ord-status pre_order"')

    # ── One query for a whole list ──────────────────────────────────
    def test_a_list_labels_its_pre_orders_without_a_query_per_row(self):
        pre = self._purchase(self._order()).for_order
        plain = self._order()
        rows = list(Order.with_pre_order_flag(Order.objects.order_by("pk")))
        with self.assertNumQueries(0):
            labels = {r.pk: r.is_pre_order for r in rows}
        self.assertTrue(labels[pre.pk])
        self.assertFalse(labels[plain.pk])
