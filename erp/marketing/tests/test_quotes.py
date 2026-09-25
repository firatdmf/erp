# to run this test, use the command:
# python manage.py test marketing.tests.test_quotes

"""Quotes — a price given before there is an order.

A quote is written for a CRM customer or just a name, printed or marked
sent, and either declined or turned into an order in one step. The
order it makes is an ordinary one: same account, same currency, same
ledger posting as the create form.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from crm.models import Contact
from marketing.models import Product, ProductVariant
from marketing.models import Quote
from operating.models import Order, OrderChange


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class QuoteTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Nick Greece")
        self.product = Product.objects.create(title="Velvet 320", sku="V320", price=10)
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="V320.ECRU")
        self.admin = get_user_model().objects.create_superuser(
            username="firat_q", password="pw", email="a@b.c")
        self.client.force_login(self.admin)

    def _body(self, **over):
        body = {
            "book_id": self.book.pk,
            "customer": {"type": "contact", "pk": self.customer.pk},
            "currency": "",
            "date": "2026-09-24",
            "valid_until": "2026-10-08",
            "notes": "Delivery in 3 weeks.",
            "items": [
                {"sku": "V320.ECRU", "quantity": "50", "unit": "mt", "price": "2.30"},
                {"sku": "", "description": "Cutting service", "quantity": "1", "unit": "", "price": "15"},
            ],
        }
        body.update(over)
        return body

    def _save(self, body=None, pk=None):
        url = reverse("marketing:quote_edit", args=[pk]) if pk else reverse("marketing:quote_create")
        return self.client.post(url, data=json.dumps(body if body is not None else self._body()),
                                content_type="application/json")

    def test_a_quote_is_saved_and_numbered(self):
        r = self._save()
        self.assertEqual(r.status_code, 200, r.content)
        quote = Quote.objects.get(pk=r.json()["quote_id"])
        self.assertTrue(quote.number.startswith("QUO-"), quote.number)
        self.assertEqual(quote.contact, self.customer)
        self.assertEqual(quote.book, self.book)
        self.assertEqual(quote.currency, self.usd)             # no account yet → the base currency
        self.assertEqual(quote.total(), Decimal("130.00"))     # 50 × 2.30 + 15
        first, second = quote.items.all()
        self.assertEqual(first.product_variant, self.variant)
        self.assertEqual(first.product, self.product)
        self.assertEqual(second.description, "Cutting service")
        self.assertIsNone(second.product)
        # Orders keep their own series.
        Order.objects.create(order_number="", contact=self.customer)
        self.assertTrue(Order.objects.get().order_number.startswith("ORD-"))

    def test_a_quote_prices_in_the_customers_account_currency(self):
        CurrentAccount.objects.create(book=self.book, contact=self.customer, code="C-1",
                                      name="Nick", type="customer", default_currency=self.eur)
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        self.assertEqual(quote.currency, self.eur)
        # Unless the form says otherwise.
        quote = Quote.objects.get(pk=self._save(self._body(currency="USD")).json()["quote_id"])
        self.assertEqual(quote.currency, self.usd)

    def test_a_line_needs_a_product_or_a_description(self):
        r = self._save(self._body(items=[{"sku": "", "description": "", "quantity": "1", "price": "1"}]))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Quote.objects.exists())
        r = self._save(self._body(items=[{"sku": "NOPE", "quantity": "1", "price": "1"}]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("NOPE", r.json()["error"])

    def test_a_quote_needs_someone_to_be_for(self):
        r = self._save(self._body(customer=None, customer_name=""))
        self.assertEqual(r.status_code, 400)
        r = self._save(self._body(customer=None, customer_name="Walk-in Ali", customer_phone="555"))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Quote.objects.get().get_client(), "Walk-in Ali")

    def test_the_pages_render(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        for name in ("quote_detail", "quote_print", "quote_edit"):
            page = self.client.get(reverse("marketing:%s" % name, args=[quote.pk]))
            self.assertContains(page, quote.number, msg_prefix=name)
        page = self.client.get(reverse("marketing:quote_list"))
        self.assertContains(page, quote.number)
        self.assertContains(page, "Nick Greece")

    def test_editing_replaces_the_lines(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        r = self._save(self._body(items=[{"sku": "V320.ECRU", "quantity": "20", "price": "2.50"}]), pk=quote.pk)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(quote.items.count(), 1)
        self.assertEqual(quote.total(), Decimal("50.00"))
        self.assertEqual(Quote.objects.count(), 1)

    def test_accepting_makes_the_order(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            currency="EUR", items=[{"sku": "V320.ECRU", "quantity": "50", "unit": "mt", "price": "2.30"}],
        )).json()["quote_id"])
        r = self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        order = Order.objects.get()
        self.assertRedirects(r, reverse("operating:order_detail", args=[order.pk]),
                             fetch_redirect_response=False)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "accepted")
        self.assertEqual(quote.order, order)
        self.assertEqual(order.contact, self.customer)
        self.assertEqual(order.notes, "Delivery in 3 weeks.")
        self.assertEqual(order.currency, self.eur)              # as quoted, not the account's default
        self.assertEqual(order.current_account.book, self.book)
        [line] = order.items.all()
        self.assertEqual((line.product, line.product_variant, line.quantity, line.price),
                         (self.product, self.variant, Decimal("50.00"), Decimal("2.30")))
        sale = CurrentAccountMovement.objects.get(movement_type="order_sale", source_id=order.pk)
        self.assertEqual((sale.amount, sale.currency), (Decimal("115.00"), self.eur))
        self.assertTrue(OrderChange.objects.filter(order=order, field="quote",
                                                   new_value__contains=quote.number).exists())
        # Closed: no more edits, no second order.
        self.assertEqual(self._save(pk=quote.pk).status_code, 400)
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        self.assertEqual(Order.objects.count(), 1)

    def test_a_free_text_line_blocks_conversion(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])     # has "Cutting service"
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        self.assertContains(page, "Cutting service")
        self.assertContains(page, "name no catalog product")
        r = self.client.post(reverse("marketing:quote_convert", args=[quote.pk]), follow=True)
        self.assertFalse(Order.objects.exists())
        self.assertContains(r, "name no catalog product")

    def test_a_name_only_quote_cannot_convert(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            customer=None, customer_name="Walk-in Ali",
            items=[{"sku": "V320.ECRU", "quantity": "5", "price": "2"}])).json()["quote_id"])
        self.assertIn("Pick a CRM customer", " ".join(str(w) for w in quote.conversion_blockers()))
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        self.assertFalse(Order.objects.exists())

    def test_status_marks(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        url = reverse("marketing:quote_status", args=[quote.pk])
        for status in ("sent", "declined", "draft"):
            self.client.post(url, {"status": status})
            quote.refresh_from_db()
            self.assertEqual(quote.status, status)
        self.client.post(url, {"status": "accepted"})
        quote.refresh_from_db()
        self.assertEqual(quote.status, "draft")                # accepting is the convert step

    def test_an_old_quote_reads_as_expired(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            valid_until=(date.today() - timedelta(days=1)).isoformat())).json()["quote_id"])
        self.assertTrue(quote.is_expired)
        self.assertEqual(quote.status_key, "expired")
        page = self.client.get(reverse("marketing:quote_list") + "?status=expired")
        self.assertContains(page, quote.number)
        page = self.client.get(reverse("marketing:quote_list") + "?status=accepted")
        self.assertNotContains(page, quote.number)

    def test_the_product_search_finds_variants(self):
        r = self.client.get(reverse("marketing:quote_product_search") + "?q=velvet")
        [row] = r.json()["results"]
        self.assertEqual((row["sku"], row["variant"]), ("V320.ECRU", True))
        self.assertIn("Velvet 320", row["label"])
