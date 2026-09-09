"""Creating an order is a PAGE, not a drawer.

Editing moved off the drawer because a 50vw overlay cannot show a
customer, a dozen lines and their prices at once, and closed on any click
landing outside it — one stray click and everything typed was gone.
Creating types MORE than editing does, so it had the better claim all
along.

The page is book-scoped, and that is the part that fixes a bug rather
than moving one. The drawer loaded /operating/orders/create, a URL naming
no book, so `current_book` fell back to the member's DEFAULT book however
deliberately they had opened a different book's order list — and every
line that names no book of its own is filed under `current_book`. An
order started from Ergene's list could be written into Laleli.

Run with:
    python manage.py test operating.test_create_order_page
"""
import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory


def _book_input(html):
    m = re.search(r'name="book" id="co-book-input"\s*value="([^"]*)"', html)
    return m.group(1) if m else None


class CreateOrderIsAPage(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        User = get_user_model()
        self.user = User.objects.create_user("seller", "s@t.com", "pw")
        self.user.member.books.add(self.laleli, self.ergene)
        # Working book is Laleli, so an unscoped form would say Laleli
        # whichever book's list the user actually opened.
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _url(self, book):
        return reverse("operating:create_order_page", kwargs={"book_id": book.pk})

    def test_it_renders_a_whole_page(self):
        resp = self.client.get(self._url(self.laleli))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "operating/create_order_page.html")

    def test_the_page_carries_the_form_the_sidebar_used(self):
        """The same partial, not the retired create_order.html, which
        carried a second hand-rolled copy of the form."""
        resp = self.client.get(self._url(self.laleli))
        self.assertTemplateUsed(resp, "operating/partials/create_order_form.html")
        self.assertTemplateNotUsed(resp, "operating/create_order.html")

    def test_it_offers_the_way_back(self):
        resp = self.client.get(self._url(self.laleli))
        self.assertContains(
            resp,
            reverse("operating:order_list_scoped", kwargs={"book_id": self.laleli.pk}))

    # ── the bug the scoping fixes ───────────────────────────────────
    def test_the_form_is_filed_under_the_book_in_the_url(self):
        """Not the member's default. Opening Ergene's create page while
        working in Laleli must produce a form that files its lines in
        Ergene — this is what the drawer got wrong."""
        html = self.client.get(self._url(self.ergene)).content.decode()
        self.assertEqual(_book_input(html), str(self.ergene.pk))

    def test_the_page_says_which_book_it_will_write_to(self):
        resp = self.client.get(self._url(self.ergene))
        self.assertContains(resp, "Ergene Fabric")

    def test_a_book_the_member_cannot_use_is_refused(self):
        stranger = Book.objects.create(name="Somebody Else Fabric")
        resp = self.client.get(self._url(stranger))
        self.assertEqual(resp.status_code, 404)

    # ── the drawer still works where it is still opened ─────────────
    def test_an_htmx_request_still_gets_the_bare_partial(self):
        resp = self.client.get(reverse("operating:create_order"),
                               headers={"hx-request": "true"})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "operating/partials/create_order_form.html")
        self.assertTemplateNotUsed(resp, "operating/create_order_page.html")

    # ── the drawer and the page are the same form ───────────────────
    def test_the_drawer_is_filed_under_the_book_it_was_asked_for(self):
        """A drawer has no URL of its own to name the book, so it sends
        ?book=. Without it the form falls back to the member's default —
        the bug the page fixed, which the drawer must not keep."""
        resp = self.client.get(
            reverse("operating:create_order"),
            {"book": self.ergene.pk}, headers={"hx-request": "true"})
        self.assertEqual(_book_input(resp.content.decode()), str(self.ergene.pk))

    def test_the_two_faces_agree_about_the_book(self):
        """The point of the pair: whichever way it was opened, the form
        files its lines in the same place."""
        page = self.client.get(self._url(self.ergene)).content.decode()
        drawer = self.client.get(
            reverse("operating:create_order"),
            {"book": self.ergene.pk},
            headers={"hx-request": "true"}).content.decode()
        self.assertEqual(_book_input(page), _book_input(drawer))
        self.assertEqual(_book_input(drawer), str(self.ergene.pk))

    def test_the_drawer_cannot_be_told_to_use_someone_else_s_book(self):
        """?book= arrives from the browser and may claim anything. A book
        the member is not assigned is ignored rather than obeyed."""
        stranger = Book.objects.create(name="Somebody Else Fabric")
        resp = self.client.get(
            reverse("operating:create_order"),
            {"book": stranger.pk}, headers={"hx-request": "true"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(_book_input(resp.content.decode()), str(stranger.pk))

    def test_the_drawer_is_the_same_size_as_every_other_drawer(self):
        """It used to override .sidebar-modal into a full-screen
        workspace, because the order form is denser than a contact or a
        task. The page took that job, so the drawer inherits again —
        which is what keeps it the same width as the contact and task
        drawers when THOSE change, rather than matching them today and
        drifting tomorrow.
        """
        with open("erp/templates/base.html", encoding="utf-8") as fh:
            base = fh.read()
        import re
        # Only rules aimed at the PANEL (or the overlay itself). The form
        # inside it may still say how wide its own content runs — that is
        # the form's business, and does not make the drawer a different
        # shape from its siblings.
        panel = re.findall(
            r"#orderSidebarOverlay(?:\s+\.sidebar-modal)?\s*\{[^}]*\}", base)
        for rule in panel:
            for prop in ("width", "height"):
                self.assertNotIn(
                    prop + ":", rule,
                    "the order drawer is sizing itself again: " + rule[:140])

    def test_the_drawer_opener_passes_the_book(self):
        """Guards the client half: the opener has to send ?book=, or the
        server has nothing to settle and quietly picks the default."""
        with open("erp/templates/base.html", encoding="utf-8") as fh:
            base = fh.read()
        opener = base[base.index("function openOrderSidebar("):][:1200]
        self.assertIn("?book=", opener)
        self.assertIn("current_book.pk", opener)
