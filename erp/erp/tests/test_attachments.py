"""Files on any record, one way (erp.attachments): a payment's bank slip,
an expense's receipt, an order's customer PO.

Each record's files box uploads into the record's own app folder, lists
the files on the record's page, opens each one, and is walled exactly as
the record is: another book's payment, expense or order keeps its files
to itself. Deleting the record takes its files and their bytes with it.
The CRM's old rows moved onto the shared table with their paths intact.

Run with:
    scripts/test_local.sh erp.tests.test_attachments
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory, EquityExpense, ExpenseCategory, StakeholderBook
from accounting.models_accounts import CurrentAccount, Payment
from erp.models import Attachment
from erp.testing import TransactionTestCase
from operating.models import Order


def _pdf(name="bank-slip.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 slip", "application/pdf")


@override_settings(USE_BUNNY_CDN=True)
@patch("marketing.utils.bunny_storage.delete_from_bunny", return_value=True)
@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn.invalid/x")
class RecordFilesTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.other_book = Book.objects.create(name="Ergene", base_currency=self.usd)
        self.user = get_user_model().objects.create_user("burak", password="pw")
        self.user.member.books.add(self.book)
        self.user.member.default_book = self.book
        self.user.member.save()
        StakeholderBook.objects.create(book=self.book, member=self.user.member, shares=1)
        self.client.force_login(self.user)
        self.records = {kind: self._record(kind, self.book) for kind in ("payment", "expense", "order")}

    def _account(self, book):
        n = CurrentAccount.objects.count() + 1
        return CurrentAccount.objects.create(
            book=book, code=f"C-{n}", name=f"Euroland {n}", type="customer",
            default_currency=self.usd)

    def _record(self, kind, book):
        if kind == "payment":
            return Payment.objects.create(
                current_account=self._account(book), book=book, number=f"COL-{book.pk}",
                type="collection", method="bank_transfer", status="draft",
                date=date(2026, 11, 21), amount=Decimal("100.00"), currency=self.usd)
        if kind == "expense":
            cash = CashAccount.objects.create(book=book, name=f"Kasa {book.pk}", currency=self.usd,
                                              balance=Decimal("1000.00"))
            return EquityExpense.objects.create(
                book=book, category=ExpenseCategory.objects.get_or_create(name="Delivery")[0],
                cash_account=cash, currency=self.usd, amount=Decimal("25.00"),
                date=date(2026, 11, 21), description="Courier")
        return Order.objects.create(order_number=f"DK-{book.pk}", current_account=self._account(book),
                                    status="pending")

    ROUTES = {"payment": "accounts:payment_files", "expense": "accounts:expense_files",
              "order": "operating:order_files"}
    FOLDERS = {"payment": "Accounting/payments", "expense": "Accounting/expenses",
               "order": "Operating/orders"}

    def _page(self, kind, record):
        if kind == "payment":
            return reverse("accounts:payment_detail", args=[record.pk])
        if kind == "expense":
            return reverse("accounting:equity_expense_detail",
                           kwargs={"pk": record.book_id, "expense_pk": record.pk})
        return reverse("operating:order_detail", args=[record.pk])

    def _upload(self, kind, record, *files):
        return self.client.post(reverse(self.ROUTES[kind], args=[record.pk]), {"files": list(files)})

    def test_a_file_goes_onto_the_record_into_its_apps_folder(self, upload, _delete):
        for kind, record in self.records.items():
            with self.subTest(kind):
                r = self._upload(kind, record, _pdf())
                self.assertTrue(r.json()["success"], r.json())
                self.assertIn("bank-slip.pdf", r.json()["html"])
                doc = record.attachments.get()
                self.assertEqual((doc.name, doc.content_type, doc.uploaded_by),
                                 ("bank-slip.pdf", "application/pdf", self.user))
                self.assertTrue(doc.path.startswith(f"{self.FOLDERS[kind]}/{record.pk}/"), doc.path)

    def test_the_records_page_has_the_box_and_opens_each_file(self, upload, _delete):
        for kind, record in self.records.items():
            with self.subTest(kind):
                self._upload(kind, record, _pdf())
                doc = record.attachments.get()
                file_url = reverse(self.ROUTES[kind] + "_file", args=[record.pk, doc.pk])
                page = self.client.get(self._page(kind, record))
                self.assertContains(page, reverse(self.ROUTES[kind], args=[record.pk]))
                self.assertContains(page, file_url)
                with patch("marketing.utils.bunny_storage.download_from_bunny",
                           return_value=SimpleNamespace(iter_content=lambda chunk_size: [b"%PDF-1.4 slip"])):
                    r = self.client.get(file_url)
                self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 slip")
                self.assertIn("inline", r["Content-Disposition"])

    def test_deleting_one_takes_its_bytes(self, upload, delete):
        for kind, record in self.records.items():
            with self.subTest(kind):
                self._upload(kind, record, _pdf())
                doc = record.attachments.get()
                delete_url = reverse(self.ROUTES[kind] + "_delete", args=[record.pk, doc.pk])
                self.assertEqual(self.client.get(delete_url).status_code, 405)
                self.assertTrue(self.client.post(delete_url).json()["success"])
                self.assertFalse(record.attachments.exists())
                delete.assert_called_with(doc.path)

    def test_another_books_record_keeps_its_files_to_itself(self, upload, _delete):
        for kind in self.ROUTES:
            with self.subTest(kind):
                theirs = self._record(kind, self.other_book)
                doc = Attachment.objects.create(record=theirs, name="theirs.pdf", path="x/theirs.pdf",
                                                content_type="application/pdf")
                route = self.ROUTES[kind]
                self.assertEqual(self._upload(kind, theirs, _pdf()).status_code, 404)
                self.assertEqual(self.client.get(reverse(route + "_file", args=[theirs.pk, doc.pk])).status_code, 404)
                self.assertEqual(self.client.post(reverse(route + "_delete", args=[theirs.pk, doc.pk])).status_code, 404)
                # Nor through a record of one's own naming it.
                mine = self.records[kind]
                self.assertEqual(self.client.get(reverse(route + "_file", args=[mine.pk, doc.pk])).status_code, 404)
                self.assertTrue(Attachment.objects.filter(pk=doc.pk).exists())

    def test_deleting_the_record_takes_its_files_and_their_bytes(self, upload, delete):
        payment = self.records["payment"]
        self._upload("payment", payment, _pdf())
        path = payment.attachments.get().path
        payment.delete()
        self.assertFalse(Attachment.objects.exists())
        delete.assert_called_with(path)


BEFORE = [("erp", "0008_attachment"), ("crm", "0030_retire_attachment_related_names")]
AFTER = [("erp", "0009_attachments_from_crm")]


class CrmFilesMoveOntoTheSharedTable(TransactionTestCase):
    """erp 0009: each crm.Attachment row becomes an erp.Attachment on the
    same record, keeping its path, uploader and upload time."""

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(BEFORE)
        apps = executor.loader.project_state(BEFORE).apps
        Old = apps.get_model("crm", "Attachment")
        directory = apps.get_model("crm", "Directory").objects.get_or_create(name="Migration test list")[0]
        contact = apps.get_model("crm", "Contact").objects.create(name="Abbie Braker", directory=directory)
        company = apps.get_model("crm", "Company").objects.create(name="Woodline", directory=directory)
        usd = apps.get_model("accounting", "CurrencyCategory").objects.create(code="USD", name="USD", symbol="$")
        book = apps.get_model("accounting", "Book").objects.create(name="Ergene")
        account = apps.get_model("accounting", "CurrentAccount").objects.create(
            book=book, code="C-1", name="Hakan", type="supplier", default_currency=usd)
        purchase = apps.get_model("accounting", "Invoice").objects.create(
            book=book, current_account=account, currency=usd, type="purchase", number="PUR-1",
            date=date(2026, 11, 20), due_date=date(2026, 12, 20))
        self.ids = {"contact": contact.pk, "company": company.pk, "invoice": purchase.pk}
        for field, pk, name in (("contact", contact.pk, "contract.pdf"),
                                ("company", company.pk, "spec.xlsx"),
                                ("invoice", purchase.pk, "goods.jpg")):
            row = Old.objects.create(**{f"{field}_id": pk}, name=name, path=f"old/{name}",
                                     size=10, content_type="x/y")
            Old.objects.filter(pk=row.pk).update(uploaded_at="2026-11-20T10:00:00Z")

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(AFTER)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_each_row_lands_on_its_record_with_its_path(self):
        apps = MigrationExecutor(connection).loader.project_state(AFTER).apps
        New = apps.get_model("erp", "Attachment")
        rows = {(r.record_type.app_label, r.record_type.model, r.record_id): r
                for r in New.objects.select_related("record_type")}
        self.assertEqual(set(rows), {("crm", "contact", self.ids["contact"]),
                                     ("crm", "company", self.ids["company"]),
                                     ("accounting", "invoice", self.ids["invoice"])})
        contract = rows[("crm", "contact", self.ids["contact"])]
        self.assertEqual((contract.name, contract.path, contract.size), ("contract.pdf", "old/contract.pdf", 10))
        self.assertEqual(contract.uploaded_at.isoformat(), "2026-11-20T10:00:00+00:00")
        self.assertFalse(apps.get_model("crm", "Attachment").objects.exists())
