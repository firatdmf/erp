# to run this test, use the command:
# python manage.py test notifications.tests

"""A new web order is told to the members of its book only — the book of
the warehouses its lines were picked from (create_web_order splits a cart
by book) — and to superusers, who have every book."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import WebClient
from notifications.models import Notification, NotificationPreference
from operating.models import Order


class NewOrderNotificationBookTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        cls.laleli = Book.objects.create(name="Laleli Fabric")
        cls.ergene = Book.objects.create(name="Ergene")
        cls.web_client = WebClient.objects.create(username="ayse", email="ayse@example.com")

        cls.laleli_staff = User.objects.create_user("laleli_staff", password="pw").member
        cls.laleli_staff.books.set([cls.laleli])
        cls.ergene_staff = User.objects.create_user("ergene_staff", password="pw").member
        cls.ergene_staff.books.set([cls.ergene])
        cls.both = User.objects.create_user("both_books", password="pw").member
        cls.both.books.set([cls.laleli, cls.ergene])
        cls.no_book = User.objects.create_user("no_book", password="pw").member
        cls.boss = User.objects.create_superuser("boss", password="pw").member

    def web_order_in(self, book):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{book.pk}", name="Ayşe", type="customer",
            default_currency=self.usd)
        return Order.objects.create(web_client=self.web_client, current_account=account,
                                    order_status="pending")

    def told(self, order):
        return set(Notification.objects.filter(notification_type="new_order", object_id=order.pk)
                   .values_list("recipient", flat=True))

    def test_only_the_orders_book_is_told(self):
        order = self.web_order_in(self.laleli)
        self.assertEqual(self.told(order), {self.laleli_staff.pk, self.both.pk, self.boss.pk})

    def test_each_book_hears_of_its_own_order(self):
        order = self.web_order_in(self.ergene)
        self.assertEqual(self.told(order), {self.ergene_staff.pk, self.both.pk, self.boss.pk})

    def test_an_order_with_no_book_is_told_to_superusers_only(self):
        order = Order.objects.create(web_client=self.web_client, order_status="pending")
        self.assertEqual(self.told(order), {self.boss.pk})

    def test_a_member_who_turned_order_notifications_off_is_not_told(self):
        NotificationPreference.objects.create(member=self.laleli_staff,
                                              receive_order_notifications=False)
        order = self.web_order_in(self.laleli)
        self.assertEqual(self.told(order), {self.both.pk, self.boss.pk})
