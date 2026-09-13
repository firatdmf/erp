"""Adding a client to the CRM does not open a current account.

It used to, behind an "Open a current account" box ticked by default. That
made an account for every lead and prospect in whichever book the person
typing happened to be working in — before anyone knew which business the
client would buy from, or in which currency. An account is now opened the
first time the client is picked on a document, in that document's book.

These tests submit the sidebars the way their JS does (FormData over the
rendered form) rather than hand-building a POST, so markup that still
offered the choice would show up here.

Run:
    python manage.py test crm.test_create_opens_no_account
"""
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Member
from crm.models import Company, Contact


class _FormData(HTMLParser):
    """What `new FormData(document.getElementById(form_id))` would send:
    named inputs with their values, ticked checkboxes as "on", and each
    select's selected (or first) option."""

    def __init__(self, form_id):
        super().__init__()
        self.form_id = form_id
        self.inside = False
        self.data = {}
        self._select = None
        self._select_has_value = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.inside = attrs.get("id") == self.form_id
            return
        if not self.inside:
            return
        name = attrs.get("name")
        if tag == "input" and name:
            kind = attrs.get("type", "text")
            if kind == "checkbox":
                if "checked" in attrs:
                    self.data[name] = attrs.get("value", "on")
            elif kind not in ("button", "submit", "file"):
                self.data.setdefault(name, attrs.get("value", ""))
        elif tag == "select" and name:
            self._select, self._select_has_value = name, False
        elif tag == "option" and self._select:
            if not self._select_has_value or "selected" in attrs:
                self.data[self._select] = attrs.get("value", "")
                self._select_has_value = True

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False
        elif tag == "select":
            self._select = None


class CrmCreateOpensNoAccount(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric")
        self.user = get_user_model().objects.create_user(
            username="staff", password="pw")
        member = Member.objects.get(user=self.user)
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

    def _form_data(self, form_id):
        page = self.client.get(reverse("crm:company_list"))
        self.assertEqual(page.status_code, 200)
        parser = _FormData(form_id)
        parser.feed(page.content.decode())
        self.assertTrue(parser.data, f"#{form_id} not found on the page")
        return parser.data

    def _submit(self, url_name, data):
        resp = self.client.post(reverse(url_name), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["success"], resp.content)

    def test_add_company_sidebar_opens_none(self):
        data = self._form_data("companyForm")
        data["name"] = "Braker Tekstil"
        self._submit("crm:create_company", data)
        self.assertTrue(Company.objects.filter(name="Braker Tekstil").exists())
        self.assertFalse(CurrentAccount.objects.exists())

    def test_add_contact_sidebar_opens_none(self):
        data = self._form_data("mainContactForm")
        data["name"] = "Abbie Braker"
        self._submit("crm:create_contact", data)
        self.assertTrue(Contact.objects.filter(name="Abbie Braker").exists())
        self.assertFalse(CurrentAccount.objects.exists())

    def test_nested_contact_sidebar_opens_none(self):
        data = self._form_data("contactForm")
        data["name"] = "Dilek Braker"
        self._submit("crm:create_contact", data)
        self.assertTrue(Contact.objects.filter(name="Dilek Braker").exists())
        self.assertFalse(CurrentAccount.objects.exists())

    def test_the_sidebars_no_longer_offer_the_choice(self):
        page = self.client.get(reverse("crm:company_list"))
        self.assertNotContains(page, 'name="create_current_account"')

    def test_a_stale_tab_posting_the_old_box_still_opens_none(self):
        data = self._form_data("companyForm")
        data.update(name="Old Tab Ltd", create_current_account="on")
        self._submit("crm:create_company", data)
        self.assertFalse(CurrentAccount.objects.exists())
