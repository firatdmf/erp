"""Files hung off a CRM record.

A salesperson's paperwork — the signed contract, the spec sheet the
customer sent back — lives in their inbox until there is somewhere on
the contact to put it. These endpoints are that somewhere, and they are
shared by contacts, companies and suppliers: the record kind travels in
the URL.

The bytes go to Bunny or nowhere: MEDIA_ROOT is a container path with
no volume mounted, so a file written there looks saved and is gone on
the next deploy. A failed upload is therefore an error the user can
retry, never a local copy — and in production a server without Bunny
configured refuses the upload instead of writing to a doomed disk.

Nobody reads a file by its CDN address either: rows keep the storage
path, and the download view hands the bytes to signed-in users only.

Run:
    python manage.py test crm.test_attachments
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Attachment, Company, Contact

User = get_user_model()


class AttachmentUpload(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dilek", password="x")
        self.client.force_login(self.user)
        self.contact = Contact.objects.create(name="Abbie Braker")

    def _upload(self, *files, kind="contact", pk=None):
        return self.client.post(
            reverse("crm:upload_attachments", args=[kind, pk or self.contact.pk]),
            {"files": list(files)},
        )

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_upload_goes_to_the_cdn_under_its_record(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x.pdf"
        f = SimpleUploadedFile("contract.pdf", b"%PDF-1.4 ...", "application/pdf")

        res = self._upload(f)

        self.assertEqual(res.status_code, 200)
        row = Attachment.objects.get()
        self.assertEqual(row.contact, self.contact)
        self.assertEqual(row.name, "contract.pdf")
        self.assertTrue(
            row.path.startswith(f"Marketing/crm/contact/{self.contact.pk}/"))
        self.assertFalse(row.file)
        self.assertEqual(row.uploaded_by, self.user)
        # Marketing/crm/<kind>/<id>/ — one folder per record.
        path = mock_upload.call_args[0][1]
        self.assertTrue(
            path.startswith(f"Marketing/crm/contact/{self.contact.pk}/"), path)
        self.assertTrue(path.endswith("contract.pdf"), path)

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_two_files_of_one_name_do_not_collide(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x.pdf"
        self._upload(SimpleUploadedFile("contract.pdf", b"one", "application/pdf"))
        self._upload(SimpleUploadedFile("contract.pdf", b"two", "application/pdf"))

        first, second = [c[0][1] for c in mock_upload.call_args_list]
        self.assertNotEqual(first, second)
        self.assertEqual(Attachment.objects.count(), 2)

    @override_settings(USE_BUNNY_CDN=True, DEBUG=False)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_a_failed_cdn_upload_saves_nothing_and_says_so(self, mock_upload):
        mock_upload.side_effect = RuntimeError("bunny is down")

        res = self._upload(SimpleUploadedFile("spec.txt", b"hello", "text/plain"))

        # No half-saved row pointing at a disk that gets wiped on deploy.
        self.assertFalse(Attachment.objects.exists())
        self.assertIn("spec.txt", res["HX-Trigger"])

    @override_settings(USE_BUNNY_CDN=False, DEBUG=False)
    def test_production_without_bunny_refuses_rather_than_writing_locally(self):
        res = self._upload(SimpleUploadedFile("spec.txt", b"hello", "text/plain"))

        self.assertFalse(Attachment.objects.exists())
        self.assertIn("not configured", res["HX-Trigger"])

    @override_settings(USE_BUNNY_CDN=False, DEBUG=True)
    def test_a_dev_box_without_bunny_still_stores_locally(self):
        self._upload(SimpleUploadedFile("spec.txt", b"hello", "text/plain"))

        row = Attachment.objects.get()
        self.assertEqual(row.path, "")
        self.assertTrue(row.file)
        row.delete()   # keep the dev media directory clean

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_an_oversized_file_is_skipped_not_the_whole_batch(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x"
        big = SimpleUploadedFile("huge.bin", b"x" * (26 * 1024 * 1024), "application/octet-stream")
        ok = SimpleUploadedFile("small.txt", b"fine", "text/plain")

        res = self._upload(big, ok)

        self.assertEqual([a.name for a in Attachment.objects.all()], ["small.txt"])
        self.assertIn("huge.bin", res["HX-Trigger"])

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_files_hang_off_companies_too(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x"
        company = Company.objects.create(name="O'Keefe-Adams")

        self._upload(
            SimpleUploadedFile("price-list.pdf", b"pdf", "application/pdf"),
            kind="company", pk=company.pk,
        )

        row = Attachment.objects.get()
        self.assertEqual(row.company, company)
        self.assertIsNone(row.contact)
        self.assertTrue(row.path.startswith(f"Marketing/crm/company/{company.pk}/"))

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_a_program_is_refused_and_the_rest_of_the_batch_is_not(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x"

        res = self._upload(
            SimpleUploadedFile("setup.exe", b"MZ", "application/octet-stream"),
            SimpleUploadedFile("quote.pdf", b"%PDF", "application/pdf"),
        )

        self.assertEqual([a.name for a in Attachment.objects.all()], ["quote.pdf"])
        self.assertIn("setup.exe", res["HX-Trigger"])

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_an_executable_wearing_a_document_name_is_refused(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x"

        self._upload(SimpleUploadedFile("invoice.pdf.exe", b"MZ", "application/pdf"))

        self.assertFalse(Attachment.objects.exists())

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_a_macro_enabled_workbook_is_refused(self, mock_upload):
        mock_upload.return_value = "https://cdn.example/x"

        self._upload(SimpleUploadedFile("prices.xlsm", b"PK", "application/vnd.ms-excel"))

        self.assertFalse(Attachment.objects.exists())

    @override_settings(USE_BUNNY_CDN=True)
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_the_stored_type_comes_from_the_name_not_the_client(self, mock_upload):
        """A crafted client cannot pick how its file is served later."""
        mock_upload.return_value = "https://cdn.example/x"

        self._upload(SimpleUploadedFile("quote.pdf", b"%PDF", "image/svg+xml"))

        self.assertEqual(Attachment.objects.get().content_type, "application/pdf")

    def test_an_unknown_record_kind_is_a_404(self):
        res = self.client.post(reverse("crm:upload_attachments", args=["order", 1]), {})
        self.assertEqual(res.status_code, 404)


class AttachmentDelete(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dilek", password="x")
        self.client.force_login(self.user)
        self.contact = Contact.objects.create(name="Abbie Braker")

    @patch("marketing.utils.bunny_storage.delete_from_bunny")
    def test_delete_removes_the_row_and_the_stored_file(self, mock_delete):
        row = Attachment.objects.create(
            contact=self.contact, name="contract.pdf",
            path="Marketing/crm/contact/1/abc_contract.pdf",
        )

        res = self.client.post(reverse("crm:delete_attachment", args=[row.pk]))

        self.assertEqual(res.status_code, 200)
        self.assertFalse(Attachment.objects.exists())
        mock_delete.assert_called_once_with(row.path)

    @patch("marketing.utils.bunny_storage.delete_from_bunny")
    def test_deleting_the_contact_takes_its_files_off_the_cdn(self, mock_delete):
        """The route most attachments actually die by."""
        Attachment.objects.create(
            contact=self.contact, name="a.pdf", path="Marketing/crm/contact/1/a.pdf")
        Attachment.objects.create(
            contact=self.contact, name="b.pdf", path="Marketing/crm/contact/1/b.pdf")

        self.contact.delete()

        self.assertFalse(Attachment.objects.exists())
        self.assertEqual(
            sorted(c[0][0] for c in mock_delete.call_args_list),
            ["Marketing/crm/contact/1/a.pdf", "Marketing/crm/contact/1/b.pdf"])

    @patch("marketing.utils.bunny_storage.delete_from_bunny")
    def test_a_cdn_that_will_not_delete_still_drops_the_row(self, mock_delete):
        mock_delete.side_effect = RuntimeError("bunny is down")
        row = Attachment.objects.create(
            contact=self.contact, name="x.pdf", path="Marketing/crm/contact/1/x.pdf")

        self.client.post(reverse("crm:delete_attachment", args=[row.pk]))

        self.assertFalse(Attachment.objects.exists())


class AttachmentsOnThePage(TestCase):
    """The contact page lists what is attached, and says how many."""

    def setUp(self):
        self.user = User.objects.create_user("dilek", password="x")
        self.client.force_login(self.user)
        self.contact = Contact.objects.create(name="Abbie Braker")

    def test_the_files_group_lists_them_without_leaking_the_cdn_address(self):
        row = Attachment.objects.create(
            contact=self.contact, name="contract.pdf",
            path="Marketing/crm/contact/1/abc_contract.pdf", size=2048,
            content_type="application/pdf",
        )

        html = self.client.get(
            reverse("crm:contact_detail", args=[self.contact.pk])).content.decode()

        self.assertIn("contract.pdf", html)
        self.assertIn(reverse("crm:download_attachment", args=[row.pk]), html)
        self.assertNotIn("Marketing/crm/contact/1/abc_contract.pdf", html)
        self.assertIn('id="grpFileCount">(1)', html)

    def test_the_partial_is_just_the_rows(self):
        Attachment.objects.create(
            contact=self.contact, name="spec.xlsx",
            path="Marketing/crm/contact/1/spec.xlsx")

        html = self.client.get(
            reverse("crm:attachments_partial", args=["contact", self.contact.pk])
        ).content.decode()

        self.assertIn("spec.xlsx", html)
        self.assertNotIn("<html", html)


class AttachmentDownload(TestCase):
    """Files are read through the app, so a session is required."""

    def setUp(self):
        self.user = User.objects.create_user("dilek", password="x")
        self.contact = Contact.objects.create(name="Abbie Braker")
        self.row = Attachment.objects.create(
            contact=self.contact, name="contract.pdf",
            path="Marketing/crm/contact/1/abc_contract.pdf",
            size=11, content_type="application/pdf",
        )

    def test_a_stranger_gets_the_login_screen_not_the_document(self):
        res = self.client.get(reverse("crm:download_attachment", args=[self.row.pk]))

        self.assertEqual(res.status_code, 302)
        self.assertIn("/authentication/signin", res["Location"])

    @patch("marketing.utils.bunny_storage.download_from_bunny")
    def test_a_signed_in_user_gets_the_bytes(self, mock_download):
        mock_download.return_value.iter_content.return_value = iter([b"hello world"])
        self.client.force_login(self.user)

        res = self.client.get(reverse("crm:download_attachment", args=[self.row.pk]))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(b"".join(res.streaming_content), b"hello world")
        self.assertEqual(res["Content-Type"], "application/pdf")
        # A PDF opens in the tab; the browser is told not to cache it.
        self.assertIn("inline", res["Content-Disposition"])
        self.assertIn("no-store", res["Cache-Control"])
        mock_download.assert_called_once_with(self.row.path)

    @patch("marketing.utils.bunny_storage.download_from_bunny")
    def test_a_spreadsheet_downloads_rather_than_rendering(self, mock_download):
        mock_download.return_value.iter_content.return_value = iter([b"x"])
        self.row.content_type = "application/vnd.ms-excel"
        self.row.name = "prices.xlsx"
        self.row.save()
        self.client.force_login(self.user)

        res = self.client.get(reverse("crm:download_attachment", args=[self.row.pk]))

        self.assertIn('attachment; filename="prices.xlsx"', res["Content-Disposition"])

    @patch("marketing.utils.bunny_storage.download_from_bunny")
    def test_an_svg_is_handed_over_not_rendered(self, mock_download):
        """Rendering one would run its script on our own origin."""
        mock_download.return_value.iter_content.return_value = iter([b"<svg/>"])
        self.row.content_type = "image/svg+xml"
        self.row.name = "logo.svg"
        self.row.save()
        self.client.force_login(self.user)

        res = self.client.get(reverse("crm:download_attachment", args=[self.row.pk]))

        self.assertIn("attachment", res["Content-Disposition"])
        self.assertEqual(res["X-Content-Type-Options"], "nosniff")

    @patch("marketing.utils.bunny_storage.download_from_bunny")
    def test_a_file_missing_from_storage_is_a_404(self, mock_download):
        mock_download.side_effect = RuntimeError("gone")
        self.client.force_login(self.user)

        res = self.client.get(reverse("crm:download_attachment", args=[self.row.pk]))

        self.assertEqual(res.status_code, 404)
