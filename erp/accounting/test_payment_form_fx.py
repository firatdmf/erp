# to run this test, use the command:
# python manage.py test accounting.test_payment_form_fx

import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
)
from accounting.models_accounts import CariAccount, Payment


class PaymentFormFxTests(TestCase):
    """Entering a rate on the payment form, and what reaches the ledger."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="fx_tester", password="pw"
        )
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.try_ = CurrencyCategory.objects.create(
            code="TRY", name="Turkish Lira", symbol="₺"
        )
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.lira = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.try_, balance=Decimal("0.00")
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Rana", type="customer",
            default_currency=self.try_,
        )

    # -- the rate endpoint -------------------------------------------------
    def test_the_lookup_returns_the_rate_for_the_date_asked_for(self):
        url = reverse("accounts:fx_rate_lookup")
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")
            response = self.client.get(
                url, {"from": "TRY", "to": "USD", "date": "2026-08-17"}
            )

        self.assertEqual(rate.call_args.kwargs["on_date"], date(2026, 8, 17))
        body = response.json()
        self.assertEqual(body["rate"], "0.025")
        self.assertEqual(body["date"], "2026-08-17")

    def test_the_lookup_answers_rather_than_erroring_when_no_source_has_it(self):
        """A blank box to fill in beats an error that interrupts the user."""
        url = reverse("accounts:fx_rate_lookup")
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.side_effect = RuntimeError("no FX source")
            response = self.client.get(url, {"from": "TRY", "to": "USD"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["rate"])

    def test_the_lookup_reports_nothing_to_convert_for_one_currency(self):
        response = self.client.get(
            reverse("accounts:fx_rate_lookup"), {"from": "USD", "to": "USD"}
        )
        self.assertIsNone(response.json()["rate"])

    def test_the_lookup_needs_a_login(self):
        self.client.logout()
        response = self.client.get(
            reverse("accounts:fx_rate_lookup"), {"from": "TRY", "to": "USD"}
        )
        self.assertEqual(response.status_code, 302)

    # -- the form ----------------------------------------------------------
    def test_the_form_tells_the_script_the_books_currency(self):
        response = self.client.get(
            reverse("accounts:payment_create"), {"account": self.cari.pk}
        )
        self.assertContains(response, 'id="fxRow"')
        self.assertContains(response, f'"code": "USD"')

    def test_the_form_says_null_before_an_account_is_picked(self):
        """No account means no book, so nothing is known to convert to."""
        response = self.client.get(reverse("accounts:payment_create"))
        self.assertContains(response, "var BASE = null;")

    # -- what gets saved ---------------------------------------------------
    def _create(self, **overrides):
        data = {
            "account": self.cari.pk,
            "type": "collection",
            "method": "cash",
            "date": "2026-08-17",
            "amount": "200.00",
            "currency": self.try_.pk,
            "cash_account": self.lira.pk,
            "description": "",
            "notes": "",
            "allocations_json": "[]",
            "auto_confirm": "1",
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:payment_create"), data)

    def test_a_typed_rate_is_stored_and_used(self):
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")  # the API's number
            self._create(exchange_rate="0.030000")  # the teller's

        payment = Payment.objects.get()
        self.assertEqual(payment.exchange_rate, Decimal("0.030000"))

        entry = CashTransactionEntry.objects.get(
            content_type=ContentType.objects.get_for_model(Payment),
            content_pk=payment.pk,
        )
        self.assertEqual(entry.exchange_rate, Decimal("0.030000"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("6.00"))

    def test_an_empty_rate_box_leaves_the_published_rate_to_apply(self):
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")
            self._create(exchange_rate="")

        payment = Payment.objects.get()
        self.assertIsNone(payment.exchange_rate)
        entry = CashTransactionEntry.objects.get(
            content_type=ContentType.objects.get_for_model(Payment),
            content_pk=payment.pk,
        )
        self.assertEqual(entry.amount_in_base_currency, Decimal("5.00"))

    def test_a_zero_or_junk_rate_is_treated_as_not_stated(self):
        """Zero would convert the payment to nothing; it cannot be a rate."""
        for bad in ("0", "0.000000", "abc", "-1"):
            Payment.objects.all().delete()
            with mock.patch("accounting.services.get_exchange_rate") as rate:
                rate.return_value = Decimal("0.025")
                self._create(exchange_rate=bad)
            self.assertIsNone(
                Payment.objects.get().exchange_rate, f"{bad!r} should not be a rate"
            )

    def test_editing_the_rate_reconverts_the_ledger_row(self):
        with mock.patch("accounting.services.get_exchange_rate") as rate:
            rate.return_value = Decimal("0.025")
            self._create(exchange_rate="0.030000")
        payment = Payment.objects.get()

        self.client.post(
            reverse("accounts:payment_edit", kwargs={"pk": payment.pk}),
            {
                "type": "collection", "method": "cash", "date": "2026-08-17",
                "amount": "200.00", "currency": self.try_.pk,
                "cash_account": self.lira.pk, "description": "", "notes": "",
                "allocations_json": "[]", "exchange_rate": "0.050000",
            },
        )

        entry = CashTransactionEntry.objects.get(
            content_type=ContentType.objects.get_for_model(Payment),
            content_pk=payment.pk,
        )
        self.assertEqual(entry.exchange_rate, Decimal("0.050000"))
        self.assertEqual(entry.amount_in_base_currency, Decimal("10.00"))
