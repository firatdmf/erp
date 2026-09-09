"""The order form asks for one thing at a time.

Two changes, one idea: do not put work in front of someone before it can
mean anything.

A delivery address is five empty fields, and most orders do not need
them — they were the first thing between picking a customer and picking
what that customer is buying. They are folded behind a button now.

And the sections gate. Products is closed until there is a customer;
Deposit & Notes is closed until there is a line. Neither is decoration:
an order with no customer cannot be saved at all, so picking products for
nobody is work the save then refuses. The gate says so before the work
instead of after it.

The gate reads live state rather than a "furthest step reached" counter,
which is what makes an EDIT behave like the plain form it always was: its
customer and its lines arrive already filled, so everything is open from
the first paint.

Run with:
    python manage.py test operating.test_order_form_steps
"""
import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product

from .models import Order, OrderItem

FORM = "operating/templates/operating/partials/create_order_form.html"


def read_form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def section_classes(html):
    """id -> the classes it is painted with, straight out of the markup."""
    return {m.group(2): m.group(1)
            for m in re.finditer(r'<div class="(co-section[^"]*)" id="(co-step-\d+)"', html)}


class TheFormOpensOneStepAtATime(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        User = get_user_model()
        user = User.objects.create_superuser("seller", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _create_form(self):
        return self.client.get(
            reverse("operating:create_order_page", kwargs={"book_id": self.book.pk})
        ).content.decode()

    # ── how a fresh form is painted ─────────────────────────────────
    def test_only_the_customer_step_is_open_to_begin_with(self):
        classes = section_classes(self._create_form())
        # co-step-3 is the CUSTOMER section — the ids are historical and
        # do not run in the order the badges do.
        self.assertIn("active", classes["co-step-3"], "customer should be open")
        self.assertNotIn("active", classes["co-step-2"], "products should be closed")
        self.assertNotIn("active", classes["co-step-4"], "deposit should be closed")

    def test_the_gate_is_driven_by_what_the_form_holds(self):
        """Not by a counter of how far the user has got. A counter would
        keep Products open after the customer was cleared."""
        form = read_form()
        self.assertIn("function coStepReady", form)
        self.assertIn("orderItems.length > 0", form)
        # Every place the state can change re-asks the question.
        self.assertGreaterEqual(form.count("coRefreshSteps()"), 4)

    def test_a_locked_step_cannot_be_opened_by_clicking_it(self):
        """The header is still a control; refusing the click is what makes
        the lock real rather than a style."""
        form = read_form()
        toggle = form[form.index("window.coToggle = function"):][:420]
        self.assertIn("coStepReady", toggle)
        self.assertIn("showToast", toggle)

    def test_a_locked_step_is_also_a_closed_one(self):
        """Locking the header but leaving the body open would stop the
        click and not the reading."""
        refresh = read_form()
        body = refresh[refresh.index("function coRefreshSteps"):][:600]
        self.assertIn("classList.remove('active')", body)

    # ── the delivery address ────────────────────────────────────────
    def test_the_delivery_address_is_folded_away(self):
        html = self._create_form()
        self.assertIn('id="co-delivery-add"', html)
        self.assertIn('id="co-delivery-body" hidden', html)

    def test_the_fields_still_post_under_their_own_names(self):
        """Folded, not replaced: the inputs are the same ones, so an
        address typed in still arrives exactly as it did."""
        html = self._create_form()
        for name in ("delivery_address_title", "delivery_address",
                     "delivery_city", "delivery_country", "delivery_phone"):
            self.assertIn(f'name="{name}"', html)

    def test_closing_it_clears_what_was_typed(self):
        """The button says whether this order HAS a delivery address, so
        closing it has to mean the order does not have one — otherwise it
        posts an address the user believes they removed."""
        form = read_form()
        fn = form[form.index("window.coToggleDelivery = function"):][:700]
        self.assertIn("el.value =", fn)
        self.assertIn("delivery_country", fn)

    def test_an_address_already_on_the_order_opens_itself(self):
        """Editing must never hide what is already there behind a button
        that reads 'add'."""
        self.assertIn("function coSyncDeliveryDisclosure", read_form())


class EditingIsNotAWizard(TestCase):
    """An edit arrives with its customer and its lines, so the same
    state-driven gate leaves everything open."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        contact = Contact.objects.create(name="Oleg")
        account = CurrentAccount.objects.create(
            book=self.book, code="C-1", name="Oleg", type="customer",
            contact=contact, default_currency=usd)
        self.order = Order.objects.create(
            order_number="DK0000901", current_account=account, contact=contact)
        product = Product.objects.create(title="Krep", sku="K24644")
        OrderItem.objects.create(order=self.order, product=product,
                                 quantity=Decimal("50"), price=Decimal("2"))
        User = get_user_model()
        user = User.objects.create_superuser("editor9", "e9@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def test_the_edit_form_unlocks_from_what_it_was_given(self):
        html = self.client.get(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk})
        ).content.decode()
        # The customer preset and the hydrated items are what open the
        # later steps, and they run before the gate is settled.
        self.assertIn("co-customer-preset", html)
        self.assertIn("existing-order-items", html)
        tail = html[html.index("coSyncDeliveryDisclosure();"):][:200]
        self.assertIn("coRefreshSteps();", tail)
        self.assertIn("coAdvanceTo(2);", tail)
        self.assertIn("coAdvanceTo(3);", tail)


class SearchResultsCloseWhenTheyStopBeingTheAnswer(TestCase):
    """Both searches filled a container and left it filled.

    The list stayed under the form once the field lost focus, and once it
    was emptied, sitting between the reader and the section below it.
    htmx only ever fills the container, so something has to empty it.
    """

    def test_both_searches_are_wired(self):
        """The customer search had the identical defect. One mechanism
        covers both rather than one fix and one survivor."""
        form = read_form()
        block = form[form.index("var CO_AUTOCOMPLETES"):][:400]
        self.assertIn("co-product-search", block)
        self.assertIn("co-customer-search", block)

    def test_an_emptied_field_closes_its_list(self):
        form = read_form()
        self.assertIn("if (!(input.value || '').trim()) coCloseResults", form)

    def test_a_pointer_outside_closes_it(self):
        """Blur alone would race the click that picks a row — blur lands
        first and the row is gone before its click."""
        form = read_form()
        self.assertIn("addEventListener('pointerdown'", form)
        self.assertIn("results.contains(ev.target)", form)

    def test_it_does_not_swallow_mousedown_inside_the_list(self):
        """The usual dodge for that race. Not available here: the list
        scrolls, and swallowing mousedown takes its scrollbar with it."""
        form = read_form()
        wiring = form[form.index("function coWireAutocompletes"):
                      form.index("// ── Delivery address disclosure")]
        self.assertNotIn("mousedown", wiring)
        # ...and the list really does scroll, which is what makes that true.
        self.assertIn("max-height:260px;overflow-y:auto", form)

    def test_escape_closes_it(self):
        self.assertIn("ev.key === 'Escape'", read_form())

    def test_the_create_customer_panel_is_left_alone(self):
        """It is a sibling of the results, not part of them: closing the
        list must not close a form somebody opened from it."""
        form = read_form()
        wiring = form[form.index("function coWireAutocompletes"):
                      form.index("// ── Delivery address disclosure")]
        self.assertNotIn("co-new-customer-panel", wiring)
