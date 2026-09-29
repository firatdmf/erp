"""A quote carries two notes: the one printed for the customer, and one
for the team that the print leaves out. Accepting the quote hands both
to the order.

Run with:
    python manage.py test marketing.tests.test_quote_internal_notes
"""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from crm.models import Contact
from marketing.models import Product, ProductVariant, Quote

PRINTED = "Prices per metre in USD."
INTERNAL = "Everything at cost: $9,973.76"


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class QuoteInternalNotesTest(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Hanefi")
        product = Product.objects.create(title="Velvet 320", sku="V320", price=10)
        ProductVariant.objects.create(product=product, variant_sku="V320.ECRU")
        admin = get_user_model().objects.create_superuser(
            username="firat_qn", password="pw", email="a@b.c")
        self.client.force_login(admin)

    def _quote(self):
        body = {
            "book_id": self.book.pk,
            "customer": {"type": "contact", "pk": self.customer.pk},
            "currency": "", "date": "2026-09-29", "valid_until": "",
            "notes": PRINTED, "internal_notes": INTERNAL,
            "items": [{"sku": "V320.ECRU", "quantity": "50", "unit": "mt", "price": "2.30"}],
        }
        r = self.client.post(reverse("marketing:quote_create"), data=json.dumps(body),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return Quote.objects.get(pk=r.json()["quote_id"])

    def test_the_form_saves_and_reopens_with_them(self):
        quote = self._quote()
        self.assertEqual(quote.notes, PRINTED)
        self.assertEqual(quote.internal_notes, INTERNAL)
        form = self.client.get(reverse("marketing:quote_edit", args=[quote.pk]))
        self.assertContains(form, f">{INTERNAL}</textarea>")

    def test_the_page_shows_them_and_the_print_does_not(self):
        quote = self._quote()
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        self.assertContains(page, INTERNAL)
        printout = self.client.get(reverse("marketing:quote_print", args=[quote.pk]) + "?html=1")
        self.assertContains(printout, PRINTED)
        self.assertNotContains(printout, INTERNAL)

    def test_accepting_hands_them_to_the_order(self):
        quote = self._quote()
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        quote.refresh_from_db()
        self.assertEqual(quote.order.notes, PRINTED)
        self.assertEqual(quote.order.internal_notes, INTERNAL)
