"""The delivery address is typed as one block, line by line, and every
page that prints it keeps the lines."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import Order


class TheAddressKeepsItsLines(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-77", name="Oleg Textiles", type="customer", default_currency=usd)
        self.order = Order.objects.create(
            order_number="DK-77", current_account=account,
            delivery_address="Fatih Cad. 12\nIstanbul, Turkey\n+90 555 000 00 00")
        user = get_user_model().objects.create_user("staff_addr", password="pw")
        user.member.books.add(book)
        user.member.default_book = book
        user.member.save()
        self.client.force_login(user)

    def test_the_detail_page(self):
        resp = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertContains(resp, "Fatih Cad. 12<br>Istanbul, Turkey<br>+90 555 000 00 00")

    def test_the_printout(self):
        resp = self.client.get(reverse("operating:order_print", args=[self.order.pk]))
        self.assertContains(resp, "Fatih Cad. 12<br>Istanbul, Turkey<br>+90 555 000 00 00")
