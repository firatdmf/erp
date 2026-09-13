# to run this test, use the command:
# python manage.py test accounting.test_account_currency_rules

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CurrencyCategory, CurrentAccount, CurrentAccountMovement, Invoice,
)


class CurrencyRulesBase(TestCase):
    """A dollar account in a dollar book, and lira to get wrong with."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ccy_rules", password="pw")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.user.member.books.add(self.book)
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-001", name="RANA", type="customer",
            default_currency=self.usd)

    def movement(self, currency=None, movement_type="adjustment", **kw):
        return CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-11",
            amount=kw.pop("amount", Decimal("100.00")), currency=currency or self.usd,
            movement_type=movement_type,
            exchange_rate=Decimal("0.02062000"), amount_base=Decimal("2.06"), **kw)

    def invoice(self, currency=None, **kw):
        return Invoice.objects.create(
            current_account=self.account, book=self.book, number=kw.pop("number", "INV-1"),
            type="sales", status="draft", date="2026-09-11", due_date="2026-10-11",
            currency=currency or self.usd, **kw)


class CurrencyLockTest(CurrencyRulesBase):

    def test_an_empty_account_can_change_its_currency(self):
        self.account.default_currency = self.try_
        self.account.save()
        self.account.refresh_from_db()
        self.assertEqual(self.account.default_currency, self.try_)
        self.assertFalse(self.account.currency_is_locked)

    def test_a_movement_locks_it(self):
        self.movement()
        self.account.default_currency = self.try_
        with self.assertRaises(ValidationError):
            self.account.save()

    def test_a_draft_invoice_locks_it_too(self):
        """A draft posts no movement, but it is already in the account's currency."""
        self.invoice()
        self.assertTrue(self.account.currency_is_locked)
        self.account.default_currency = self.try_
        with self.assertRaises(ValidationError):
            self.account.save()

    def test_a_locked_account_still_saves_its_other_fields(self):
        self.movement()
        self.account.name = "RANA UYGUR"
        self.account.save()
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "RANA UYGUR")

    def test_the_edit_form_shows_no_picker_once_locked(self):
        url = reverse("accounts:edit", kwargs={"pk": self.account.pk})
        self.assertContains(self.client.get(url), 'name="default_currency"')
        self.movement()
        response = self.client.get(url)
        self.assertNotContains(response, 'name="default_currency"')
        self.assertContains(response, "can't be changed once it has movements or invoices")

    def test_a_stale_form_changing_it_saves_nothing(self):
        """Not the other edits with the currency quietly dropped."""
        self.movement()
        self.client.post(reverse("accounts:edit", kwargs={"pk": self.account.pk}), {
            "name": "RENAMED", "type": "customer", "default_currency": self.try_.pk,
        })
        self.account.refresh_from_db()
        self.assertEqual(self.account.default_currency, self.usd)
        self.assertEqual(self.account.name, "RANA")


class InvoiceCurrencyTest(CurrencyRulesBase):

    def test_an_invoice_in_another_currency_is_refused(self):
        with self.assertRaises(ValidationError):
            self.invoice(currency=self.try_)

    def test_the_form_ignores_a_posted_currency(self):
        self.client.post(reverse("accounts:invoice_create", kwargs={"book_id": self.book.pk}), {
            "account": self.account.pk, "type": "sales", "series": "INV",
            "date": "2026-09-11", "currency": self.try_.pk,
            "items_json": json.dumps([{"description": "Curtain", "quantity": "1", "unit_price": "10"}]),
        })
        self.assertEqual(Invoice.objects.get().currency, self.usd)

    def test_an_old_invoice_that_broke_the_rule_still_saves_as_it_is(self):
        inv = self.invoice()
        Invoice.objects.filter(pk=inv.pk).update(currency=self.try_)   # as if from before the rule
        inv.refresh_from_db()
        inv.notes = "a typo fixed"
        inv.save()
        inv.refresh_from_db()
        self.assertEqual(inv.notes, "a typo fixed")

    def test_moving_an_invoice_onto_another_currency_is_refused(self):
        inv = self.invoice()
        inv.currency = self.try_
        with self.assertRaises(ValidationError):
            inv.save()


class MovementCurrencyTest(CurrencyRulesBase):

    def test_a_manual_adjustment_in_another_currency_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            self.movement(currency=self.try_)
        self.assertIn("account's currency (USD)", " ".join(caught.exception.messages))

    def test_every_debt_changing_type_is_held_to_it(self):
        for kind in ("opening", "interest", "discount", "order_sale", "invoice_purchase"):
            with self.assertRaises(ValidationError, msg=kind):
                self.movement(currency=self.try_, movement_type=kind)

    def test_settling_types_may_be_in_another_currency(self):
        for kind in ("collection", "payment", "advance_in", "advance_out"):
            self.movement(currency=self.try_, movement_type=kind)
        self.assertEqual(self.account.movements.count(), 4)

    def test_a_row_a_document_posted_follows_its_document(self):
        """A transfer posts both legs in one currency on purpose."""
        self.movement(currency=self.try_, source_type=ContentType.objects.get_for_model(Invoice),
                      source_id=1)
        self.assertEqual(self.account.movements.count(), 1)

    def test_an_old_row_that_broke_the_rule_still_saves_as_it_is(self):
        """Fourteen lira adjustments on dollar accounts predate the rule."""
        mv = self.movement()
        CurrentAccountMovement.objects.filter(pk=mv.pk).update(currency=self.try_)
        mv.refresh_from_db()
        mv.description = "a typo fixed"
        mv.save()
        mv.refresh_from_db()
        self.assertEqual(mv.description, "a typo fixed")
        self.assertEqual(mv.currency, self.try_)

    def test_turning_a_settling_row_into_a_debt_one_brings_it_under_the_rule(self):
        mv = self.movement(currency=self.try_, movement_type="advance_in")
        mv.movement_type = "adjustment"
        with self.assertRaises(ValidationError):
            mv.save()

    def test_the_form_says_so_and_saves_nothing(self):
        response = self.client.post(
            reverse("accounts:movement_create", kwargs={"pk": self.account.pk}), {
                "date": "2026-09-11", "movement_type": "adjustment",
                "currency": self.try_.pk, "direction": "debit", "amount": "100.00",
            }, follow=True)
        self.assertEqual(self.account.movements.count(), 0)
        self.assertContains(response, "must be in the account&#x27;s currency (USD)")

    def test_the_form_tells_the_script_what_to_fix_the_currency_to(self):
        response = self.client.get(reverse("accounts:movement_create", kwargs={"pk": self.account.pk}))
        self.assertEqual(response.context["debt_currency_id"], self.usd.pk)
        self.assertIn("adjustment", json.loads(response.context["debt_types_json"]))
        self.assertNotIn("collection", json.loads(response.context["debt_types_json"]))

    def test_an_old_rows_form_keeps_its_own_currency(self):
        """So opening it to fix a typo does not turn its lira into dollars."""
        mv = self.movement()
        CurrentAccountMovement.objects.filter(pk=mv.pk).update(currency=self.try_)
        response = self.client.get(reverse(
            "accounts:movement_edit", kwargs={"pk": self.account.pk, "mv_pk": mv.pk}))
        self.assertEqual(response.context["debt_currency_id"], self.try_.pk)
