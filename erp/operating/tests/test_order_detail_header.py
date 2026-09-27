"""The order page's header line — the icon beside the customer's name.

Run:
    python manage.py test operating.tests.test_order_detail_header
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact
from marketing.models import Product

from operating.models import Order, OrderItem

User = get_user_model()


class TheCustomerIconFollowsTheCustomer(TestCase):
    """People for a contact, a building for a company — the same
    distinction the side menu draws between Contacts and Companies.

    It was `fa-user` on every order, so an order for a company was
    headed by the icon for an individual.
    """

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        # The page is book_guarded: the order's money has to land in a
        # book this viewer is assigned to, or it is a 404.
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-1", name="Oleg", type="customer",
            default_currency=usd)
        self.product = Product.objects.create(title="Crepe", sku="KZL000315", price=10)
        boss = User.objects.create_superuser("boss", "b@t.com", "pw")
        boss.member.books.add(self.book)
        self.client.force_login(boss)

    def _page(self, **who):
        order = Order.objects.create(order_number="DK-284",
                                     current_account=self.account, **who)
        OrderItem.objects.create(order=order, product=self.product,
                                 quantity=Decimal("156.00"), price=Decimal("2.50"))
        resp = self.client.get(reverse("operating:order_detail", kwargs={"pk": order.pk}))
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_a_company_is_headed_by_a_building(self):
        resp = self._page(company=Company.objects.create(name="HAZAL HOME"))
        self.assertContains(resp, '<i class="fa fa-building"></i>', html=False)
        self.assertNotContains(resp, '<i class="fa fa-users"></i>', html=False)

    def test_a_contact_is_headed_by_people(self):
        resp = self._page(contact=Contact.objects.create(name="OLEG"))
        self.assertContains(resp, '<i class="fa fa-users"></i>', html=False)
        self.assertNotContains(resp, '<i class="fa fa-building"></i>', html=False)

    def test_the_template_comment_is_not_printed_onto_the_page(self):
        """A {# … #} comment only works on ONE line; spread over several
        Django renders it verbatim, which is how this landed on the
        page as text between the date and the customer."""
        resp = self._page(contact=Contact.objects.create(name="OLEG"))
        self.assertNotContains(resp, "WHICH KIND")
        self.assertNotContains(resp, "{#")
