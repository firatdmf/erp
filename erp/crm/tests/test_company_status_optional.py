"""A company's status is where it stands as a sales lead, and only that.

Every company used to be born a "Prospect", so 221 of 226 on prod read as
leads: suppliers, our own books, the headquarters. Status may now be
blank, meaning not a lead, and that is what a new company gets unless
someone picks Prospect. What a company is to us shows from its accounts'
types instead, beside the status on the list and on its page.

Run:
    python manage.py test crm.tests.test_company_status_optional
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Member
from crm.models import Company
from crm.tests.test_create_opens_no_account import _FormData


class CompanyStatusOptional(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.user = get_user_model().objects.create_user(username="staff", password="pw")
        member = Member.objects.get(user=self.user)
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

    def _sidebar_data(self):
        page = self.client.get(reverse("crm:company_list"))
        parser = _FormData("companyForm")
        parser.feed(page.content.decode())
        return parser.data

    def _create(self, data):
        resp = self.client.post(reverse("crm:create_company"), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_a_new_company_is_not_a_lead_by_default(self):
        self.assertEqual(Company.objects.create(name="Plain Ltd").status, "")
        data = self._sidebar_data()
        data["name"] = "Sidebar Ltd"
        self._create(data)
        self.assertEqual(Company.objects.get(name="Sidebar Ltd").status, "")

    def test_prospect_can_still_be_picked(self):
        data = self._sidebar_data()
        data.update(name="Lead Ltd", status="prospect")
        self._create(data)
        self.assertEqual(Company.objects.get(name="Lead Ltd").status, "prospect")

    def test_the_follow_up_option_starts_hidden(self):
        page = self.client.get(reverse("crm:company_list"))
        self.assertContains(page, 'id="companyFollowupOption" style="display: none;"')

    def test_account_types_show_on_the_list_and_the_page(self):
        hq = Company.objects.create(name="DEMFIRAT | Plaza HQ")
        CurrentAccount.objects.create(book=self.book, code="00491", name=hq.name,
                                      type="intercompany", company=hq,
                                      default_currency=self.usd)
        listing = self.client.get(reverse("crm:company_list"))
        self.assertContains(listing, 'class="ord-status account-intercompany"')
        self.assertNotContains(listing, 'class="ord-status prospect"')
        page = self.client.get(reverse("crm:company_detail", args=[hq.pk]))
        self.assertContains(page, 'class="ord-status account-intercompany"')

    def test_the_edit_form_names_the_blank_choice(self):
        hq = Company.objects.create(name="Edit Me Ltd", created_by=self.user)
        html = self.client.get(reverse("crm:update_company", args=[hq.pk]),
                               HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()
        start = html.index('id="id_edit_company_status"')
        select = html[start:html.index("</select>", start)]
        self.assertIn('<option value="" selected>Not a lead</option>', select)
        self.assertNotIn("---------", select)
