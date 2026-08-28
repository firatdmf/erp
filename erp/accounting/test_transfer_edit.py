# to run this test, use the command:
# python manage.py test accounting.test_transfer_edit

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounting.models import CariMovement, CariTransfer
from accounting.test_cari_transfer import TransferTestBase


class TransferEditPageTest(TransferTestBase):
    """A transfer owns two ledger rows in two accounts, so neither is
    editable where it sits. Until now that was a dead end: the row said a
    transfer owned it and had nowhere to send you, because a transfer could
    be made and never looked at again.
    """

    def setUp(self):
        super().setUp()
        self.transfer = CariTransfer.objects.create(
            book=self.book, date="2026-02-01",
            from_cari=self.a, to_cari=self.b,
            amount=Decimal("400.00"), currency=self.usd,
        )
        self.transfer.post()

    def edit_url(self, t=None):
        return reverse("accounts:transfer_edit", args=[(t or self.transfer).pk])

    def detail_url(self, t=None):
        return reverse("accounts:transfer_detail", args=[(t or self.transfer).pk])

    def undo_url(self, t=None):
        return reverse("accounts:transfer_undo", args=[(t or self.transfer).pk])

    # --- the way back from the ledger row -------------------------------

    def test_a_leg_now_links_to_the_transfer_that_owns_it(self):
        from accounting.views_accounts import _movement_owner
        label, url, editable = _movement_owner(self.transfer.from_movement)
        self.assertEqual(url, self.edit_url())
        self.assertFalse(editable, "the leg itself stays read-only")

    def test_the_leg_is_still_not_editable_in_place(self):
        """The rule that sent us here has not been relaxed."""
        r = self.client.get(reverse("accounts:movement_edit",
                                    args=[self.a.pk, self.transfer.from_movement.pk]))
        self.assertEqual(r.status_code, 302)

    # --- correcting it ---------------------------------------------------

    def test_the_page_opens(self):
        r = self.client.get(self.edit_url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["transfer"].pk, self.transfer.pk)

    def test_a_new_amount_moves_both_legs_together(self):
        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))
        r = self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": self.b.pk,
            "amount": "250.00", "currency": self.usd.pk,
        })
        self.assertEqual(r.status_code, 302)
        # Lands on the transfer, not on one of the two statements — which
        # would answer for one account and say nothing about the other.
        self.assertEqual(r["Location"], self.detail_url())
        self.assertEqual(self.balances(), (Decimal("750.00"), Decimal("250.00")))

    def test_the_corrected_pair_still_nets_to_zero(self):
        """The invariant the model exists to keep: one rate, one date, so
        the two legs cancel in base currency as well as in the one typed."""
        self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-03-05",
            "from_cari": self.a.pk, "to_cari": self.b.pk,
            "amount": "250.00", "currency": self.usd.pk,
        })
        self.transfer.refresh_from_db()
        legs = [self.transfer.from_movement, self.transfer.to_movement]
        self.assertEqual(sum(m.amount_base for m in legs), Decimal("0.00"))
        self.assertEqual(len({m.exchange_rate for m in legs}), 1)
        self.assertEqual(len({m.date for m in legs}), 1)

    def test_it_leaves_exactly_two_legs_behind(self):
        """Saving is unpost-then-post, so the old rows go rather than
        piling up beside the new ones."""
        self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": self.b.pk,
            "amount": "250.00", "currency": self.usd.pk,
        })
        self.assertEqual(
            CariMovement.objects.filter(reference=f"TRANSFER {self.transfer.pk}").count(), 2)

    def test_redirecting_the_transfer_moves_the_balance_to_the_new_account(self):
        c = self.b.__class__.objects.create(
            book=self.book, code="01786", name="ÜÇÜNCÜ", default_currency=self.usd)
        self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": c.pk,
            "amount": "400.00", "currency": self.usd.pk,
        })
        self.b.refresh_from_db(); c.refresh_from_db()
        self.assertEqual(self.b.cached_balance, Decimal("0.00"))
        self.assertEqual(c.cached_balance, Decimal("400.00"))

    def test_a_rejected_edit_leaves_the_transfer_as_it_was(self):
        """Both accounts the same is the one thing the form refuses. The
        legs must survive it — unpost() runs inside the transaction."""
        r = self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": self.a.pk,
            "amount": "250.00", "currency": self.usd.pk,
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        self.assertEqual(self.balances(), (Decimal("600.00"), Decimal("400.00")))
        self.transfer.refresh_from_db()
        self.assertIsNotNone(self.transfer.from_movement_id)

    # --- undoing it ------------------------------------------------------

    def test_undo_removes_both_legs_and_the_transfer(self):
        r = self.client.post(self.undo_url())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.balances(), (Decimal("1000.00"), Decimal("0.00")))
        self.assertEqual(CariTransfer.objects.count(), 0)
        self.assertEqual(
            CariMovement.objects.filter(reference=f"TRANSFER {self.transfer.pk}").count(), 0)

    def test_undo_is_post_only(self):
        self.assertEqual(self.client.get(self.undo_url()).status_code, 405)

    # --- the detail page -------------------------------------------------

    def test_the_detail_page_names_both_legs(self):
        r = self.client.get(self.detail_url())
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for account in (self.a, self.b):
            self.assertIn(account.code, html)
            self.assertIn(reverse("accounts:movement_detail",
                                  args=[account.pk, getattr(
                                      self.transfer,
                                      "from_movement" if account == self.a else "to_movement").pk]),
                          html)

    def test_the_detail_page_offers_edit_and_undo(self):
        html = self.client.get(self.detail_url()).content.decode()
        self.assertIn(self.edit_url(), html)
        self.assertIn(self.undo_url(), html)

    def test_the_leg_links_to_the_edit_form_not_the_detail_page(self):
        """Same as an invoice or a payment: the ledger row's button is the
        one that corrects the document, because that is what the note beside
        it tells the reader to do."""
        from accounting.views_accounts import _movement_owner
        _label, url, _editable = _movement_owner(self.transfer.from_movement)
        self.assertEqual(url, self.edit_url())


