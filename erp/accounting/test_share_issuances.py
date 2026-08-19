# to run this test, use the command:
# python manage.py test accounting.test_share_issuances

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, ShareIssuance, StakeholderBook
from authentication.models import Member


class SharesTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="shares_tester", password="pw")
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Laleli Fabric", total_shares=10000000)
        self.cuma = self.stakeholder("cuma", "Cuma", "Öztürk")

    def stakeholder(self, username, first, last):
        user = get_user_model().objects.create_user(username=username, password="pw")
        user.first_name, user.last_name = first, last
        user.save()
        return StakeholderBook.objects.create(
            member=Member.objects.get(user=user), book=self.book, shares=0
        )

    def issue(self, sb, shares, reason="capital", date="2026-08-19"):
        return ShareIssuance.objects.create(
            stakeholder=sb, shares=shares, date=date, reason=reason
        )

    def url(self, book=None):
        return reverse("accounting:book_shares", kwargs={"pk": (book or self.book).pk})


class HoldingIsDerivedTest(SharesTestBase):
    """`shares` is a cache of the issuance rows, like the cari balance."""

    def test_an_issuance_updates_the_holding(self):
        self.issue(self.cuma, 10000000)
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 10000000)

    def test_issuances_accumulate(self):
        self.issue(self.cuma, 6000000)
        self.issue(self.cuma, 1500000)
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 7500000)

    def test_a_negative_row_takes_shares_back(self):
        self.issue(self.cuma, 10000000)
        self.issue(self.cuma, -2500000, reason="buyback")
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 7500000)

    def test_deleting_an_issuance_restates_the_holding(self):
        first = self.issue(self.cuma, 4000000)
        self.issue(self.cuma, 1000000)
        first.delete()
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 1000000)

    def test_recompute_is_idempotent(self):
        self.issue(self.cuma, 3000000)
        for _ in range(3):
            self.cuma.recompute_shares()
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 3000000)

    def test_a_stakeholder_with_history_cannot_be_deleted(self):
        """PROTECT — losing the holder would lose why ownership moved."""
        from django.db.models import ProtectedError
        self.issue(self.cuma, 1000)
        with self.assertRaises(ProtectedError):
            self.cuma.delete()


class BookSharesPageTest(SharesTestBase):
    def test_the_page_shows_the_cap_table_and_the_history(self):
        self.issue(self.cuma, 10000000, reason="opening")
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Cuma Öztürk", html)
        self.assertIn("10,000,000", html)
        self.assertIn("100.00%", html)
        self.assertIn("Opening holding", html)

    def test_recording_an_issuance_from_the_page(self):
        response = self.client.post(self.url(), {
            "stakeholder": self.cuma.pk, "shares": "2,500,000",
            "date": "2026-08-19", "reason": "capital", "note": "Opening cash",
        })
        self.assertRedirects(response, self.url())
        issuance = ShareIssuance.objects.get()
        self.assertEqual(issuance.shares, 2500000)
        self.assertEqual(issuance.note, "Opening cash")
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 2500000)

    def test_the_recorder_is_attributed(self):
        self.client.post(self.url(), {
            "stakeholder": self.cuma.pk, "shares": "100", "date": "2026-08-19",
        })
        self.assertEqual(
            ShareIssuance.objects.get().created_by, Member.objects.get(user=self.user)
        )

    def test_the_book_cannot_be_over_allocated(self):
        other = self.stakeholder("ayse", "Ayşe", "Küçük")
        self.issue(other, 6000000)
        response = self.client.post(self.url(), {
            "stakeholder": self.cuma.pk, "shares": "5000000", "date": "2026-08-19",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("4,000,000", response.context["error"])
        self.assertEqual(ShareIssuance.objects.filter(stakeholder=self.cuma).count(), 0)

    def test_you_cannot_take_back_more_than_is_held(self):
        self.issue(self.cuma, 1000)
        response = self.client.post(self.url(), {
            "stakeholder": self.cuma.pk, "shares": "-5000", "date": "2026-08-19",
        })
        self.assertEqual(response.status_code, 400)
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 1000)

    def test_zero_is_not_a_movement(self):
        response = self.client.post(self.url(), {
            "stakeholder": self.cuma.pk, "shares": "0", "date": "2026-08-19",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ShareIssuance.objects.count(), 0)

    def test_a_stakeholder_of_another_book_is_refused(self):
        other_book = Book.objects.create(name="Başka", total_shares=100)
        stranger = StakeholderBook.objects.create(
            member=self.cuma.member, book=other_book, shares=0
        )
        response = self.client.post(self.url(), {
            "stakeholder": stranger.pk, "shares": "50", "date": "2026-08-19",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ShareIssuance.objects.count(), 0)

    def test_the_pool_can_be_resized(self):
        response = self.client.post(
            self.url(), {"action": "pool", "total_shares": "5,000,000"}
        )
        self.assertRedirects(response, self.url())
        self.book.refresh_from_db()
        self.assertEqual(self.book.total_shares, 5000000)

    def test_the_pool_cannot_shrink_below_what_is_allocated(self):
        self.issue(self.cuma, 8000000)
        response = self.client.post(
            self.url(), {"action": "pool", "total_shares": "1000"}
        )
        self.assertEqual(response.status_code, 400)
        self.book.refresh_from_db()
        self.assertEqual(self.book.total_shares, 10000000)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)


class BookHeaderIsReadOnlyTest(SharesTestBase):
    """The header summarises; it no longer edits."""

    def test_the_header_links_to_the_shares_page(self):
        response = self.client.get(
            reverse("accounting:book_detail", kwargs={"pk": self.book.pk})
        )
        html = response.content.decode()
        self.assertIn(self.url(), html)

    def test_the_header_carries_no_inline_editor(self):
        response = self.client.get(
            reverse("accounting:book_detail", kwargs={"pk": self.book.pk})
        )
        html = response.content.decode()
        self.assertNotIn('class="hs-shares" role="button"', html)
        self.assertNotIn('class="hs-pool"', html)
