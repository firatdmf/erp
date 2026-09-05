# to run this test, use the command:
# python manage.py test accounting.test_member_book

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from accounting.services_accounts import acting_member, get_default_book
from authentication.models import Member


class MemberWorkingBook(TestCase):
    """Which business a record belongs to follows the person entering
    it, not the server."""

    def setUp(self):
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        # A Member is created for every User by signal, so fetch rather
        # than create.
        self.user = get_user_model().objects.create_user(
            username="ergene_staff", password="pw")
        self.member = Member.objects.get(user=self.user)
        self.member.books.set([self.laleli, self.ergene])

    def test_the_book_they_picked_wins(self):
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        self.assertEqual(get_default_book(self.member).pk, self.ergene.pk)

    def test_a_member_with_no_pick_gets_their_first_assigned_book(self):
        """Assigned books are ordered by name, so Ergene comes first."""
        self.assertEqual(get_default_book(self.member).pk, self.ergene.pk)

    def test_two_members_book_into_different_places(self):
        other = Member.objects.get(
            user=get_user_model().objects.create_user(username="laleli_staff",
                                                      password="pw"))
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        other.books.set([self.laleli])
        other.default_book = self.laleli
        other.save(update_fields=["default_book"])
        self.assertEqual(get_default_book(self.member).pk, self.ergene.pk)
        self.assertEqual(get_default_book(other).pk, self.laleli.pk)

    def test_no_member_at_all_still_resolves(self):
        """Cron jobs, imports and the shell have no member."""
        with self.settings(CARI_BOOK_ID=str(self.laleli.pk)):
            self.assertEqual(get_default_book(None).pk, self.laleli.pk)

    def test_it_is_read_from_the_request_when_not_passed(self):
        """~15 call sites have no member in scope, so the acting member
        comes from the middleware's thread-local."""
        from operating.audit import CurrentUserMiddleware
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        # The signal that creates a Member caches it on the User, so
        # drop that cache — a real request loads the user fresh.
        self.user.refresh_from_db()

        seen = {}

        def view(request):
            seen["member"] = acting_member()
            seen["book"] = get_default_book()
            return "response"

        request = type("R", (), {"user": self.user})()
        CurrentUserMiddleware(view)(request)
        self.assertEqual(seen["member"], self.member)
        self.assertEqual(seen["book"].pk, self.ergene.pk)

    def test_the_thread_local_is_cleared_after_the_request(self):
        """Otherwise one member's book would leak into the next
        request handled by the same worker thread."""
        from operating.audit import CurrentUserMiddleware
        CurrentUserMiddleware(lambda r: "response")(
            type("R", (), {"user": self.user})())
        self.assertIsNone(acting_member())

    def test_a_new_cari_lands_in_the_members_book(self):
        from crm.models import Company
        from accounting.models import CurrencyCategory
        from accounting.services_accounts import get_or_create_cari_for_company
        CurrencyCategory.objects.get_or_create(code="USD",
                                               defaults={"name": "USD"})
        self.member.default_book = self.ergene
        self.member.save(update_fields=["default_book"])
        company = Company.objects.create(name="Acme Tekstil")
        cari = get_or_create_cari_for_company(company, member=self.member)
        self.assertEqual(cari.book_id, self.ergene.pk)


class WorkingBookEndpoint(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Ergene Fabric")
        self.other = Book.objects.create(name="Laleli Fabric")
        self.user = get_user_model().objects.create_user(
            username="staff", password="pw")
        self.member = Member.objects.get(user=self.user)
        self.member.books.set([self.book, self.other])
        self.member.default_book = self.other
        self.member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

    def url(self, book=None):
        return reverse("accounting:set_my_working_book",
                       kwargs={"pk": (book or self.book).pk})

    def test_it_sets_the_members_book(self):
        resp = self.client.post(self.url())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])
        self.member.refresh_from_db()
        self.assertEqual(self.member.default_book_id, self.book.pk)

    def test_it_refuses_to_leave_them_with_no_book(self):
        """There is no unsetting a working book. "Cleared" never meant
        booking nowhere — get_default_book just picked the first book they
        were assigned, which is the guess this field replaces."""
        resp = self.client.post(self.url(), {"clear": "1"})
        self.assertEqual(resp.status_code, 400)
        self.member.refresh_from_db()
        self.assertEqual(self.member.default_book_id, self.other.pk)

    def test_it_only_touches_the_acting_member(self):
        stranger = Member.objects.get(
            user=get_user_model().objects.create_user(username="other",
                                                      password="pw"))
        stranger.books.set([self.other])
        stranger.default_book = self.other
        stranger.save(update_fields=["default_book"])
        self.client.post(self.url())
        stranger.refresh_from_db()
        self.assertEqual(stranger.default_book_id, self.other.pk)

    def test_the_page_knows_whose_book_it_is(self):
        self.client.post(self.url())
        ctx = self.client.get(
            reverse("accounting:book_detail", kwargs={"pk": self.book.pk})).context
        self.assertTrue(ctx["is_my_working_book"])
        other = self.client.get(
            reverse("accounting:book_detail", kwargs={"pk": self.other.pk})).context
        self.assertFalse(other["is_my_working_book"])

    def test_picking_a_book_says_so_on_the_next_page(self):
        """The switcher navigates straight after this POST, so the
        confirmation has to survive into the page it lands on — the app's
        own flash, not a toast the JSON response would have to raise."""
        from django.contrib.messages import get_messages
        resp = self.client.post(self.url())
        said = [str(m) for m in get_messages(resp.wsgi_request)]
        self.assertEqual(said, ['Working book set to "Ergene Fabric".'])

    def test_a_refused_clear_says_nothing(self):
        from django.contrib.messages import get_messages
        resp = self.client.post(self.url(), {"clear": "1"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual([str(m) for m in get_messages(resp.wsgi_request)], [])

    def test_a_refused_book_says_nothing(self):
        """A member who may not use the book gets 403 and no flash — a
        confirmation for something that did not happen is worse than none."""
        from django.contrib.messages import get_messages
        self.member.books.set([self.other])
        resp = self.client.post(self.url())
        self.assertEqual(resp.status_code, 403)
        self.assertEqual([str(m) for m in get_messages(resp.wsgi_request)], [])


class RetailCariIsNamedInEnglish(TestCase):
    """The shared walk-in account is written by code, never typed, so its
    name is ours to state — and the database states things in English."""

    def setUp(self):
        from accounting.models import CurrencyCategory
        # get_or_create_retail_cari resolves a currency for the new row,
        # and default_currency is NOT NULL.
        CurrencyCategory.objects.create(code="USD", name="US Dollar",
                                        symbol="$")

    def test_a_fresh_install_creates_it_in_english(self):
        from accounting.services_accounts import get_or_create_retail_cari
        cari = get_or_create_retail_cari()
        self.assertEqual(cari.code, "PERAKENDE")
        self.assertEqual(cari.name, "Retail Sales")
        self.assertNotIn("Perakende", cari.notes)
