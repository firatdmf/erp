"""The product search has to be able to READ the book it searches in.

c494c492 made the search book-aware by moving its parameters into an
`hx-vals='js:{book: CO_BOOK_ID, cross_book: coCrossBook ...}'`
expression, so the "other books" toggle could change the answer while
the form was open. Both names are declared inside the form's script —
which is wrapped in an IIFE.

htmx evaluates a `js:` hx-vals with `Function("return (" + expr + ")")()`,
and a Function body runs in GLOBAL scope: it cannot see anything the
IIFE declared. So every keystroke raised `ReferenceError: CO_BOOK_ID is
not defined` inside getInputValues, issueAjaxRequest never fired, and
the search silently stopped suggesting anything — on the create sidebar
and the edit page alike. Nothing appeared server-side, because no
request was ever sent.

The parameters now travel in two hidden inputs the search pulls in with
hx-include. The DOM is reachable from both scopes, so there is no
expression left to evaluate and nothing to be out of scope.

Run with:
    python manage.py test operating.test_order_form_search_params
"""
import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import Product

from operating.models import Order, OrderItem

FORM = ("operating/templates/operating/partials/create_order_form.html")


class TheSearchCarriesItsBook(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.book = Book.objects.create(name="Laleli Fabric")
        current_account = CurrentAccount.objects.create(
            book=self.book, code="C-087", name="Anna", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(
            order_number="DK0000297", current_account=current_account)
        product = Product.objects.create(title="Crepe", sku="KZL000315", price=10)
        OrderItem.objects.create(order=self.order, product=product,
                                 quantity=Decimal("12.00"), price=Decimal("2.50"))
        self.client.force_login(
            User.objects.create_superuser("editor", "e@t.com", "pw"))

    def test_the_edit_page_names_the_orders_book_in_the_dom(self):
        """Not in a script variable: the search reads it off the page."""
        resp = self.client.get(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        html = resp.content.decode()
        book_input = re.search(
            r'<input type="hidden" name="book" id="co-book-input"\s*'
            r'value="([^"]*)"', html)
        self.assertIsNotNone(
            book_input, "the edit form lost the hidden book input")
        self.assertEqual(book_input.group(1), str(self.book.pk))

    def test_the_search_pulls_both_parameters_in(self):
        resp = self.client.get(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        html = resp.content.decode()
        search = re.search(r'id="co-product-search".*?>', html, re.S)
        self.assertIsNotNone(search, "the product search input is gone")
        self.assertIn("#co-book-input", search.group(0))
        self.assertIn("#co-cross-book-input", search.group(0))
        self.assertIn('id="co-cross-book-input"', html)

    def test_the_toggle_writes_where_the_search_reads(self):
        """Turning on "other books" has to reach the hidden input; a
        script variable alone would leave the search on one book."""
        with open(FORM, encoding="utf-8") as fh:
            form = fh.read()
        toggle = re.search(
            r"window\.coToggleCrossBook = function.*?\n  \};", form, re.S)
        self.assertIsNotNone(toggle)
        self.assertIn("co-cross-book-input", toggle.group(0))


class NoHxValsReachesIntoTheIife(TestCase):
    """The rule the bug broke, pinned for the whole form.

    htmx evaluates `js:`/`javascript:` hx-vals with Function(), whose
    body sees globals only — while every name in this form is declared
    inside its IIFE. So an hx-vals expression here may reference nothing
    but `window.`-qualified names, and the safe way to pass a value is
    the DOM.
    """

    def test_no_js_hx_vals_names_an_iife_local(self):
        with open(FORM, encoding="utf-8") as fh:
            form = fh.read()
        # The script really is wrapped — that is what makes the rule apply.
        self.assertIn("<script>\n(function() {", form)
        for expr in re.findall(
                r"hx-vals=['\"](?:js|javascript):(.*?)['\"]", form, re.S):
            # Object keys name nothing — {book: window.x} reads no `book`.
            reads = re.sub(r"([{,]\s*)[A-Za-z_$][\w$]*\s*:", r"\1", expr)
            names = set(re.findall(r"(?<![.\w])([A-Za-z_$][\w$]*)\s*(?![\w$(])",
                                   reads)) - {"true", "false", "null", "window"}
            self.assertFalse(
                names,
                f"hx-vals evaluates in global scope but names {sorted(names)}, "
                f"declared inside the form's IIFE — every keystroke would "
                f"raise a ReferenceError and send no request. Pass the value "
                f"through a hidden input and hx-include instead.")
