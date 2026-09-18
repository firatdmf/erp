"""The company's own identity, edited on the Settings page.

One row overrides the code defaults in settings.BRAND_DEFAULTS, field by
field: what is typed wins, what is left blank falls through. Only an
admin may change it, and an edit reaches every document at once.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book
from authentication.models import Permission
from erp.branding import brand, brand_flag, clear_cache
from erp.models import BrandProfile


@override_settings(BRAND_DISPLAY_NAME="DEMFIRAT® | Karven Home Collection",
                   BRAND_ADDRESS="Ergene, Tekirdağ", BRAND_PHONE="+90 501",
                   BRAND_TAX_NUMBER="", NEJUM_CREDIT=True)
class BrandValues(TestCase):
    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_with_no_row_the_code_default_stands(self):
        self.assertEqual(brand("BRAND_ADDRESS"), "Ergene, Tekirdağ")
        self.assertTrue(brand_flag("NEJUM_CREDIT"))

    def test_an_edited_field_wins_and_a_blank_one_does_not(self):
        BrandProfile.objects.create(address="Yeni adres 5", phone="")
        self.assertEqual(brand("BRAND_ADDRESS"), "Yeni adres 5")
        self.assertEqual(brand("BRAND_PHONE"), "+90 501")

    def test_the_flag_can_be_turned_off(self):
        BrandProfile.objects.create(nejum_credit=False)
        self.assertFalse(brand_flag("NEJUM_CREDIT"))

    def test_saving_refreshes_what_documents_read(self):
        row = BrandProfile.objects.create(address="First")
        self.assertEqual(brand("BRAND_ADDRESS"), "First")
        row.address = "Second"
        row.save()
        self.assertEqual(brand("BRAND_ADDRESS"), "Second")

    def test_there_is_only_ever_one_row(self):
        BrandProfile.objects.create(address="First")
        BrandProfile.objects.create(address="Second")
        self.assertEqual(BrandProfile.objects.count(), 1)
        self.assertEqual(brand("BRAND_ADDRESS"), "Second")

    def test_the_documents_follow_it(self):
        """The name a book signs with, and the invoice issuer block."""
        book = Book.objects.create(name="Laleli Fabric")   # no brand_name of its own
        from accounting.services_accounts import brand_name_for
        self.assertEqual(book.effective_brand_name,
                         "DEMFIRAT® | Karven Home Collection")
        BrandProfile.objects.create(display_name="Acme Textiles")
        book.refresh_from_db()
        self.assertEqual(book.effective_brand_name, "Acme Textiles")
        self.assertEqual(brand_name_for(book), "Acme Textiles")


class TheCompanyTab(TestCase):
    def setUp(self):
        clear_cache()
        self.admin = User.objects.create_superuser("brand_boss", "b@t.com", "pw")
        self.staff = User.objects.create_user("brand_staff", password="pw")
        self.url = reverse("brand_profile_update")

    def tearDown(self):
        clear_cache()

    def post(self, user, **fields):
        self.client.force_login(user)
        data = {"display_name": "", "legal_suffix": "", "address": "", "phone": "",
                "fax": "", "email": "", "tax_office": "", "tax_number": "",
                "logo_url": ""}
        data.update(fields)
        return self.client.post(self.url, data)

    def test_an_admin_saves_it(self):
        resp = self.post(self.admin, display_name="Acme Textiles",
                         address="Yeni adres 5", nejum_credit="on")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Company profile updated.")
        row = BrandProfile.objects.get()
        self.assertEqual(row.display_name, "Acme Textiles")
        self.assertEqual(row.updated_by, self.admin)
        self.assertTrue(row.nejum_credit)
        self.assertEqual(brand("BRAND_DISPLAY_NAME"), "Acme Textiles")

    def test_the_credit_line_is_turned_off_by_unticking_it(self):
        self.post(self.admin, nejum_credit="on")
        self.assertTrue(brand_flag("NEJUM_CREDIT"))
        self.post(self.admin)          # checkbox absent = unticked
        self.assertFalse(brand_flag("NEJUM_CREDIT"))

    def test_a_member_without_admin_rights_is_refused(self):
        resp = self.post(self.staff, display_name="Hijacked")
        self.assertContains(resp, "Only an administrator")
        self.assertFalse(BrandProfile.objects.exists())

    def test_a_member_with_the_admin_permission_may(self):
        perm, _ = Permission.objects.get_or_create(name="admin")
        self.staff.member.permissions.add(perm)
        self.post(self.staff, display_name="Acme Textiles")
        self.assertEqual(BrandProfile.objects.get().display_name, "Acme Textiles")

    def test_a_bad_email_is_refused_with_its_reason(self):
        resp = self.post(self.admin, email="not-an-address")
        self.assertContains(resp, "email")
        self.assertFalse(BrandProfile.objects.filter(email="not-an-address").exists())

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_the_page_shows_the_fields_and_the_defaults(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("user_settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Company Profile")
        self.assertContains(resp, 'name="display_name"')
        self.assertContains(resp, 'name="nejum_credit"')
        # Nothing edited yet, so the code default shows as the placeholder.
        self.assertContains(resp, 'placeholder="DEMFIRAT')

    def test_a_non_admin_sees_it_read_only(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("user_settings"))
        self.assertContains(resp, "Only an administrator can change these")
        self.assertContains(resp, "disabled")
        self.assertNotContains(resp, "Save Company Profile")
