# to run this test, use the command:
# python manage.py test accounting.test_intake_currency

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from accounting.services_accounts import (
    MixedCurrencyError, convert_lines_to_currency, invoice_currency_for,
)


def _line(price, currency, desc="GREK Beyaz"):
    return {"description": desc, "quantity": Decimal("10"), "unit": "mt",
            "unit_price": Decimal(price), "currency": currency}


class InvoiceCurrencyTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Demfirat")

    def _cari(self, currency, code="CARI-001"):
        return CariAccount.objects.create(
            book=self.book, code=code, name="Kızılırmak",
            type="supplier", default_currency=currency,
        )

    def test_the_alim_is_denominated_in_what_we_owe_them(self):
        self.assertEqual(invoice_currency_for(self._cari(self.try_)), "TRY")
        self.assertEqual(invoice_currency_for(self._cari(self.usd, "CARI-002")), "USD")

    def test_an_account_with_no_currency_falls_back_to_base(self):
        """Defensive only — the column is NOT NULL, so this cannot come out
        of the database. It guards the unsaved instance and the None."""
        self.assertEqual(invoice_currency_for(CariAccount()), "USD")
        self.assertEqual(invoice_currency_for(None), "USD")


class ConvertLinesTest(TestCase):
    """The bug this replaces: a delivery priced part in dollars and part in
    lira was billed as though ₺100 were $100 — no conversion, no warning."""

    def test_a_line_already_in_the_target_is_untouched(self):
        out = convert_lines_to_currency([_line("4.00", "USD")], "USD", {})
        self.assertEqual(out[0]["unit_price"], Decimal("4.00"))
        self.assertEqual(out[0]["currency"], "USD")
        self.assertNotIn("@", out[0]["description"])

    def test_a_foreign_line_is_converted_at_the_rate_given(self):
        out = convert_lines_to_currency(
            [_line("100.00", "TRY")], "USD", {"TRY": "0.02077833"})
        self.assertEqual(out[0]["unit_price"], Decimal("2.077833"))
        self.assertEqual(out[0]["currency"], "USD")

    def test_the_unit_price_is_not_rounded_to_cents(self):
        """A cent rounded off a UNIT price comes back multiplied by metres.
        TRY 100.00/m at 0.02077833 held as $2.08 bills $913.95 for a 439.40 m
        line whose true cost is $913.00."""
        from accounting.models_accounts import InvoiceItem
        line = convert_lines_to_currency(
            [_line("100.00", "TRY")], "USD", {"TRY": "0.02077833"})[0]
        item = InvoiceItem(quantity=Decimal("439.40"),
                           unit_price=line["unit_price"],
                           discount_rate=Decimal("0"), tax_rate=Decimal("0"))
        item.compute()
        self.assertEqual(item.subtotal, Decimal("913.00"))

    def test_the_column_can_actually_hold_it(self):
        """Six decimals in memory is worth nothing if the column rounds them
        back on the way in — the whole bug was rounding AT REST."""
        from accounting.models_accounts import InvoiceItem
        self.assertEqual(InvoiceItem._meta.get_field("unit_price").decimal_places, 6)

    def test_the_original_price_stays_readable_on_the_line(self):
        """The converted figure has to be checkable against what was agreed."""
        out = convert_lines_to_currency(
            [_line("100.00", "TRY")], "USD", {"TRY": "0.02077833"})
        self.assertIn("100.00 TRY", out[0]["description"])
        self.assertIn("0.02077833", out[0]["description"])

    def test_a_mixed_batch_comes_out_in_one_currency(self):
        out = convert_lines_to_currency(
            [_line("4.00", "USD"), _line("100.00", "TRY")], "USD", {"TRY": "0.02"})
        self.assertEqual({l["currency"] for l in out}, {"USD"})
        self.assertEqual([l["unit_price"] for l in out],
                         [Decimal("4.00"), Decimal("2.000000")])

    def test_case_does_not_matter(self):
        out = convert_lines_to_currency([_line("100.00", "try")], "usd", {"TrY": "0.02"})
        self.assertEqual(out[0]["unit_price"], Decimal("2.000000"))

    def test_a_zero_price_needs_no_rate(self):
        out = convert_lines_to_currency([_line("0", "TRY")], "USD", {})
        self.assertEqual(out[0]["currency"], "USD")

    @patch("accounting.services.get_exchange_rate", return_value=Decimal("0.03"))
    def test_a_missing_rate_falls_back_to_the_published_one(self, _fx):
        out = convert_lines_to_currency([_line("100.00", "TRY")], "USD", {})
        self.assertEqual(out[0]["unit_price"], Decimal("3.000000"))

    @patch("accounting.services.get_exchange_rate", return_value=None)
    def test_no_rate_anywhere_refuses_rather_than_billing_at_par(self, _fx):
        """The one thing that must not happen: a number carried across a
        currency boundary as if it were already in the right one."""
        with self.assertRaises(MixedCurrencyError) as ctx:
            convert_lines_to_currency([_line("100.00", "TRY")], "USD", {})
        self.assertIn("TRY", str(ctx.exception))
        self.assertIn("USD", str(ctx.exception))

    @patch("accounting.services.get_exchange_rate", return_value=None)
    def test_a_zero_rate_is_refused_too(self, _fx):
        with self.assertRaises(MixedCurrencyError):
            convert_lines_to_currency([_line("100.00", "TRY")], "USD", {"TRY": "0"})
