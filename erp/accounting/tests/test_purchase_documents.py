"""A purchase's documents: the supplier's invoice, delivery notes, photos.

They are files on the purchase (the shared erp.Attachment), kept in the
storage zone like a contact's, and reached only through the purchase's
own pages, so they open for exactly the people the purchase opens for.

Run with:
    scripts/test_local.sh accounting.tests.test_purchase_documents
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from authentication.models import Permission
from crm.models import Company
from erp.models import Attachment
from operating.models import Warehouse


@override_settings(USE_BUNNY_CDN=True)
@patch("marketing.utils.bunny_storage.delete_from_bunny")
@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.invalid/x")
class PurchaseDocumentsTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene")
        self.other_book = Book.objects.create(name="Laleli")
        self.hakan = Company.objects.create(name="Hakan Atölye")
        account = CurrentAccount.objects.create(
            book=self.book, code="C-HKN", name="Hakan Atölye", type="supplier",
            default_currency=usd, company=self.hakan)
        self.purchase = Invoice.objects.create(
            book=self.book, current_account=account, currency=usd, type="purchase",
            number="PUR-2026-000200", date=date(2026, 11, 20), due_date=date(2026, 12, 20))
        self.user = get_user_model().objects.create_user("mustafa", password="pw")
        self.user.member.books.add(self.book)
        self.client.force_login(self.user)

    def _url(self, name, *extra, purchase=None):
        return reverse(f"accounts:{name}", args=[(purchase or self.purchase).pk, *extra])

    def _upload(self, *files, purchase=None):
        return self.client.post(self._url("purchase_documents", purchase=purchase),
                                {"files": list(files)})

    @staticmethod
    def _pdf(name="hakan-invoice.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4 ...", "application/pdf")

    def test_a_file_goes_onto_the_purchase_and_into_its_folder(self, upload, _delete):
        r = self._upload(self._pdf(), SimpleUploadedFile("delivery.txt", b"20 rolls", "text/plain"))
        self.assertTrue(r.json()["success"], r.json())
        self.assertIn("hakan-invoice.pdf", r.json()["html"])
        docs = self.purchase.attachments
        self.assertEqual(docs.count(), 2)
        doc = docs.get(name="hakan-invoice.pdf")
        self.assertEqual(doc.record, self.purchase)
        self.assertEqual(doc.uploaded_by, self.user)
        self.assertTrue(doc.path.startswith(f"Accounting/purchases/{self.purchase.pk}/"), doc.path)

    def test_a_heavy_scanned_pdf_is_stored_lighter_under_its_name(self, upload, _delete):
        from erp.tests.test_pdf_optimizer import _scan
        scan = _scan(size=(1500, 2000), pages=1)
        self.assertTrue(self._upload(scan).json()["success"])
        doc = self.purchase.attachments.get()
        self.assertEqual((doc.name, doc.content_type), ("hakan-invoice.pdf", "application/pdf"))
        self.assertLess(doc.size, scan.size // 2)

    def test_a_program_is_refused_by_name_and_the_rest_kept(self, upload, _delete):
        r = self._upload(self._pdf(), SimpleUploadedFile("setup.exe", b"MZ", "application/octet-stream"))
        self.assertFalse(r.json()["success"])
        self.assertIn("setup.exe", " ".join(r.json()["errors"]))
        self.assertEqual(list(self.purchase.attachments
                              .values_list("name", flat=True)), ["hakan-invoice.pdf"])

    def test_the_purchase_page_lists_them_and_opens_each(self, upload, _delete):
        self._upload(self._pdf())
        doc = self.purchase.attachments.get()
        page = self.client.get(self._url("purchase_order_detail"))
        self.assertContains(page, "hakan-invoice.pdf")
        self.assertContains(page, self._url("purchase_documents_file", doc.pk))
        with patch("marketing.utils.bunny_storage.download_from_bunny",
                   return_value=SimpleNamespace(iter_content=lambda chunk_size: [b"%PDF-1.4 ..."])):
            r = self.client.get(self._url("purchase_documents_file", doc.pk))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 ...")
        self.assertIn("inline", r["Content-Disposition"])

    def test_a_photo_shows_a_thumbnail(self, upload, _delete):
        """A photo shows itself in the list; a PDF keeps its icon."""
        from erp.tests.test_image_optimizer import _image_file
        self._upload(self._pdf(), _image_file("goods.jpg", "JPEG", size=(400, 300),
                                              content_type="image/jpeg"))
        docs = {d.name: d for d in self.purchase.attachments.all()}
        page = self.client.get(self._url("purchase_order_detail")).content.decode()
        photo_url = self._url("purchase_documents_file", docs["goods.jpg"].pk)
        pdf_url = self._url("purchase_documents_file", docs["hakan-invoice.pdf"].pk)
        self.assertIn(f'<img src="{photo_url}"', page)
        self.assertNotIn(f'<img src="{pdf_url}"', page)

    def test_the_form_shows_a_saved_purchases_documents(self, upload, _delete):
        wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        Invoice.objects.filter(pk=self.purchase.pk).update(status="ordered", intake_warehouse=wh)
        self._upload(self._pdf())
        form = self.client.get(reverse("accounts:goods_receipt_edit", args=[self.purchase.pk]))
        self.assertContains(form, "hakan-invoice.pdf")
        self.assertContains(form, self._url("purchase_documents"))
        # A new purchase's box keeps its files until the first save.
        new = self.client.get(reverse("accounts:goods_receipt", args=[self.book.pk]))
        self.assertContains(new, "They are uploaded when the purchase is saved.")

    def test_deleting_one_takes_its_file_too(self, upload, delete):
        self._upload(self._pdf())
        doc = self.purchase.attachments.get()
        self.assertEqual(self.client.get(self._url("purchase_documents_delete", doc.pk)).status_code, 405)
        r = self.client.post(self._url("purchase_documents_delete", doc.pk))
        self.assertTrue(r.json()["success"])
        self.assertFalse(Attachment.objects.filter(pk=doc.pk).exists())
        delete.assert_called_once_with(doc.path)

    def test_another_books_purchase_keeps_its_papers_to_itself(self, upload, _delete):
        theirs = Invoice.objects.create(
            book=self.other_book, current_account=CurrentAccount.objects.create(
                book=self.other_book, code="C-X", name="Elsewhere", type="supplier",
                default_currency=self.purchase.currency),
            currency=self.purchase.currency, type="purchase", number="PUR-L-1",
            date=date(2026, 11, 20), due_date=date(2026, 12, 20))
        doc = Attachment.objects.create(record=theirs, name="theirs.pdf", path="Accounting/purchases/x.pdf",
                                           content_type="application/pdf")
        self.assertEqual(self._upload(self._pdf(), purchase=theirs).status_code, 404)
        self.assertEqual(self.client.get(self._url("purchase_documents_file", doc.pk, purchase=theirs)).status_code, 404)
        self.assertEqual(self.client.post(self._url("purchase_documents_delete", doc.pk, purchase=theirs)).status_code, 404)
        # Nor through a purchase of one's own book naming it.
        self.assertEqual(self.client.get(self._url("purchase_documents_file", doc.pk)).status_code, 404)
        self.assertTrue(Attachment.objects.filter(pk=doc.pk).exists())

    def test_a_role_without_the_ledger_still_handles_them(self, upload, _delete):
        """Purchasing is warehouse work: Operations opens purchases without
        the ledger or the CRM, and their documents with them."""
        self.user.member.permissions.add(Permission.objects.get_or_create(name="no_accounts")[0])
        self.assertTrue(self._upload(self._pdf()).json()["success"])
        doc = self.purchase.attachments.get()
        self.assertEqual(self.client.post(self._url("purchase_documents_delete", doc.pk)).status_code, 200)
        # The CRM's own file routes stay theirs: closed to this role.
        self.assertNotEqual(self.client.get(reverse("crm:download_attachment", args=[doc.pk])).status_code, 200)

    def test_the_suppliers_purchase_history_says_how_many(self, upload, _delete):
        self.user.is_superuser = True
        self.user.save()
        self._upload(self._pdf(), self._pdf("delivery-photo.pdf"))
        page = self.client.get(reverse("crm:company_detail", args=[self.hakan.pk]))
        self.assertContains(page, "2 documents")
        self.assertNotContains(page, "hakan-invoice.pdf")
