"""The company sidebar attaches every contact picked, not just the last."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.models import Member
from crm.models import Company, Contact
from crm.tests.test_create_opens_no_account import _FormData


class TheCompanyTakesSeveralContacts(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Ergene Fabric")
        user = get_user_model().objects.create_user(username="staff_cc", password="pw")
        member = Member.objects.get(user=user)
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.client.force_login(user)
        self.a = Contact.objects.create(name="Abbie Braker")
        self.b = Contact.objects.create(name="Dilek Braker")
        self.other = Contact.objects.create(name="Nobody Else")

    def _create(self, **fields):
        # The sidebar's own defaults, read off the page, plus what the
        # test is about — the way a browser would post it.
        parser = _FormData("companyForm")
        parser.feed(self.client.get(reverse("crm:company_list")).content.decode())
        data = dict(parser.data, name="Braker Tekstil")
        data.update(fields)
        resp = self.client.post(reverse("crm:create_company"), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["success"], resp.content)
        return Company.objects.get(name="Braker Tekstil")

    def test_every_picked_contact_is_attached(self):
        company = self._create(contact_ids=f"{self.a.pk},{self.b.pk}")
        self.assertEqual(set(company.contacts.values_list("name", flat=True)),
                         {"Abbie Braker", "Dilek Braker"})
        self.other.refresh_from_db()
        self.assertIsNone(self.other.company)

    def test_a_stale_tab_posting_one_contact_still_works(self):
        company = self._create(contact_id=self.a.pk)
        self.assertEqual(list(company.contacts.all()), [self.a])

    def test_rubbish_in_the_list_is_ignored(self):
        company = self._create(contact_ids=f"{self.a.pk},abc,,999999")
        self.assertEqual(list(company.contacts.all()), [self.a])

    def test_contacts_typed_in_are_made_with_the_company(self):
        import json
        company = self._create(
            contact_ids=str(self.a.pk),
            new_contacts_json=json.dumps([
                {"name": "Yeni Kişi", "email": "y@k.com", "phone": "+90 555"},
                {"name": "   ", "email": "ignored@x.com"},
            ]))
        names = set(company.contacts.values_list("name", flat=True))
        self.assertEqual(names, {"Abbie Braker", "Yeni Kişi"})
        made = Contact.objects.get(name="Yeni Kişi")
        self.assertEqual((made.email, made.phone), (["y@k.com"], ["+90 555"]))
        self.assertFalse(Contact.objects.filter(email__contains=["ignored@x.com"]).exists())


class TheNameIsOneCompanys(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Ergene Fabric")
        user = get_user_model().objects.create_user(username="staff_dup", password="pw")
        member = Member.objects.get(user=user)
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.client.force_login(user)
        Company.objects.create(name="Woodline Saliveros")

    def _post(self, name):
        parser = _FormData("companyForm")
        parser.feed(self.client.get(reverse("crm:company_list")).content.decode())
        data = dict(parser.data, name=name)
        return self.client.post(reverse("crm:create_company"), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_the_same_name_is_refused_with_a_reason(self):
        resp = self._post("Woodline Saliveros")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already exists", resp.json()["errors"]["name"][0]["message"])
        self.assertEqual(Company.objects.count(), 1)

    def test_a_different_case_is_the_same_name(self):
        resp = self._post("WOODLINE SALIVEROS")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("name", resp.json()["errors"])
        self.assertEqual(Company.objects.count(), 1)
