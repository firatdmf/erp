# to run this test, use the command:
# python manage.py test accounting.test_book_rename

import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book


class RenameBookTest(TestCase):
    """Inline rename from the book detail page header."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="rename_tester", password="pw"
        )
        self.client.force_login(self.user)
        self.book = Book.objects.create(name="Demfirat", total_shares=10000000)
        self.other = Book.objects.create(name="Nejum")

    def url(self, book=None):
        return reverse("accounting:rename_book", kwargs={"pk": (book or self.book).pk})

    def test_rename_saves_and_returns_the_new_name(self):
        response = self.client.post(self.url(), {"name": "Demfirat Tekstil"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content), {"success": True, "name": "Demfirat Tekstil"}
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat Tekstil")

    def test_rename_leaves_total_shares_alone(self):
        """The rename form is name-only — total_shares divides every
        stakeholder's percentage and must not ride along."""
        self.client.post(self.url(), {"name": "Yeni Ad", "total_shares": 42})
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Yeni Ad")
        self.assertEqual(self.book.total_shares, 10000000)

    def test_duplicate_name_is_rejected(self):
        response = self.client.post(self.url(), {"name": "Nejum"})
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertFalse(payload["success"])
        self.assertIn("name", payload["errors"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat")

    def test_empty_name_is_rejected(self):
        response = self.client.post(self.url(), {"name": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", json.loads(response.content)["errors"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat")

    def test_surrounding_whitespace_is_trimmed(self):
        self.client.post(self.url(), {"name": "  Demfirat Halı  "})
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat Halı")

    def test_renaming_one_book_does_not_touch_another(self):
        self.client.post(self.url(), {"name": "Değişti"})
        self.other.refresh_from_db()
        self.assertEqual(self.other.name, "Nejum")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url()).status_code, 405)

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(self.url(), {"name": "Anonim"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.name, "Demfirat")

    def test_detail_page_edits_the_printed_title_in_place(self):
        """The pencil and the rename endpoint hang off the <h1> itself —
        there is no second input rendered under it to type into."""
        response = self.client.get(
            reverse("accounting:book_detail", kwargs={"pk": self.book.pk})
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="bookTitleEditBtn"', html)
        self.assertIn('id="bookTitle" data-rename-url="%s"' % self.url(), html)
        self.assertNotIn('id="bookTitleInput"', html)
