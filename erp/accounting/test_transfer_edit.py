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
