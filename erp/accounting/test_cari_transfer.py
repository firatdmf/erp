# to run this test, use the command:
# python manage.py test accounting.test_cari_transfer

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book,
    CariAccount,
    CariMovement,
    CariTransfer,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
    InTransfer,
)


class TransferTestBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="transfer_tester", password="pw"
        )
        self.client.force_login(self.user)

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")

        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Nejum")

        self.a = CariAccount.objects.create(
            book=self.book, code="01784", name="ELMİRA MAYKOP",
            default_currency=self.usd,
        )
        self.b = CariAccount.objects.create(
            book=self.book, code="01785", name="AHMET",
            default_currency=self.usd,
        )
        self.elsewhere = CariAccount.objects.create(
            book=self.other_book, code="09000", name="OTHER BOOK",
            default_currency=self.usd,
        )

        # A owes us 1000 to start with.
        CariMovement.objects.create(
            cari=self.a, book=self.book, date="2026-01-01",
            amount=Decimal("1000.00"), currency=self.usd, movement_type="opening",
        )

        self.kasa = CashAccount.objects.create(
            book=self.book, name="Ziraat", currency=self.usd, balance=Decimal("5000.00")
        )
        self.banka = CashAccount.objects.create(
            book=self.book, name="Garanti", currency=self.usd, balance=Decimal("0.00")
        )

    def url(self, book=None):
        return reverse("accounting:make_in_transfer", kwargs={"pk": (book or self.book).pk})

    def balances(self):
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        return self.a.cached_balance, self.b.cached_balance


class CariTransferModelTest(TransferTestBase):
    """The debt moves and the money does not — which is the whole
    difference between this and the cash transfer sharing its page."""

    def test_posting_moves_the_debt_and_leaves_the_total_alone(self):
        t = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd,
        )
        t.post()

        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))
        self.assertEqual(
            sum(b for b in self.balances()), Decimal("1000.00"),
            "the book's total receivable must not change",
        )

    def test_posting_touches_no_cash(self):
        t = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd,
        )
        t.post()

        self.kasa.refresh_from_db()
        self.banka.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("5000.00"))
        self.assertEqual(self.banka.balance, Decimal("0.00"))
        self.assertFalse(CashTransactionEntry.objects.exists())

    def test_both_legs_share_one_rate_so_they_cancel_in_base(self):
        """Posted in TRY, the pair must still net to zero in USD.

        Deriving each leg's rate from its own account's currency would
        leave an FX residue on the book that nobody entered.
        """
        t = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.try_,
        )
        t.post()

        self.assertEqual(
            t.from_movement.amount_base + t.to_movement.amount_base,
            Decimal("0.00"),
        )
        self.assertEqual(t.from_movement.exchange_rate, t.to_movement.exchange_rate)

    def test_posting_twice_writes_one_pair(self):
        t = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd,
        )
        t.post()
        t.post()

        self.assertEqual(CariMovement.objects.filter(cari=self.b).count(), 1)
        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))

    def test_unposting_leaves_both_statements_as_if_it_never_happened(self):
        t = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd,
        )
        t.post()
        t.unpost()

        self.assertEqual(self.balances(), (Decimal("1000.00"), Decimal("0.00")))
        self.assertEqual(CariMovement.objects.filter(cari=self.b).count(), 0)

    def test_an_account_cannot_transfer_to_itself(self):
        with self.assertRaises(ValidationError):
            CariTransfer.objects.create(
                book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.a,
                amount=Decimal("400.00"), currency=self.usd,
            )

    def test_a_transfer_cannot_span_two_books(self):
        with self.assertRaises(ValidationError):
            CariTransfer.objects.create(
                book=self.book, date="2026-02-01",
                from_cari=self.a, to_cari=self.elsewhere,
                amount=Decimal("400.00"), currency=self.usd,
            )

    def test_amount_must_be_positive(self):
        """Direction is the from/to pair, never the sign of the amount —
        a negative would silently reverse the transfer."""
        for bad in (Decimal("0.00"), Decimal("-400.00")):
            with self.subTest(amount=bad):
                with self.assertRaises(ValidationError):
                    CariTransfer.objects.create(
                        book=self.book, date="2026-02-01",
                        from_cari=self.a, to_cari=self.b,
                        amount=bad, currency=self.usd,
                    )


