"""Saving the edit side panel keeps what the panel does not show.

The panels post only some of a record's fields. Every save there used
to wipe the rest: a contact lost its company (so its company's accounts
dropped off its page), country, group and background info, a company
its group.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crm.models import ClientGroup, Company, Contact
from crm.tests.test_create_opens_no_account import _FormData

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class TheEditPanelKeepsWhatItDoesNotShow(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(username="admin_ek", password="pw")
        self.client.force_login(user)
        self.group = ClientGroup.objects.create(name="Wholesale")
        self.company = Company.objects.create(
            name="Hazal Home", country="Poland", group=self.group,
            backgroundInfo="Curtain shop")
        self.contact = Contact.objects.create(
            name="Hanefi Polonya", company=self.company, country="Poland",
            group=self.group, backgroundInfo="Owner", address="Warsaw",
            email=["h@example.com"], phone=["+48 1"])

    def _panel(self, url, form_id):
        # What the browser posts: the panel's own fields, read off it.
        parser = _FormData(form_id)
        parser.feed(self.client.get(url, **AJAX).content.decode())
        self.assertTrue(parser.data, f"#{form_id} not found in the panel")
        return parser.data

    def test_renaming_a_contact_keeps_its_company_country_group_and_info(self):
        url = reverse("crm:update_contact", args=[self.contact.pk])
        data = self._panel(url, "editContactForm")
        self.assertNotIn("company", data)  # the premise: the panel never sends it
        data.update(name="Hanifi Polonya", address="Warsaw",
                    emails_data='["h@example.com"]', phones_data='["+48 1"]')
        resp = self.client.post(url, data, **AJAX)
        self.assertTrue(resp.json()["success"], resp.content)

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.name, "Hanifi Polonya")
        self.assertEqual(self.contact.company, self.company)
        self.assertEqual(self.contact.country, "Poland")
        self.assertEqual(self.contact.group, self.group)
        self.assertEqual(self.contact.backgroundInfo, "Owner")

    def test_a_field_the_panel_sends_empty_is_still_cleared(self):
        url = reverse("crm:update_contact", args=[self.contact.pk])
        data = self._panel(url, "editContactForm")
        data.update(address="", emails_data="[]", phones_data='["+48 1"]')
        self.client.post(url, data, **AJAX)

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.address, "")
        self.assertEqual(self.contact.email, [])
        self.assertEqual(self.contact.company, self.company)

    def test_editing_a_company_keeps_its_group(self):
        url = reverse("crm:update_company", args=[self.company.pk])
        data = self._panel(url, "editCompanyForm")
        self.assertNotIn("group", data)
        data.update(name="Hazal Home Ltd", backgroundInfo="Curtain shop", address="")
        resp = self.client.post(url, data, **AJAX)
        self.assertTrue(resp.json()["success"], resp.content)

        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Hazal Home Ltd")
        self.assertEqual(self.company.group, self.group)
        self.assertEqual(self.company.country, "Poland")
