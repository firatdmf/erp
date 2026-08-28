# to run this test, use the command:
# python manage.py test accounting.test_book_stakeholders

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, StakeholderBook
from authentication.models import Member


class BookHeaderStakeholdersTest(TestCase):
    """Stakeholders and their stake, shown in the book page header."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="sh_tester", password="pw")
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Laleli Fabric", total_shares=10000000)

    def member(self, username, first, last):
        user = get_user_model().objects.create_user(username=username, password="pw")
        user.first_name, user.last_name = first, last
        user.save()
        return Member.objects.get(user=user)   # auto-created by the User post_save signal

    def url(self):
        return reverse("accounting:book_detail", kwargs={"pk": self.book.pk})

    def test_header_lists_each_stakeholder_with_shares_and_stake(self):
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=7500000
        )
        response = self.client.get(self.url())
        rows = response.context["stakeholders"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["shares"], 7500000)
        self.assertEqual(rows[0]["pct"], Decimal("75.0"))

        html = response.content.decode()
        self.assertIn("Cuma Öztürk", html)
        self.assertIn("7,500,000", html)
        self.assertIn("75.0%", html)

    def test_stakeholders_are_ordered_by_holding(self):
        StakeholderBook.objects.create(
            member=self.member("a", "Ayşe", "Küçük"), book=self.book, shares=1000000
        )
        StakeholderBook.objects.create(
            member=self.member("b", "Cuma", "Öztürk"), book=self.book, shares=9000000
        )
        rows = self.client.get(self.url()).context["stakeholders"]
        self.assertEqual([r["shares"] for r in rows], [9000000, 1000000])
        self.assertEqual([r["pct"] for r in rows], [Decimal("90.0"), Decimal("10.0")])

    def test_unissued_stakeholder_reads_zero_not_a_blank(self):
        """A stakeholder with no shares yet is a real state — it shows 0%,
        muted, rather than being hidden or left empty."""
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=0
        )
        response = self.client.get(self.url())
        self.assertEqual(response.context["stakeholders"][0]["pct"], Decimal("0.0"))
        self.assertIn('class="hs-pct zero"', response.content.decode())

    def test_unissued_pool_is_reported(self):
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=4000000
        )
        response = self.client.get(self.url())
        self.assertEqual(response.context["shares_issued"], 4000000)
        self.assertEqual(response.context["shares_pool"], 10000000)
        self.assertIn(
            "4,000,000 of 10,000,000 shares issued", response.content.decode()
        )

    def test_a_fully_issued_book_still_shows_the_pool(self):
        """The pool line is the handle for resizing the pool, so it stays
        even when there is nothing left unissued to report."""
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=10000000
        )
        html = self.client.get(self.url()).content.decode()
        self.assertIn("100.0%", html)
        self.assertIn("shares issued", html)
        self.assertIn("10,000,000", html)

    def test_a_book_with_no_shares_pool_shows_no_percentage(self):
        """total_shares=0 would divide by nothing — show a dash, not a crash."""
        self.book.total_shares = 0
        self.book.save()
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=0
        )
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["stakeholders"][0]["pct"])

    def test_a_book_with_none_points_at_the_cap_table(self):
        """Empty state sends you to the cap table, which is where shares
        are issued. The book page itself no longer carries the add
        action — that moved to the Accounting menu with the rest of the
        entry actions when this page became a report."""
        response = self.client.get(self.url())
        self.assertEqual(response.context["stakeholders"], [])
        html = response.content.decode()
        self.assertIn("Add a stakeholder", html)
        self.assertIn(
            reverse("accounting:book_shares", kwargs={"pk": self.book.pk}), html
        )

    def test_the_bottom_card_is_gone(self):
        """It moved into the header — it must not be rendered twice."""
        StakeholderBook.objects.create(
            member=self.member("cuma", "Cuma", "Öztürk"), book=self.book, shares=10000000
        )
        html = self.client.get(self.url()).content.decode()
        self.assertNotIn("stakeholders-footer-card", html)
        # The name still legitimately appears in the page's member
        # dropdowns, so count only the stakeholder rows themselves.
        self.assertEqual(html.count('class="hs-name"'), 1)