class TransferPageModeTest(TransferTestBase):
    """One page, two modes. The page must ask which before it moves
    anything, and each mode must post only its own kind of row."""

    def test_page_offers_both_modes(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Between cash accounts")
        self.assertContains(response, "Between current accounts")

    def test_cash_is_the_default_mode(self):
        response = self.client.get(self.url())
        self.assertEqual(response.context["mode"], "cash")

    def test_unknown_mode_falls_back_to_cash(self):
        response = self.client.get(self.url() + "?mode=nonsense")
        self.assertEqual(response.context["mode"], "cash")

    def test_cari_mode_only_offers_accounts_of_this_book(self):
        response = self.client.get(self.url() + "?mode=cari")
        queryset = response.context["cari_form"].fields["from_cari"].queryset
        self.assertIn(self.a, queryset)
        self.assertNotIn(self.elsewhere, queryset)

    def test_posting_cari_mode_moves_the_balance(self):
        response = self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": self.a.pk,
            "to_cari": self.b.pk,
            "amount": "400.00",
            "currency": self.usd.pk,
            "description": "Devir",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))
        self.assertEqual(CariTransfer.objects.count(), 1)
        self.assertEqual(InTransfer.objects.count(), 0)

    def test_posting_cari_mode_records_who_did_it(self):
        self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": self.a.pk,
            "to_cari": self.b.pk,
            "amount": "400.00",
            "currency": self.usd.pk,
        })
        transfer = CariTransfer.objects.get()
        self.assertIsNotNone(transfer.from_movement)
        self.assertIsNotNone(transfer.to_movement)
        self.assertEqual(transfer.from_movement.reference, f"TRANSFER {transfer.pk}")

    def test_a_rejected_cari_transfer_moves_nothing(self):
        response = self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": self.a.pk,
            "to_cari": self.a.pk,
            "amount": "400.00",
            "currency": self.usd.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["mode"], "cari")
        self.assertTrue(response.context["cari_form"].errors)
        self.assertEqual(self.balances(), (Decimal("1000.00"), Decimal("0.00")))
        self.assertEqual(CariTransfer.objects.count(), 0)

    def test_posting_cash_mode_still_moves_cash(self):
        """The mode the page grew was added beside the one it had, not
        over it."""
        response = self.client.post(self.url(), {
            "mode": "cash",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cash_account": self.kasa.pk,
            "to_cash_account": self.banka.pk,
            "amount": "250.00",
            "currency": self.usd.pk,
        })

        self.assertEqual(response.status_code, 302)
        self.kasa.refresh_from_db()
        self.banka.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("4750.00"))
        self.assertEqual(self.banka.balance, Decimal("250.00"))
        self.assertEqual(CashTransactionEntry.objects.count(), 2)
        self.assertEqual(CariTransfer.objects.count(), 0)

    def test_a_rejected_cash_transfer_moves_nothing(self):
        response = self.client.post(self.url(), {
            "mode": "cash",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cash_account": self.kasa.pk,
            "to_cash_account": "",
            "amount": "250.00",
            "currency": self.usd.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.kasa.refresh_from_db()
        self.assertEqual(self.kasa.balance, Decimal("5000.00"))
        self.assertEqual(CashTransactionEntry.objects.count(), 0)


class TransferOnTheStatementTest(TransferTestBase):
    """A transfer leg is half a pair. The statement must show it as
    someone else's row, not as a line the operator can edit."""

    def setUp(self):
        super().setUp()
        self.transfer = CariTransfer.objects.create(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd, description="Devir",
        )
        self.transfer.post()

    def rows_for(self, cari):
        from accounting.views_accounts import _attach_links
        return _attach_links([
            {"mv": mv, "balance_after": Decimal("0")}
            for mv in CariMovement.objects.filter(cari=cari)
        ])

    def test_a_transfer_leg_is_not_editable_in_place(self):
        row = next(r for r in self.rows_for(self.b))
        self.assertFalse(row["editable"])
        self.assertEqual(str(row["owner_label"]), "Account transfer")

    def test_a_transfer_leg_is_not_mistaken_for_a_cancellation(self):
        """Cancellation counter-rows are adjustments with a source FK
        too — the transfer must not be swept up with them."""
        row = next(r for r in self.rows_for(self.b))
        self.assertFalse(row["is_cancel_row"])
        self.assertIsNone(row["linked_payment"])
        self.assertIsNone(row["linked_invoice"])

    def test_the_leg_names_the_account_on_the_other_side(self):
        row = next(r for r in self.rows_for(self.b))
        self.assertIn(self.a.code, row["description"])
        self.assertIn("Devir", row["description"])

    def test_a_transfer_writes_no_payment_row(self):
        """Adjustment, not collection — a virman is not money received,
        and mirroring one into Payment would put it in Tahsilatlar."""
        from accounting.models import Payment
        self.assertEqual(Payment.objects.count(), 0)


class TransferFormRenderingTest(TransferTestBase):
    """The page shows where both sides land as soon as they are picked.
    That reads off the rendered <option>, so the attributes carrying it
    are part of the contract, not decoration."""

    def test_account_options_carry_their_balance(self):
        response = self.client.get(self.url() + "?mode=cari")
        html = response.context["cari_form"]["from_cari"].as_widget()
        self.assertIn('data-balance="1000.00"', html)

    def test_cash_options_carry_their_balance(self):
        response = self.client.get(self.url())
        html = response.context["form"]["from_cash_account"].as_widget()
        self.assertIn('data-balance="5000.00"', html)
        self.assertIn('data-symbol="$"', html)

    def test_the_blank_choice_carries_no_balance(self):
        """The empty option has no instance behind it — reading one off
        it would put a stray 0.00 in the summary."""
        response = self.client.get(self.url() + "?mode=cari")
        html = response.context["cari_form"]["from_cari"].as_widget()
        blank = html.split("<option")[1]
        self.assertNotIn("data-balance", blank)

    def test_the_page_waits_for_a_rate_before_promising_a_figure(self):
        """A cari balance is carried in base currency. Transfer in
        another and the landing figure depends on the rate, so the page
        must have the wording to ask for one rather than subtract."""
        response = self.client.get(self.url() + "?mode=cari")
        self.assertContains(response, "Enter the exchange rate to see where they land.")

    def test_the_rate_override_row_is_on_the_page(self):
        response = self.client.get(self.url() + "?mode=cari")
        self.assertContains(response, 'id="tfFxRow"')
        self.assertContains(response, 'name="exchange_rate"')
        self.assertContains(response, "Use published")

    def test_currency_options_carry_their_code(self):
        """The converter asks the server for a pair by code, and the
        option label is a display string that must not be parsed."""
        response = self.client.get(self.url() + "?mode=cari")
        html = response.context["cari_form"]["currency"].as_widget()
        self.assertIn('data-code="TRY"', html)
        self.assertIn('data-code="USD"', html)

    def test_both_panes_render_so_switching_needs_no_round_trip(self):
        response = self.client.get(self.url())
        self.assertContains(response, 'id="tfCashForm"')
        self.assertContains(response, 'id="tfCariForm"')


class TransferPickerTest(TransferTestBase):
    """The account fields are typed into rather than scrolled through.
    The <select> underneath is what actually posts, so it has to stay
    intact and named — the typeahead only drives it."""

    def test_the_select_still_carries_the_field_name(self):
        response = self.client.get(self.url() + "?mode=cari")
        self.assertContains(response, 'name="from_cari"')
        self.assertContains(response, 'name="to_cari"')

    def test_every_account_is_in_the_page_to_search(self):
        """Filtering is client-side over the options already rendered —
        an account missing from the markup is unfindable."""
        response = self.client.get(self.url() + "?mode=cari")
        html = response.context["cari_form"]["from_cari"].as_widget()
        for cari in (self.a, self.b):
            self.assertIn(str(cari.pk), html)
            self.assertIn(cari.name, html)

    def test_picking_by_typing_posts_the_same_as_picking_from_the_list(self):
        """The typeahead sets the <select>, so the POST is unchanged —
        this is the shape the browser sends either way."""
        response = self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": str(self.a.pk),
            "to_cari": str(self.b.pk),
            "amount": "400.00",
            "currency": self.usd.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))


