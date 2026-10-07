"""The supplier page carries what the contact page carries.

Contact and company detail grew files, an always-open note composer,
and Account history across every book; the supplier page was left as
first drawn. It now shows the same, plus Purchase history — the
supplier's side of a customer's Order history — and who raised the
record.

Run:
    python manage.py test crm.tests.test_supplier_detail
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from authentication.models import Member
from crm.models import Note, Supplier
from crm.tests import works_in_a_book

User = get_user_model()


class SupplierDetailPage(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("firat", password="x", email="f@x.c")
        cls.member = Member.objects.get(user=cls.user)
        cls.supplier = Supplier.objects.create(company_name="Karven Tekstil", contact_name="Ali")
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        cls.laleli = Book.objects.create(name="Laleli")
        cls.ergene = Book.objects.create(name="Ergene")
        cls.acc_laleli = CurrentAccount.objects.create(
            book=cls.laleli, code="S-KRV", name="Karven", type="supplier",
            supplier=cls.supplier, default_currency=usd,
        )
        cls.acc_ergene = CurrentAccount.objects.create(
            book=cls.ergene, code="S-KRV-E", name="Karven", type="supplier",
            supplier=cls.supplier, default_currency=usd,
        )
        cls.purchase = Invoice.objects.create(
            current_account=cls.acc_laleli, book=cls.laleli, currency=usd,
            type="purchase", status="issued", number="Purchase-2026-000007",
            date=date(2026, 9, 1), due_date=date(2026, 10, 1),
        )
        cls.note = Note.objects.create(supplier=cls.supplier, content="Ships on Fridays")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("crm:supplier_detail", args=[self.supplier.pk])

    def test_page_renders(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Karven Tekstil")

    def test_files_hang_off_the_supplier(self):
        res = self.client.get(self.url)
        self.assertContains(
            res, reverse("crm:upload_attachments", args=["supplier", self.supplier.pk]))
        self.assertContains(res, 'id="attachmentsList"')

    def test_note_composer_and_history(self):
        res = self.client.get(self.url)
        self.assertContains(res, 'id="noteComposerInput"')
        self.assertContains(res, "Ships on Fridays")
        self.assertContains(res, f"/crm/supplier/{self.supplier.pk}/notes_partial/")

    def test_every_books_account_is_listed(self):
        res = self.client.get(self.url)
        self.assertContains(res, "Account history")
        self.assertContains(res, reverse("accounts:detail", args=[self.acc_laleli.pk]))
        self.assertContains(res, reverse("accounts:detail", args=[self.acc_ergene.pk]))
        self.assertContains(res, reverse("accounts:statement_print_combined"))

    def test_purchases_are_listed_with_their_page(self):
        res = self.client.get(self.url)
        self.assertContains(res, "Purchase history")
        self.assertContains(res, "Purchase-2026-000007")
        self.assertContains(
            res, reverse("accounts:purchase_order_detail", args=[self.purchase.pk]))

    def test_creator_is_named(self):
        res = self.client.get(self.url)
        # This row predates the column: the page says so instead of
        # printing a bare dash.
        self.assertContains(res, "Creator not recorded")

    def test_new_supplier_is_stamped_with_its_creator(self):
        res = self.client.post(reverse("crm:supplier_create"), {
            "company_name": "Yeni Iplik", "contact_name": "", "email": "",
            "phone": "", "website": "", "address": "", "country": "",
        })
        self.assertIn(res.status_code, (200, 302), res.content[:300])
        made = Supplier.objects.get(company_name="Yeni Iplik")
        self.assertEqual(made.created_by, self.user)

    def test_adding_a_task_returns_rows_the_page_counts(self):
        res = self.client.post(
            self.url + "?action=add_task",
            {"name": "Call about the delay", "due_date": "2026-10-01",
             "priority": "medium", "member": self.member.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'class="od-task"')
        self.assertContains(res, "Call about the delay")


class SupplierEditSidebar(TestCase):
    """Edit opens a slide-in on the detail page, served by SupplierUpdate
    over XHR: the form partial on GET, JSON on POST."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("firat2", password="x", email="f2@x.c")
        cls.supplier = Supplier.objects.create(company_name="Karven Tekstil", country="TR")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("crm:supplier_update", args=[self.supplier.pk])
        self.xhr = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def _post(self, **fields):
        data = {"company_name": "", "contact_name": "", "email": "", "phone": "",
                "website": "", "address": "", "country": "",
                "linked_company": "", "linked_contact": ""}
        data.update(fields)
        return self.client.post(self.url, data, **self.xhr)

    def test_detail_page_opens_the_sidebar(self):
        res = self.client.get(reverse("crm:supplier_detail", args=[self.supplier.pk]))
        self.assertContains(res, "openEditSupplierSidebar()")
        self.assertContains(res, 'id="editSupplierSidebarOverlay"')

    def test_xhr_get_is_the_bare_form(self):
        res = self.client.get(self.url, **self.xhr)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'id="editSupplierForm"')
        self.assertContains(res, 'value="Karven Tekstil"')
        self.assertContains(res, reverse("crm:supplier_search_companies"))
        self.assertNotContains(res, "<html")

    def test_plain_get_is_still_the_full_page(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "<html")
        self.assertContains(res, "Edit supplier")

    def test_xhr_post_saves_and_points_back_at_the_record(self):
        res = self._post(company_name="Karven Tekstil A.S.", phone="0212 555")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["redirect_url"],
                         reverse("crm:supplier_detail", args=[self.supplier.pk]))
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.company_name, "Karven Tekstil A.S.")
        self.assertEqual(self.supplier.phone, "0212 555")

    def test_xhr_post_reports_errors_as_json(self):
        res = self._post(email="not-an-email")
        self.assertEqual(res.status_code, 400)
        errors = res.json()["errors"]
        self.assertIn("email", errors)
        # Neither name given: the model's rule comes back form-level.
        self.assertIn("__all__", errors)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.company_name, "Karven Tekstil")


