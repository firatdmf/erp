"""The company's own identity, edited on the Settings page.

One row is the only place documents read it from: what is typed there
prints, what is left blank prints blank. Only an admin may change it, and
an edit reaches every document at once.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.models import Permission
from erp.branding import brand, brand_flag, clear_cache
from erp.models import BrandProfile


class BrandValues(TestCase):
    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_the_row_was_seeded_with_what_the_settings_used_to_say(self):
        """erp 0006 ran when this database was built: the documents kept
        their address on the day it stopped being a setting."""
        self.assertTrue(BrandProfile.objects.get().address)
        self.assertEqual(brand("BRAND_ADDRESS"), BrandProfile.objects.get().address)

    def test_with_no_row_nothing_is_answered(self):
        BrandProfile.objects.all().delete()
        self.assertEqual(brand("BRAND_ADDRESS"), "")
        self.assertFalse(hasattr(settings, "BRAND_ADDRESS"))

    def test_what_is_typed_prints_and_a_blank_field_prints_blank(self):
        BrandProfile.objects.create(address="Yeni adres 5", phone="")
        self.assertEqual(brand("BRAND_ADDRESS"), "Yeni adres 5")
        self.assertEqual(brand("BRAND_PHONE"), "")

    def test_the_short_name_and_code_prefix_are_on_the_row_too(self):
        BrandProfile.objects.create(short_name="Acme", code_prefix="ACM")
        self.assertEqual(brand("BRAND_NAME"), "Acme")
        self.assertEqual(brand("BRAND_CODE_PREFIX"), "ACM")
        self.assertFalse(hasattr(settings, "BRAND_NAME"))

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
        BrandProfile.objects.create(display_name="", short_name="Acme")
        self.assertEqual(book.effective_brand_name, "Acme")
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
        self.assertFalse(BrandProfile.objects.filter(display_name="Hijacked").exists())

    def test_a_member_who_manages_a_book_is_refused_too(self):
        # 'admin' on a Member is for the books they are assigned; the
        # company profile belongs to every business on the install
        # (erp.ownership.is_install_admin).
        perm, _ = Permission.objects.get_or_create(name="admin")
        self.staff.member.permissions.add(perm)
        resp = self.post(self.staff, display_name="Acme Textiles")
        self.assertContains(resp, "Only an administrator")
        self.assertFalse(BrandProfile.objects.filter(display_name="Acme Textiles").exists())

    def test_a_bad_email_is_refused_with_its_reason(self):
        resp = self.post(self.admin, email="not-an-address")
        self.assertContains(resp, "email")
        self.assertFalse(BrandProfile.objects.filter(email="not-an-address").exists())

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_the_page_shows_the_fields_and_what_they_hold(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        BrandProfile.objects.create(display_name="Acme Textiles")
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("user_settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Company Profile")
        self.assertContains(resp, 'name="display_name"')
        self.assertContains(resp, 'name="nejum_credit"')
        self.assertContains(resp, 'value="Acme Textiles"')

    def test_a_non_admin_sees_it_read_only(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("user_settings"))
        self.assertContains(resp, "Only an administrator can change these")
        self.assertContains(resp, "disabled")
        self.assertNotContains(resp, "Save Company Profile")
