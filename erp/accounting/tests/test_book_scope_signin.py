"""A visitor who is not signed in is sent to sign in, not shown a 404.

The book guards answer 404 to a MEMBER who is not assigned the book, so
that which books exist cannot be probed by status code. But the views
they wrap are mostly plain ListView/DetailView with no login mixin, so
an anonymous visitor got the same 404 — a broken page where the sign-in
form should be. Signed-out is not the same as unassigned.
"""
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import Order


class AnonymousIsSentToSignIn(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=self.book, code="C-1", name="Karven", type="customer",
            default_currency=usd)
        self.order = Order.objects.create(
            order_number="DK-1", current_account=account)

    def _assert_sent_to_signin(self, url):
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302, url)
        self.assertEqual(resp["Location"], f"/authentication/signin?next={url}")

    def test_a_book_scoped_collection(self):
        self._assert_sent_to_signin(reverse(
            "operating:order_list_scoped", kwargs={"book_id": self.book.pk}))

    def test_a_book_guarded_object(self):
        self._assert_sent_to_signin(reverse(
            "operating:order_detail", kwargs={"pk": self.order.pk}))
