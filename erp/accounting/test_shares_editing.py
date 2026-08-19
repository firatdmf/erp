# to run this test, use the command:
# python manage.py test accounting.test_shares_editing

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, StakeholderBook
from authentication.models import Member


class SharesEditingTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="shares_tester", password="pw")
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Laleli Fabric", total_shares=10000000)
        self.cuma = self.stakeholder("cuma", "Cuma", "Öztürk", 0)

    def stakeholder(self, username, first, last, shares):
        user = get_user_model().objects.create_user(username=username, password="pw")
        user.first_name, user.last_name = first, last
        user.save()
        return StakeholderBook.objects.create(
            member=Member.objects.get(user=user), book=self.book, shares=shares
        )

    def holding_url(self, sb=None):
        return reverse(
            "accounting:set_stakeholder_shares",
            kwargs={"pk": self.book.pk, "sb_pk": (sb or self.cuma).pk},
        )

    def pool_url(self, book=None):
        return reverse(
            "accounting:set_book_total_shares", kwargs={"pk": (book or self.book).pk}
        )


class SetStakeholderSharesTest(SharesEditingTestBase):
    def test_setting_a_holding_saves_and_returns_every_stake(self):
        response = self.client.post(self.holding_url(), {"shares": "10000000"})
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["issued"], 10000000)
        self.assertEqual(payload["stakeholders"][0]["pct"], "100.0")
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 10000000)

    def test_commas_from_the_displayed_figure_are_accepted(self):
        self.client.post(self.holding_url(), {"shares": "7,500,000"})
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 7500000)

    def test_the_book_cannot_be_over_allocated(self):
        """Every percentage on the page is measured against the pool, so
        exceeding it would make all of them wrong at once."""
        other = self.stakeholder("ayse", "Ayşe", "Küçük", 6000000)
        response = self.client.post(self.holding_url(), {"shares": "5000000"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("4,000,000", json.loads(response.content)["error"])
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 0)
        self.assertEqual(other.shares, 6000000)

    def test_a_holding_may_be_raised_to_exactly_the_pool(self):
        response = self.client.post(self.holding_url(), {"shares": "10000000"})
        self.assertEqual(response.status_code, 200)

    def test_its_own_current_holding_does_not_count_against_it(self):
        """Re-saving 9,000,000 as 9,500,000 must not read the old 9M as
        somebody else's allocation."""
        self.cuma.shares = 9000000
        self.cuma.save()
        response = self.client.post(self.holding_url(), {"shares": "9500000"})
        self.assertEqual(response.status_code, 200)
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 9500000)

    def test_rubbish_and_negatives_are_rejected(self):
        for bad in ("abc", "", "-5"):
            response = self.client.post(self.holding_url(), {"shares": bad})
            self.assertEqual(response.status_code, 400, bad)
        self.cuma.refresh_from_db()
        self.assertEqual(self.cuma.shares, 0)

    def test_a_stakeholder_of_another_book_is_not_reachable(self):
        other_book = Book.objects.create(name="Başka", total_shares=100)
        stranger = StakeholderBook.objects.create(
            member=self.cuma.member, book=other_book, shares=0
        )
        url = reverse(
            "accounting:set_stakeholder_shares",
            kwargs={"pk": self.book.pk, "sb_pk": stranger.pk},
        )
        self.assertEqual(self.client.post(url, {"shares": "50"}).status_code, 404)

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(self.holding_url(), {"shares": "500"})
        self.assertEqual(response.status_code, 302)


class SetBookTotalSharesTest(SharesEditingTestBase):
    def test_the_pool_can_be_resized(self):
        response = self.client.post(self.pool_url(), {"total_shares": "5000000"})
        self.assertEqual(response.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.total_shares, 5000000)

    def test_resizing_restates_every_stake(self):
        self.cuma.shares = 2500000
        self.cuma.save()
        payload = json.loads(
            self.client.post(self.pool_url(), {"total_shares": "5000000"}).content
        )
        self.assertEqual(payload["pool"], 5000000)
        self.assertEqual(payload["stakeholders"][0]["pct"], "50.0")

    def test_the_pool_cannot_shrink_below_what_is_allocated(self):
        self.cuma.shares = 8000000
        self.cuma.save()
        response = self.client.post(self.pool_url(), {"total_shares": "1000"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("8,000,000", json.loads(response.content)["error"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.total_shares, 10000000)

    def test_the_pool_may_equal_what_is_allocated(self):
        self.cuma.shares = 8000000
        self.cuma.save()
        response = self.client.post(self.pool_url(), {"total_shares": "8000000"})
        self.assertEqual(response.status_code, 200)

    def test_a_book_needs_at_least_one_share(self):
        response = self.client.post(self.pool_url(), {"total_shares": "0"})
        self.assertEqual(response.status_code, 400)
        self.book.refresh_from_db()
        self.assertEqual(self.book.total_shares, 10000000)

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(self.pool_url(), {"total_shares": "500"})
        self.assertEqual(response.status_code, 302)


class StakeholderFormSharesTest(SharesEditingTestBase):
    """The add-stakeholder form now takes the holding directly."""

    def add_url(self):
        return reverse("accounting:add_stakeholderbook", kwargs={"pk": self.book.pk})

    def test_the_form_offers_a_shares_field(self):
        response = self.client.get(self.add_url())
        self.assertIn("shares", response.context["form"].fields)

    def test_adding_a_stakeholder_with_a_holding(self):
        user = get_user_model().objects.create_user(username="yeni", password="pw")
        member = Member.objects.get(user=user)
        response = self.client.post(
            self.add_url(),
            {"member": member.pk, "book": self.book.pk, "shares": "2500000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            StakeholderBook.objects.get(member=member, book=self.book).shares, 2500000
        )

    def test_the_form_refuses_to_over_allocate(self):
        self.cuma.shares = 9000000
        self.cuma.save()
        user = get_user_model().objects.create_user(username="yeni", password="pw")
        member = Member.objects.get(user=user)
        response = self.client.post(
            self.add_url(),
            {"member": member.pk, "book": self.book.pk, "shares": "2000000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("shares", response.context["form"].errors)
        self.assertFalse(
            StakeholderBook.objects.filter(member=member, book=self.book).exists()
        )