class TransferEditRateTest(TransferTestBase):
    """The rate row: the same two-way converter the create page has.

    Both legs are stamped from one rate, so it decides how many base-currency
    units actually leave one account and land on the other.
    """

    def setUp(self):
        super().setUp()
        self.transfer = CariTransfer.objects.create(
            book=self.book, date="2026-02-01",
            from_cari=self.a, to_cari=self.b,
            amount=Decimal("1000.00"), currency=self.try_,
            exchange_rate=Decimal("0.020000"),
        )
        self.transfer.post()

    def edit_url(self):
        return reverse("accounts:transfer_edit", args=[self.transfer.pk])

    def test_the_page_knows_what_it_converts_into(self):
        r = self.client.get(self.edit_url())
        self.assertEqual(r.context["base_currency"].code, "USD")

    def test_the_rate_row_is_rendered(self):
        html = self.client.get(self.edit_url()).content.decode()
        for hook in ("mfFxRow", "mfFxBaseTotal", "mfFxReset", "mfTransferForm"):
            self.assertIn(hook, html)

    def test_a_corrected_rate_reaches_both_legs(self):
        """Typing a rate — or the base total that implies it — is the whole
        point of the row, so it has to land on the rows that are written."""
        self.client.post(self.edit_url(), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": self.b.pk,
            "amount": "1000.00", "currency": self.try_.pk,
            "exchange_rate": "0.030000",
        })
        self.transfer.refresh_from_db()
        legs = [self.transfer.from_movement, self.transfer.to_movement]
        self.assertEqual({m.exchange_rate for m in legs}, {Decimal("0.030000")})
        self.assertEqual({abs(m.amount_base) for m in legs}, {Decimal("30.00")})
        self.assertEqual(sum(m.amount_base for m in legs), Decimal("0.00"))

    def test_an_edit_does_not_force_todays_date_into_the_widget(self):
        """The instance carries its own date. Forcing today's in beside it
        rendered a second value attribute after the real one."""
        from accounting.forms import CariTransferForm
        form = CariTransferForm(instance=self.transfer, book=self.book)
        self.assertNotIn("value", form.fields["date"].widget.attrs)
        self.assertEqual(str(form["date"]).count('value='), 1)

    def test_a_new_transfer_still_defaults_to_today(self):
        from datetime import date as _date
        from accounting.forms import CariTransferForm
        form = CariTransferForm(book=self.book)
        self.assertEqual(form.fields["date"].widget.attrs.get("value"),
                         _date.today().strftime("%Y-%m-%d"))

    def test_the_base_total_the_operator_types_is_the_one_that_posts(self):
        """The complaint this precision exists for.

        At 43,940 TRY one step of a SIXTH decimal moves the base total by
        4.4 cents, so $913.00 was not on the grid — the rate rounded to
        0.020778 and the ledger came back 912.99, every time. Eight decimals
        put every cent within reach.
        """
        big = CariTransfer.objects.create(
            book=self.book, date="2026-02-01",
            from_cari=self.a, to_cari=self.b,
            amount=Decimal("43940.00"), currency=self.try_,
            exchange_rate=Decimal("0.02077800"),
        )
        big.post()
        self.assertEqual(abs(big.from_movement.amount_base), Decimal("912.99"))

        # The rate the page derives from a typed total of 913.00.
        self.client.post(reverse("accounts:transfer_edit", args=[big.pk]), {
            "book": self.book.pk, "date": "2026-02-01",
            "from_cari": self.a.pk, "to_cari": self.b.pk,
            "amount": "43940.00", "currency": self.try_.pk,
            "exchange_rate": "0.02077833",
        })
        big.refresh_from_db()
        legs = [big.from_movement, big.to_movement]
        self.assertEqual({abs(m.amount_base) for m in legs}, {Decimal("913.00")})
        self.assertEqual(sum(m.amount_base for m in legs), Decimal("0.00"))

    def test_the_rate_column_keeps_all_eight_decimals(self):
        """Widening the transfer alone would not have worked: post() stamps
        its rate straight onto both legs, so CariMovement had to widen with
        it or round the rate right back on the way into the ledger."""
        from accounting.models import CariMovement
        rate = Decimal("0.02077833")
        self.transfer.exchange_rate = rate
        self.transfer.save()
        self.transfer.unpost()
        self.transfer.post()
        self.transfer.refresh_from_db()
        for leg in (self.transfer.from_movement, self.transfer.to_movement):
            self.assertEqual(leg.exchange_rate, rate)
        self.assertEqual(CariMovement._meta.get_field("exchange_rate").decimal_places, 8)

    def test_the_rate_box_accepts_eight_decimals(self):
        from accounting.forms import CariTransferForm
        form = CariTransferForm(book=self.book)
        self.assertEqual(form.fields["exchange_rate"].widget.attrs["step"], "0.00000001")
