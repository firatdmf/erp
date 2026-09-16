"""A payment's method decides the other side of its entry, and the screens
that record payments and movements keep the entry honest.

Run with:
    python manage.py test accounting.tests.test_payment_posting
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory, Payment
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.models_ledger import JournalEntry, JournalLine
from accounting.services_ledger import balance_sheet, ensure_chart


class _Base(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.account = CurrentAccount.objects.create(
            book=self.book, code="ACC-001", name="SVETLANA",
            default_currency=self.usd)
        self.box = CashAccount.objects.create(
            book=self.book, name="Kasa", currency=self.usd,
            balance=Decimal("5000.00"))
        user = get_user_model().objects.create_user("acct", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.user = user
        self.client.force_login(user)

    def _payment(self, method, *, type_="collection", box=None, amount="655.00"):
        payment = Payment.objects.create(
            current_account=self.account, book=self.book,
            number=f"P-{Payment.objects.count() + 1}", type=type_,
            method=method, status="draft", date="2026-09-15",
            amount=Decimal(amount), currency=self.usd, cash_account=box)
        payment.confirm()
        return payment

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}


class TheMethodDecidesTheOtherSide(_Base):
    def test_cash_lands_in_the_cash_box_it_went_through(self):
        self._payment("cash", box=self.box)
        self.assertEqual(self._balances()["1000"], Decimal("655.00"))
        line = JournalLine.objects.get(account__code="1000")
        self.assertEqual(line.cash_account, self.box)

    def test_a_cheque_received_is_not_cash_yet(self):
        self._payment("check")
        b = self._balances()
        self.assertEqual(b["1400"], Decimal("655.00"))
        self.assertNotIn("1000", b)

    def test_a_cheque_given_is_owed_until_it_is_paid(self):
        self._payment("promissory_note", type_="payment")
        b = self._balances()
        self.assertEqual(b["2100"], Decimal("655.00"))
        self.assertNotIn("1000", b)

    def test_an_offset_moves_no_cash(self):
        self._payment("offset")
        b = self._balances()
        self.assertNotIn("1000", b)
        self.assertEqual(b["1900"], Decimal("655.00"))

    def test_every_method_leaves_the_book_balanced(self):
        for method, _label in Payment.METHOD_CHOICES:
            box = self.box if method in Payment.CASH_METHODS else None
            self._payment(method, box=box)
            self._payment(method, type_="payment", box=box, amount="10.00")
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_changing_the_method_moves_the_entry(self):
        """The edit screen re-saves the payment's movement, and the entry
        follows the method now on the payment, not the one it had."""
        payment = self._payment("cash", box=self.box)
        payment.method = "check"
        payment.cash_account = None
        payment.save()
        payment.resync_posted_movement()
        b = self._balances()
        self.assertNotIn("1000", b)
        self.assertEqual(b["1400"], Decimal("655.00"))
        self.assertEqual(JournalEntry.objects.count(), 1)


class ThePaymentScreensRequireACashBox(_Base):
    def _post_create(self, **extra):
        data = {
            "account": self.account.pk, "type": "collection", "method": "cash",
            "date": "2026-09-15", "amount": "655.00", "currency": self.usd.pk,
            "description": "", "notes": "", "allocations_json": "[]",
            "auto_confirm": "1",
        }
        data.update(extra)
        return self.client.post(
            reverse("accounts:payment_create", kwargs={"book_id": self.book.pk}),
            data, follow=True)

    def test_confirming_cash_with_no_box_saves_a_draft_instead(self):
        r = self._post_create()
        payment = Payment.objects.get()
        self.assertEqual(payment.status, "draft")
        self.assertIsNone(payment.posted_movement)
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertContains(r, "Choose the cash box")

    def test_confirming_cash_with_a_box_goes_through(self):
        self._post_create(cash_account=self.box.pk)
        self.assertEqual(Payment.objects.get().status, "confirmed")
        self.assertEqual(self._balances()["1000"], Decimal("655.00"))

    def test_bank_and_card_need_one_too(self):
        for method in ("bank_transfer", "credit_card"):
            self._post_create(method=method)
        self.assertFalse(Payment.objects.filter(status="confirmed").exists())

    def test_a_cheque_needs_no_box(self):
        self._post_create(method="check")
        self.assertEqual(Payment.objects.get().status, "confirmed")

    def test_a_draft_needs_no_box(self):
        data = {"auto_confirm": ""}
        self._post_create(**data)
        self.assertEqual(Payment.objects.get().status, "draft")

    def test_the_confirm_button_refuses_without_a_box(self):
        payment = Payment.objects.create(
            current_account=self.account, book=self.book, number="P-1",
            type="collection", method="cash", status="draft",
            date="2026-09-15", amount=Decimal("655.00"), currency=self.usd)
        r = self.client.post(reverse("accounts:payment_confirm",
                                     kwargs={"pk": payment.pk}), follow=True)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "draft")
        self.assertContains(r, "Choose the cash box")

    def test_a_confirmed_payment_cannot_lose_its_box(self):
        payment = self._payment("cash", box=self.box)
        self.client.post(reverse("accounts:payment_edit", kwargs={"pk": payment.pk}), {
            "type": "collection", "method": "cash", "date": "2026-09-15",
            "amount": "700.00", "currency": self.usd.pk, "cash_account": "",
            "description": "", "notes": "", "allocations_json": "[]",
        })
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("655.00"))
        self.assertEqual(payment.cash_account, self.box)

    def test_the_form_carries_the_preview(self):
        r = self.client.get(
            reverse("accounts:payment_create", kwargs={"book_id": self.book.pk}),
            {"account": self.account.pk, "type": "collection"})
        self.assertContains(r, 'id="pfPaymentPreview"')
        self.assertContains(r, "What this does in the books")


class TheTypeSetsTheDirection(_Base):
    def _create(self, movement_type, direction, account=None):
        account = account or self.account
        return self.client.post(
            reverse("accounts:movement_create", kwargs={"pk": account.pk}), {
                "date": "2026-09-15", "movement_type": movement_type,
                "currency": self.usd.pk, "direction": direction,
                "amount": "100.00", "reference": "", "description": "",
            }, follow=True)

    def test_money_types_are_not_offered_here(self):
        """This form changes what an account owes. Money that moved goes
        through Take / Make Payment, which asks where it went."""
        r = self.client.get(reverse("accounts:movement_create",
                                    kwargs={"pk": self.account.pk}))
        offered = {v for v, _l in r.context["movement_type_choices"]}
        for kind in ("collection", "payment", "advance_in", "advance_out"):
            self.assertNotIn(kind, offered)
        self.assertIn("write_off", offered)

    def test_a_money_type_posted_anyway_is_refused(self):
        r = self._create("collection", "credit")
        self.assertFalse(CurrentAccountMovement.objects.exists())
        self.assertContains(r, "Take Payment or Make Payment")

    def test_a_discount_cannot_be_a_debit(self):
        self._create("discount", "debit")
        self.assertFalse(CurrentAccountMovement.objects.exists())

    def test_trade_types_come_from_documents_not_this_form(self):
        r = self.client.get(reverse("accounts:movement_create",
                                    kwargs={"pk": self.account.pk}))
        offered = {v for v, _l in r.context["movement_type_choices"]}
        for kind in ("order_sale", "invoice_sale", "invoice_purchase",
                     "return_sale", "return_purchase"):
            self.assertNotIn(kind, offered)
        r = self._create("order_sale", "debit")
        self.assertFalse(CurrentAccountMovement.objects.exists())
        self.assertContains(r, "come from orders and invoices")

    def test_a_write_off_is_a_credit(self):
        self._create("write_off", "credit")
        self.assertEqual(CurrentAccountMovement.objects.get().amount,
                         Decimal("-100.00"))

    def test_an_adjustment_goes_either_way(self):
        self._create("adjustment", "debit")
        self._create("adjustment", "credit")
        self.assertEqual(CurrentAccountMovement.objects.count(), 2)

    def test_an_existing_collection_is_edited_on_the_payment_screen(self):
        """A collection typed here before has a Payment behind it, so its
        Edit link already leads to the payment form — the screen that can
        name the kasa it went through."""
        mv = CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-01",
            amount=Decimal("-80.00"), currency=self.usd,
            movement_type="collection", description="old")
        payment = Payment.objects.get(posted_movement=mv)
        r = self.client.get(reverse("accounts:movement_edit",
                                    kwargs={"pk": self.account.pk, "mv_pk": mv.pk}))
        self.assertRedirects(r, reverse("accounts:payment_edit",
                                        kwargs={"pk": payment.pk}),
                             fetch_redirect_response=False)

    def test_nothing_is_retyped_into_a_money_type(self):
        mv = CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-01",
            amount=Decimal("-80.00"), currency=self.usd,
            movement_type="adjustment", description="old")
        self.client.post(reverse("accounts:movement_edit",
                                 kwargs={"pk": self.account.pk, "mv_pk": mv.pk}), {
            "date": "2026-09-01", "movement_type": "collection",
            "currency": self.usd.pk, "direction": "credit",
            "amount": "80.00", "reference": "", "description": "old",
        })
        mv.refresh_from_db()
        self.assertEqual(mv.movement_type, "adjustment")

    def test_an_old_row_that_went_the_other_way_can_still_be_edited(self):
        """One discount on the live books is a debit. Opening it to fix its
        description must not refuse to save."""
        mv = CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-01",
            amount=Decimal("50.00"), currency=self.usd,
            movement_type="discount", description="old")
        url = reverse("accounts:movement_edit",
                      kwargs={"pk": self.account.pk, "mv_pk": mv.pk})
        self.client.post(url, {
            "date": "2026-09-01", "movement_type": "discount",
            "currency": self.usd.pk, "direction": "debit",
            "amount": "50.00", "reference": "", "description": "fixed",
        })
        mv.refresh_from_db()
        self.assertEqual(mv.description, "fixed")

    def test_retyping_an_old_row_brings_it_under_the_rule(self):
        mv = CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-09-01",
            amount=Decimal("50.00"), currency=self.usd,
            movement_type="adjustment", description="old")
        url = reverse("accounts:movement_edit",
                      kwargs={"pk": self.account.pk, "mv_pk": mv.pk})
        self.client.post(url, {
            "date": "2026-09-01", "movement_type": "write_off",
            "currency": self.usd.pk, "direction": "debit",
            "amount": "50.00", "reference": "", "description": "old",
        })
        mv.refresh_from_db()
        self.assertEqual(mv.movement_type, "adjustment")

    def test_the_form_tells_the_script_which_way_each_type_goes(self):
        r = self.client.get(reverse("accounts:movement_create",
                                    kwargs={"pk": self.account.pk}))
        self.assertContains(r, 'id="mfFixedDirections"')
        self.assertEqual(r.context["fixed_directions"]["write_off"], "credit")
        self.assertEqual(r.context["fixed_directions"]["order_sale"], "debit")
        self.assertNotIn("adjustment", r.context["fixed_directions"])


class OpeningBalanceOnlyOnAnEmptyAccount(_Base):
    def _create(self, movement_type="opening"):
        return self.client.post(
            reverse("accounts:movement_create", kwargs={"pk": self.account.pk}), {
                "date": "2026-09-15", "movement_type": movement_type,
                "currency": self.usd.pk, "direction": "debit",
                "amount": "100.00", "reference": "", "description": "",
            }, follow=True)

    def _offered(self):
        r = self.client.get(reverse("accounts:movement_create",
                                    kwargs={"pk": self.account.pk}))
        return r, {v for v, _l in r.context["movement_type_choices"]}

    def test_an_empty_account_offers_it_and_starts_on_it(self):
        r, offered = self._offered()
        self.assertIn("opening", offered)
        self.assertEqual(r.context["default_movement_type"], "opening")

    def test_an_account_with_history_does_not(self):
        self._create()
        r, offered = self._offered()
        self.assertNotIn("opening", offered)
        self.assertEqual(r.context["default_movement_type"], "adjustment")

    def test_a_second_one_posted_anyway_is_refused(self):
        self._create()
        r = self._create()
        self.assertEqual(CurrentAccountMovement.objects.count(), 1)
        self.assertContains(r, "no movements yet")

    def test_the_opening_row_itself_can_still_be_edited(self):
        self._create()
        mv = CurrentAccountMovement.objects.get()
        self._create("interest")
        url = reverse("accounts:movement_edit",
                      kwargs={"pk": self.account.pk, "mv_pk": mv.pk})
        r = self.client.get(url)
        self.assertIn("opening", {v for v, _l in r.context["movement_type_choices"]})
        self.client.post(url, {
            "date": "2026-09-15", "movement_type": "opening",
            "currency": self.usd.pk, "direction": "debit",
            "amount": "150.00", "reference": "", "description": "fixed",
        })
        mv.refresh_from_db()
        self.assertEqual(mv.amount, Decimal("150.00"))

    def test_another_row_cannot_be_retyped_into_one(self):
        self._create("interest")
        self._create("adjustment")
        mv = CurrentAccountMovement.objects.get(movement_type="adjustment")
        self.client.post(reverse("accounts:movement_edit",
                                 kwargs={"pk": self.account.pk, "mv_pk": mv.pk}), {
            "date": "2026-09-15", "movement_type": "opening",
            "currency": self.usd.pk, "direction": "debit",
            "amount": "100.00", "reference": "", "description": "",
        })
        mv.refresh_from_db()
        self.assertEqual(mv.movement_type, "adjustment")