class CariTransferRateTest(TransferTestBase):
    """An account's balance is the sum of its movements in BASE currency,
    so the rate decides how many dollars actually leave one account and
    land on the other. Whoever was there may know it better than a
    published source does."""

    def transfer(self, **kwargs):
        defaults = dict(
            book=self.book, date="2026-02-01", from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.try_,
        )
        defaults.update(kwargs)
        t = CariTransfer.objects.create(**defaults)
        t.post()
        return t

    def test_a_typed_rate_is_what_both_legs_convert_at(self):
        t = self.transfer(exchange_rate=Decimal("0.025000"))

        self.assertEqual(t.from_movement.exchange_rate, Decimal("0.025000"))
        self.assertEqual(t.to_movement.exchange_rate, Decimal("0.025000"))
        # 400 TRY at 0.025 is 10 USD off one account and onto the other.
        self.assertEqual(t.from_movement.amount_base, Decimal("-10.00"))
        self.assertEqual(t.to_movement.amount_base, Decimal("10.00"))
        self.assertEqual(self.balances(), (Decimal("990.00"), Decimal("10.00")))

    def test_a_typed_rate_still_leaves_the_book_total_alone(self):
        self.transfer(exchange_rate=Decimal("0.025000"))
        self.assertEqual(sum(b for b in self.balances()), Decimal("1000.00"))

    def test_a_wrong_rate_moves_a_different_amount(self):
        """The point of the override: the same 400 lira lands as a
        different number of dollars, which is why it must be correctable."""
        cheap = self.transfer(exchange_rate=Decimal("0.020000"))
        self.assertEqual(cheap.to_movement.amount_base, Decimal("8.00"))
        cheap.unpost()

        dear = self.transfer(exchange_rate=Decimal("0.030000"))
        self.assertEqual(dear.to_movement.amount_base, Decimal("12.00"))

    def test_no_rate_typed_falls_back_to_the_published_one(self):
        """Blank means nobody said — not "one to one"."""
        t = self.transfer()
        self.assertIsNone(t.exchange_rate)
        self.assertEqual(t.from_movement.exchange_rate, t.to_movement.exchange_rate)
        self.assertEqual(
            t.from_movement.amount_base + t.to_movement.amount_base, Decimal("0.00")
        )

    def test_a_rate_is_ignored_when_there_is_nothing_to_convert(self):
        t = self.transfer(currency=self.usd, exchange_rate=Decimal("0.025000"))
        self.assertEqual(t.from_movement.exchange_rate, Decimal("1.000000"))
        self.assertEqual(t.to_movement.amount_base, Decimal("400.00"))

    def test_a_non_positive_rate_is_refused(self):
        """Zero converts the transfer to nothing; negative flips which
        side of the book each leg lands on."""
        for bad in (Decimal("0"), Decimal("-0.025")):
            with self.subTest(rate=bad):
                with self.assertRaises(ValidationError):
                    CariTransfer.objects.create(
                        book=self.book, date="2026-02-01",
                        from_cari=self.a, to_cari=self.b,
                        amount=Decimal("400.00"), currency=self.try_,
                        exchange_rate=bad,
                    )

    def test_the_form_refuses_a_non_positive_rate_without_a_500(self):
        response = self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": self.a.pk,
            "to_cari": self.b.pk,
            "amount": "400.00",
            "currency": self.try_.pk,
            "exchange_rate": "0",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("exchange_rate", response.context["cari_form"].errors)
        self.assertEqual(CariTransfer.objects.count(), 0)

    def test_the_rate_typed_on_the_form_reaches_the_ledger(self):
        response = self.client.post(self.url(), {
            "mode": "cari",
            "book": self.book.pk,
            "date": "2026-02-01",
            "from_cari": self.a.pk,
            "to_cari": self.b.pk,
            "amount": "400.00",
            "currency": self.try_.pk,
            "exchange_rate": "0.025",
        })
        self.assertEqual(response.status_code, 302)
        t = CariTransfer.objects.get()
        self.assertEqual(t.exchange_rate, Decimal("0.025000"))
        self.assertEqual(t.to_movement.amount_base, Decimal("10.00"))