class SupplierEditGuard(TestCase):
    """Who may edit: admins anything, others what they created, nobody but
    an admin a supplier whose creator was never recorded."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin3", password="x", email="a3@x.c")
        cls.owner = User.objects.create_user("owner3", password="x")
        cls.other = User.objects.create_user("other3", password="x")
        for user in (cls.owner, cls.other):
            works_in_a_book(user)
        cls.legacy = Supplier.objects.create(company_name="Old Mill")
        cls.owned = Supplier.objects.create(company_name="New Mill", created_by=cls.owner)

    def _edit(self, supplier, user, ajax=True):
        self.client.force_login(user)
        extra = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if ajax else {}
        return self.client.post(
            reverse("crm:supplier_update", args=[supplier.pk]),
            {"company_name": "Renamed", "contact_name": "", "email": "", "phone": "",
             "website": "", "address": "", "country": "",
             "linked_company": "", "linked_contact": ""},
            **extra,
        )

    def test_admin_edits_a_legacy_supplier(self):
        res = self._edit(self.legacy, self.admin)
        self.assertEqual(res.status_code, 200)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.company_name, "Renamed")

    def test_creator_edits_their_own(self):
        res = self._edit(self.owned, self.owner)
        self.assertEqual(res.status_code, 200)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.company_name, "Renamed")

    def test_someone_else_is_refused_over_xhr(self):
        res = self._edit(self.owned, self.other)
        self.assertEqual(res.status_code, 403)
        self.assertFalse(res.json()["success"])
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.company_name, "New Mill")

    def test_legacy_supplier_is_admin_only(self):
        res = self._edit(self.legacy, self.other)
        self.assertEqual(res.status_code, 403)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.company_name, "Old Mill")

    def test_full_page_refusal_returns_to_the_record(self):
        res = self._edit(self.owned, self.other, ajax=False)
        self.assertRedirects(res, reverse("crm:supplier_detail", args=[self.owned.pk]),
                             fetch_redirect_response=False)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.company_name, "New Mill")


class BackfillSupplierCreator(TestCase):
    """crm.0022: suppliers older than the created_by column are Firat's."""

    def _run(self):
        import importlib
        from django.apps import apps
        mod = importlib.import_module("crm.migrations.0022_backfill_supplier_created_by")
        mod.name_firat_as_creator(apps, None)

    def test_legacy_rows_become_firats_and_owned_rows_are_left(self):
        firat = User.objects.create_user("firat", password="x")
        other = User.objects.create_user("zeynep", password="x")
        legacy = Supplier.objects.create(company_name="Old Mill")
        owned = Supplier.objects.create(company_name="New Mill", created_by=other)
        self._run()
        legacy.refresh_from_db(); owned.refresh_from_db()
        self.assertEqual(legacy.created_by, firat)
        self.assertEqual(owned.created_by, other)

    def test_without_a_firat_nothing_changes(self):
        legacy = Supplier.objects.create(company_name="Old Mill")
        self._run()
        legacy.refresh_from_db()
        self.assertIsNone(legacy.created_by)
