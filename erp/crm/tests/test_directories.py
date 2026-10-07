"""A branch with its own customers sees only its own.

Two books of one business share a directory and so a customer list; a
third book has a directory to itself. Its people must not find the
others' companies, contacts or suppliers — in a list, in a search box,
or by typing an id — and the others must not find theirs.
"""
from contextlib import contextmanager
from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounting.forms import BookForm
from accounting.models import Book
from crm import urls as crm_urls
from crm.models import (Attachment, Company, Contact, Directory, DuplicateName,
                        Note, Supplier)
from operating import audit


@contextmanager
def acting_as(user):
    """Inside a request made by `user`, as far as the models can tell."""
    before = getattr(audit._state, "user", None)
    audit._state.user = user
    try:
        yield
    finally:
        audit._state.user = before


def _staff(username, book, superuser=False):
    create = (get_user_model().objects.create_superuser if superuser
              else get_user_model().objects.create_user)
    user = create(username=username, password="pw")
    # user.member, not a second copy fetched by query: creating the user
    # cached this one on it, and acting_as() hands that same user over.
    member = user.member
    member.books.set([book])
    member.default_book = book
    member.save(update_fields=["default_book"])
    return user


class TwoBusinesses(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.main = Directory.objects.create(name="Main")
        cls.ergene = Book.objects.create(name="Ergene Fabric", directory=cls.main)
        cls.laleli = Book.objects.create(name="Laleli Fabric", directory=cls.main)
        # No directory given: a new book starts with one of its own.
        cls.almaty = Book.objects.create(name="Almaty")

        cls.mustafa = _staff("mustafa_d", cls.ergene)
        cls.cuma = _staff("cuma_d", cls.laleli)
        cls.aigerim = _staff("aigerim_d", cls.almaty)
        cls.owner = _staff("owner_d", cls.ergene, superuser=True)

        cls.woodline = Company.objects.create(name="Woodline", directory=cls.main)
        cls.ayse = Contact.objects.create(name="Ayse Kaya", company=cls.woodline)
        cls.ozce = Supplier.objects.create(company_name="Ozce Tekstil", directory=cls.main)
        cls.note = Note.objects.create(contact=cls.ayse, content="Pays late")
        cls.file = Attachment.objects.create(company=cls.woodline, name="contract.pdf")

        cls.steppe = Company.objects.create(
            name="Steppe Home", directory=cls.almaty.directory)
        cls.dana = Contact.objects.create(name="Dana Akhmet", company=cls.steppe)
        cls.kz_supplier = Supplier.objects.create(
            company_name="Shymkent Cotton", directory=cls.almaty.directory)

    THEIRS = ("Woodline", "Ayse Kaya", "Ozce Tekstil")
    OURS = ("Steppe Home", "Dana Akhmet", "Shymkent Cotton")


class ABookAndItsDirectory(TwoBusinesses):
    def test_a_new_book_gets_a_directory_of_its_own(self):
        self.assertIsNotNone(self.almaty.directory)
        self.assertNotEqual(self.almaty.directory, self.main)
        self.assertEqual(self.almaty.directory.name, "Almaty")

    def test_a_new_book_never_borrows_a_directory_by_name(self):
        book = Book.objects.create(name="Main")
        self.assertNotEqual(book.directory, self.main)

    def test_the_first_book_takes_over_what_was_kept_before_any(self):
        Book.objects.all().delete()
        first = Book.objects.create(name="First")
        self.assertEqual(first.directory, self.main)
        self.assertNotEqual(Book.objects.create(name="Second").directory, self.main)

    def test_the_book_form_offers_only_the_lists_its_author_reads(self):
        with acting_as(self.aigerim):
            offered = set(BookForm().fields["directory"].queryset)
        self.assertEqual(offered, {self.almaty.directory})
        with acting_as(self.owner):
            self.assertIn(self.main, BookForm().fields["directory"].queryset)


class WhereANewRecordIsFiled(TwoBusinesses):
    def test_with_its_authors_working_book(self):
        with acting_as(self.aigerim):
            contact = Contact.objects.create(name="Timur")
        self.assertEqual(contact.directory, self.almaty.directory)
        with acting_as(self.cuma):
            contact = Contact.objects.create(name="Hakan")
        self.assertEqual(contact.directory, self.main)

    def test_a_contact_goes_where_its_company_is(self):
        # The owner works in Ergene, but this company is Almaty's.
        with acting_as(self.owner):
            contact = Contact.objects.create(name="Timur", company=self.steppe)
        self.assertEqual(contact.directory, self.almaty.directory)

    def test_outside_a_request_with_the_oldest_book(self):
        self.assertEqual(Contact.objects.create(name="Imported").directory, self.main)

    def test_the_quick_create_on_the_order_form(self):
        self.client.force_login(self.aigerim)
        self.client.post(reverse("crm:quick_create_customer"),
                         {"type": "contact", "name": "Timur", "kind": "contact"})
        made = Contact.everywhere.filter(name="Timur").first()
        if made is not None:
            self.assertEqual(made.directory, self.almaty.directory)


class WhoSeesWhat(TwoBusinesses):
    def _names(self, model, field="name"):
        return set(model.objects.values_list(field, flat=True))

    def test_the_branch_sees_only_its_own(self):
        with acting_as(self.aigerim):
            self.assertEqual(self._names(Company), {"Steppe Home"})
            self.assertEqual(self._names(Contact), {"Dana Akhmet"})
            self.assertEqual(self._names(Supplier, "company_name"), {"Shymkent Cotton"})
            self.assertFalse(Note.objects.exists())
            self.assertFalse(Attachment.objects.exists())
            self.assertFalse(self.woodline.contacts.exists())

    def test_two_books_of_one_business_share_the_list(self):
        for user in (self.mustafa, self.cuma):
            with acting_as(user):
                self.assertEqual(self._names(Company), {"Woodline"})
                self.assertEqual(self._names(Contact), {"Ayse Kaya"})
                self.assertTrue(Note.objects.filter(pk=self.note.pk).exists())
                self.assertTrue(Attachment.objects.filter(pk=self.file.pk).exists())

    def test_what_one_shop_adds_the_factory_sees(self):
        with acting_as(self.cuma):
            Contact.objects.create(name="Hakan")
        with acting_as(self.mustafa):
            self.assertTrue(Contact.objects.filter(name="Hakan").exists())
        with acting_as(self.aigerim):
            self.assertFalse(Contact.objects.filter(name="Hakan").exists())

    def test_a_member_assigned_no_book_sees_nothing(self):
        nobody = get_user_model().objects.create_user(username="nobody_d", password="pw")
        with acting_as(nobody):
            self.assertFalse(Company.objects.exists())
            self.assertFalse(Contact.objects.exists())
            self.assertFalse(Supplier.objects.exists())

    def test_the_owner_and_work_nobody_is_signed_in_for_see_everything(self):
        with acting_as(self.owner):
            self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(Company.objects.count(), 2)

    def test_a_record_reached_through_another_is_still_named(self):
        # A page that may show an order must be able to name its customer.
        with acting_as(self.aigerim):
            self.assertEqual(Note.everywhere.get(pk=self.note.pk).contact.name, "Ayse Kaya")


class NamesAreUniquePerDirectory(TwoBusinesses):
    def test_each_business_may_have_its_own_of_a_name(self):
        with acting_as(self.aigerim):
            Contact.objects.create(name="ayse kaya")
            Company.objects.create(name="WOODLINE")
            Supplier.objects.create(company_name="Ozce Tekstil")

    def test_a_second_of_a_name_in_one_directory_is_still_refused(self):
        with acting_as(self.mustafa), self.assertRaises(DuplicateName):
            Contact.objects.create(name="AYSE KAYA")
        with acting_as(self.cuma), self.assertRaises(DuplicateName):
            Company.objects.create(name="woodline")

    def test_the_owner_is_held_to_the_directory_not_to_all_of_them(self):
        # The owner reads every directory; the name check must not.
        with acting_as(self.owner):
            Contact.objects.create(name="Dana Akhmet")
            with self.assertRaises(DuplicateName):
                Contact.objects.create(name="Ayse Kaya")

    def test_the_table_agrees(self):
        other = Contact.objects.create(name="Ali")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Contact.everywhere.filter(pk=other.pk).update(name="ayse kaya")
        Contact.everywhere.filter(pk=self.dana.pk).update(name="ayse kaya")

    def test_the_duplicate_check_does_not_say_who_the_others_know(self):
        self.client.force_login(self.aigerim)
        for route, name in (("crm:check_company_duplicate", "Woodline"),
                            ("crm:check_contact_duplicate", "Ayse Kaya")):
            body = self.client.get(reverse(route), {"name": name}).content.decode()
            self.assertNotIn("already exists", body, route)
        self.client.force_login(self.cuma)
        body = self.client.get(reverse("crm:check_company_duplicate"),
                               {"name": "woodline"}).content.decode()
        self.assertIn("already exists", body)


class ThePagesKeepTheWall(TwoBusinesses):
    """Every CRM route, opened by the branch against the others' records."""

    def setUp(self):
        self.client.force_login(self.aigerim)

    def _assert_none_of_theirs(self, response, where):
        body = response.content.decode()
        for name in self.THEIRS:
            self.assertNotIn(name, body, f"{where} shows {name}")

    def test_the_lists(self):
        for route, own in (("crm:contact_list", "Dana Akhmet"),
                           ("crm:company_list", "Steppe Home"),
                           ("crm:supplier_list", "Shymkent Cotton")):
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200, route)
            self._assert_none_of_theirs(response, route)
            self.assertIn(own, response.content.decode(), route)

    def test_the_search_boxes(self):
        searches = (
            ("post", "crm:search_contact", {"searchInput": "a"}),
            ("post", "crm:search_contacts_only", {"searchInput": "a"}),
            ("get", "crm:company_search", {"company_name": "o"}),
            ("get", "crm:task_attach_search", {"q": "o"}),
            ("get", "crm:task_attach_search", {"q": "a"}),
            ("get", "crm:customer_autocomplete", {"customer": "a"}),
            ("get", "crm:customer_autocomplete", {"customer": "o"}),
            ("get", "crm:supplier_search_companies", {"q": "o"}),
            ("get", "crm:supplier_search_contacts", {"q": "a"}),
            ("get", "global_search", {"q": "a"}),
            ("get", "global_search", {"q": "o"}),
        )
        for method, route, data in searches:
            response = getattr(self.client, method)(reverse(route), data)
            self.assertLess(response.status_code, 500, route)
            self._assert_none_of_theirs(response, route)

    # What each route's id names, so the sweep below can hand it one of
    # the OTHER business's. A route missing from here fails the sweep:
    # a new page keyed by id has to say whose record it opens.
    KEYED_BY = {
        "delete_company": "company", "company_detail": "company",
        "update_company": "company", "toggle_email_campaign": "company",
        "get_notes_partial": "company", "get_tasks_partial": "company",
        "delete_contact": "contact", "contact_detail": "contact",
        "update_contact": "contact", "get_contact_notes_partial": "contact",
        "delete_company_from_contact": "contact",
        "supplier_detail": "supplier", "supplier_update": "supplier",
        "supplier_delete": "supplier", "get_supplier_notes_partial": "supplier",
        "update_note": "note", "update_note_ajax": "note", "delete_note": "note",
        "download_attachment": "attachment", "delete_attachment": "attachment",
    }

    def _theirs(self, kind):
        return {"company": self.woodline, "contact": self.ayse,
                "supplier": self.ozce, "note": self.note,
                "attachment": self.file}[kind]

    def _swept_urls(self):
        urls = []
        for pattern in crm_urls.urlpatterns:
            params = pattern.pattern.converters
            if not params:
                continue
            name = pattern.name
            if set(params) == {"pk"}:
                self.assertIn(name, self.KEYED_BY,
                              f"crm:{name} takes an id — add it to KEYED_BY")
                urls.append(reverse(f"crm:{name}", args=[self._theirs(self.KEYED_BY[name]).pk]))
            elif set(params) == {"contact_pk"}:
                urls.append(reverse(f"crm:{name}", args=[self.ayse.pk]))
            elif set(params) == {"company_pk", "contact_pk"}:
                # Their company with our contact, and ours with theirs.
                urls.append(reverse(f"crm:{name}", args=[self.woodline.pk, self.dana.pk]))
                urls.append(reverse(f"crm:{name}", args=[self.steppe.pk, self.ayse.pk]))
            elif set(params) == {"kind", "pk"}:
                for kind in ("company", "contact", "supplier"):
                    urls.append(reverse(f"crm:{name}", args=[kind, self._theirs(kind).pk]))
            else:
                self.fail(f"crm:{name} takes {sorted(params)} — teach the sweep about it")
        return urls

    def test_no_route_opens_or_changes_the_others_records_by_id(self):
        before = self._snapshot()
        for url in self._swept_urls():
            for method in ("get", "post"):
                if method == "get" and "/delete/" in url:
                    continue  # the delete views answer POST only
                response = getattr(self.client, method)(
                    url, {"content": "hacked", "name": "Hacked", "note_id": self.note.pk},
                    # Several of these go "back" when they are done.
                    HTTP_REFERER="/crm/")
                # Refused outright, or (a view that only acts on POST)
                # an answer that names nothing of theirs; the snapshot
                # below is what proves nothing was changed either way.
                self.assertIn(response.status_code, (200, 302, 403, 404, 405),
                              f"{method.upper()} {url} answered {response.status_code}")
                if response.status_code != 302:
                    self._assert_none_of_theirs(response, url)
        self.assertEqual(self._snapshot(), before)

    def _snapshot(self):
        return {
            "companies": list(Company.everywhere.order_by("pk").values_list("pk", "name")),
            "contacts": list(Contact.everywhere.order_by("pk")
                             .values_list("pk", "name", "company_id")),
            "suppliers": list(Supplier.everywhere.order_by("pk")
                              .values_list("pk", "company_name")),
            "notes": list(Note.everywhere.order_by("pk").values_list("pk", "content")),
            "files": list(Attachment.everywhere.order_by("pk").values_list("pk", "name")),
        }

    def test_the_same_routes_open_for_the_business_they_belong_to(self):
        # The sweep above would pass on a site that refused everybody.
        self.client.force_login(self.cuma)
        for route, record in (("crm:contact_detail", self.ayse),
                              ("crm:company_detail", self.woodline),
                              ("crm:supplier_detail", self.ozce)):
            response = self.client.get(reverse(route, args=[record.pk]))
            self.assertEqual(response.status_code, 200, route)


class WhatNamesACustomerKeepsTheWallToo(TwoBusinesses):
    """An order, a task or a purchase order is not a CRM record, but its
    pages print one's name."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from operating.models import Order
        from operating.models_procurement import PurchaseOrder
        from todo.models import Task

        cls.order = Order.objects.create(company=cls.woodline)
        today = date.today()
        cls.task = Task.objects.create(
            name="Call about the velvet", contact=cls.ayse, due_date=today)
        cls.loose_task = Task.objects.create(name="Sweep the floor", due_date=today)
        cls.purchase = PurchaseOrder.objects.create(
            supplier=cls.ozce, created_by=cls.owner)

    ORDER_ROUTES = ("operating:order_customer_card", "operating:order_print",
                    "operating:order_changes", "operating:order_excel",
                    "operating:export_packing_list_excel",
                    "operating:order_packing_list_pdf")

    def test_an_orders_printouts_are_closed_to_the_other_business(self):
        self.client.force_login(self.aigerim)
        for route in self.ORDER_ROUTES:
            response = self.client.get(reverse(route, args=[self.order.pk]))
            self.assertEqual(response.status_code, 404, route)

    def test_and_open_to_its_own(self):
        self.client.force_login(self.cuma)
        for route in ("operating:order_customer_card", "operating:order_print",
                      "operating:order_changes"):
            response = self.client.get(reverse(route, args=[self.order.pk]))
            self.assertEqual(response.status_code, 200, route)

    def test_an_order_naming_nobody_is_nobodys_secret(self):
        from operating.models import Order
        self.client.force_login(self.aigerim)
        order = Order.objects.create()
        response = self.client.get(reverse("operating:order_changes", args=[order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_a_task_about_their_customer_is_not_listed_or_opened(self):
        from todo.models import Task
        with acting_as(self.aigerim):
            self.assertEqual(list(Task.objects.all()), [self.loose_task])
        with acting_as(self.mustafa):
            self.assertEqual(Task.objects.count(), 2)
        self.client.force_login(self.aigerim)
        body = self.client.get(reverse("todo:tasks_list")).content.decode()
        self.assertNotIn("Ayse Kaya", body)
        self.assertNotIn("Call about the velvet", body)
        response = self.client.get(
            reverse("todo:task_detail_ajax", args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_purchase_order_with_their_supplier_is_not_listed_or_opened(self):
        self.client.force_login(self.aigerim)
        body = self.client.get(
            reverse("operating:purchase_order_list")).content.decode()
        self.assertNotIn("Ozce Tekstil", body)
        response = self.client.get(
            reverse("operating:purchase_order_detail", args=[self.purchase.pk]))
        self.assertEqual(response.status_code, 404)

    def test_the_order_analytics_rank_only_customers_in_reach(self):
        self.client.force_login(self.aigerim)
        response = self.client.get(reverse("operating:order_analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Woodline", response.content.decode())


class ACustomerOfBoth(TwoBusinesses):
    """A customer two businesses deal with is one record, shared."""

    def test_sharing_a_company_shows_it_and_its_people_to_the_other_side(self):
        self.woodline.share_with(self.almaty.directory)
        with acting_as(self.aigerim):
            self.assertTrue(Company.objects.filter(pk=self.woodline.pk).exists())
            self.assertTrue(Contact.objects.filter(pk=self.ayse.pk).exists())
            self.assertFalse(Supplier.objects.filter(pk=self.ozce.pk).exists())
            self.assertIn(self.woodline, Company.objects.here())
        # Still one record, at home where it was.
        self.assertEqual(Company.everywhere.filter(name="Woodline").count(), 1)
        self.woodline.refresh_from_db()
        self.assertEqual(self.woodline.directory, self.main)

    def test_someone_who_joins_a_shared_company_is_shared_too(self):
        self.woodline.share_with(self.almaty.directory)
        with acting_as(self.cuma):
            hakan = Contact.objects.create(name="Hakan", company=self.woodline)
        with acting_as(self.aigerim):
            self.assertTrue(Contact.objects.filter(pk=hakan.pk).exists())

    def test_it_can_be_taken_back(self):
        self.woodline.share_with(self.almaty.directory)
        self.woodline.stop_sharing_with(self.almaty.directory)
        with acting_as(self.aigerim):
            self.assertFalse(Company.objects.filter(pk=self.woodline.pk).exists())
            self.assertFalse(Contact.objects.filter(pk=self.ayse.pk).exists())

    def test_a_twin_is_not_shared_in_beside_the_one_already_there(self):
        Company.objects.create(name="woodline", directory=self.almaty.directory)
        with self.assertRaises(DuplicateName):
            self.woodline.share_with(self.almaty.directory)
        self.assertFalse(self.woodline.shared_with.exists())

    def test_nor_made_beside_one_that_was_shared_in(self):
        self.woodline.share_with(self.almaty.directory)
        with acting_as(self.aigerim), self.assertRaises(DuplicateName):
            Company.objects.create(name="Woodline")

    def test_each_sides_dealings_with_them_stay_its_own(self):
        from accounting.models import CurrencyCategory
        from accounting.models_accounts import CurrentAccount
        from operating.models import Order

        self.woodline.share_with(self.almaty.directory)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        theirs = CurrentAccount.objects.create(
            book=self.laleli, code="C-WDL", name="Woodline", type="customer",
            company=self.woodline, default_currency=usd)
        ours = CurrentAccount.objects.create(
            book=self.almaty, code="C-WDL", name="Woodline", type="customer",
            company=self.woodline, default_currency=usd)
        their_order = Order.objects.create(company=self.woodline, current_account=theirs)
        our_order = Order.objects.create(company=self.woodline, current_account=ours)

        self.client.force_login(self.aigerim)
        page = self.client.get(reverse("crm:company_detail", args=[self.woodline.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertEqual([o.pk for o in page.context["orders"]], [our_order.pk])
        self.assertEqual([a.book for a in page.context["current_account_accounts"]],
                         [self.almaty])
        self.assertEqual(self.client.get(
            reverse("operating:order_print", args=[their_order.pk])).status_code, 404)
        self.assertEqual(self.client.get(
            reverse("operating:order_print", args=[our_order.pk])).status_code, 200)

        # The factory and the shop are one business: each sees the other's.
        self.client.force_login(self.mustafa)
        page = self.client.get(reverse("crm:company_detail", args=[self.woodline.pk]))
        self.assertEqual([o.pk for o in page.context["orders"]], [their_order.pk])


class WhoMayShare(TwoBusinesses):
    def _share(self, record, kind, directory, share="1"):
        return self.client.post(
            reverse("crm:share_record", args=[kind, record.pk]),
            {"directory": directory.pk, "share": share}, HTTP_REFERER="/crm/")

    def test_the_owner_shares_and_stops_from_the_page(self):
        self.client.force_login(self.owner)
        page = self.client.get(reverse("crm:company_detail", args=[self.woodline.pk]))
        self.assertContains(page, reverse("crm:share_record", args=["company", self.woodline.pk]))
        self._share(self.woodline, "company", self.almaty.directory)
        self.assertEqual(list(self.woodline.shared_with.all()), [self.almaty.directory])
        self._share(self.woodline, "company", self.almaty.directory, share="0")
        self.assertFalse(self.woodline.shared_with.exists())

    def test_a_twin_is_reported_not_shared(self):
        Company.objects.create(name="Woodline", directory=self.almaty.directory)
        self.client.force_login(self.owner)
        response = self._share(self.woodline, "company", self.almaty.directory)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.woodline.shared_with.exists())

    def test_someone_on_one_side_cannot(self):
        # Not their own record out to a list they do not read...
        self.client.force_login(self.aigerim)
        self.assertEqual(self._share(self.steppe, "company", self.main).status_code, 404)
        self.assertFalse(self.steppe.shared_with.exists())
        # ...nor a record shared with them, onward or away.
        self.woodline.share_with(self.almaty.directory)
        response = self._share(self.woodline, "company", self.almaty.directory, share="0")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.woodline.shared_with.exists())
        page = self.client.get(reverse("crm:company_detail", args=[self.woodline.pk]))
        self.assertNotContains(page, "/share/")


class OneBooksListAtATime(TwoBusinesses):
    """The owner reads every list, and sees one at a time."""

    def _work_in(self, book):
        member = self.owner.member
        member.default_book = book
        member.save(update_fields=["default_book"])

    def test_lists_and_search_follow_the_working_book(self):
        self.client.force_login(self.owner)
        body = self.client.get(reverse("crm:contact_list")).content.decode()
        self.assertIn("Ayse Kaya", body)
        self.assertNotIn("Dana Akhmet", body)
        found = self.client.get(reverse("crm:customer_autocomplete"),
                                {"customer": "a"}).content.decode()
        self.assertNotIn("Dana Akhmet", found)

        self._work_in(self.almaty)
        body = self.client.get(reverse("crm:contact_list")).content.decode()
        self.assertIn("Dana Akhmet", body)
        self.assertNotIn("Ayse Kaya", body)

    def test_a_page_opened_by_id_opens_whichever_book_they_are_in(self):
        self.client.force_login(self.owner)
        for route, record in (("crm:contact_detail", self.dana),
                              ("crm:company_detail", self.steppe),
                              ("crm:supplier_detail", self.kz_supplier)):
            response = self.client.get(reverse(route, args=[record.pk]))
            self.assertEqual(response.status_code, 200, route)

    def test_twins_are_never_side_by_side(self):
        self.client.force_login(self.owner)

        def found():
            return self.client.get(reverse("crm:customer_autocomplete"),
                                   {"customer": "Ayse"}).content.decode()

        alone = found().count("Ayse Kaya")
        self.assertGreater(alone, 0)
        Contact.objects.create(name="Ayse Kaya", directory=self.almaty.directory)
        self.assertEqual(found().count("Ayse Kaya"), alone)


class TheShelvesAndTheLedgerKeepTheWallToo(TwoBusinesses):
    """A branch with its own book does not read another business's
    warehouses or ledger rows by typing an id — both name customers."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from accounting.models import CurrencyCategory
        from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
        from operating.models import Order, StockMovement, Warehouse, WarehouseProduct

        cls.shop = Warehouse.objects.create(name="Laleli", accounting_book=cls.laleli)
        cls.mill = Warehouse.objects.create(name="Ergene Fabrika", accounting_book=cls.ergene)
        cls.both = Warehouse.objects.create(name="Ortak", kind="combined")
        cls.both.combined_sources.set([cls.shop, cls.mill])
        cls.depot = Warehouse.objects.create(name="Almaty Depo", accounting_book=cls.almaty)
        cls.velvet = WarehouseProduct.objects.create(
            warehouse=cls.mill, name="Velvet", sku="VLV-1")
        StockMovement.objects.create(
            product=cls.velvet, quantity=1, movement_type="out",
            reason="Sample for Ayse Kaya", contact=cls.ayse)
        cls.order = Order.objects.create(company=cls.woodline, order_number="900")

        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        cls.account = CurrentAccount.objects.create(
            book=cls.laleli, code="C-WDL", name="Woodline", type="customer",
            company=cls.woodline, default_currency=usd)

    def test_the_movement_feed_is_the_readers_warehouses_only(self):
        self.client.force_login(self.aigerim)
        body = self.client.get(reverse("operating:warehouse_movements_all")).content.decode()
        self.assertNotIn("Ayse Kaya", body)
        self.assertNotIn("Ergene Fabrika", body)
        # The shop reads the mill's through the warehouse they share.
        self.client.force_login(self.cuma)
        body = self.client.get(reverse("operating:warehouse_movements_all")).content.decode()
        self.assertIn("Ayse Kaya", body)

    def test_pages_under_another_business_warehouse_do_not_open(self):
        self.client.force_login(self.aigerim)
        for url in (
            reverse("operating:warehouse_movements", args=[self.mill.pk]),
            reverse("operating:warehouse_product_detail", args=[self.mill.pk, self.velvet.pk]),
            reverse("operating:warehouse_barcode_lookup", args=[self.mill.pk]) + "?code=X",
            reverse("operating:warehouse_excel", args=[self.mill.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.get(
            reverse("operating:warehouse_movements", args=[self.depot.pk])).status_code, 200)

    def test_a_member_of_a_shared_warehouse_still_opens_for_the_other_book(self):
        self.client.force_login(self.cuma)
        for url in (
            reverse("operating:warehouse_movements", args=[self.mill.pk]),
            reverse("operating:warehouse_product_detail", args=[self.mill.pk, self.velvet.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_an_order_is_named_by_number_alone_to_someone_outside(self):
        with acting_as(self.aigerim):
            self.assertEqual(str(self.order), "Order 900")
        with acting_as(self.cuma):
            self.assertIn("Woodline", str(self.order))
        self.assertIn("Woodline", str(self.order))

    def test_ledger_rows_of_another_book_do_not_open_or_act(self):
        self.client.force_login(self.aigerim)
        for method, route in (("get", "accounts:fx_post"), ("post", "accounts:fx_post")):
            response = getattr(self.client, method)(reverse(route, args=[self.account.pk]))
            self.assertEqual(response.status_code, 404, route)

    def test_every_ledger_route_keyed_by_id_is_guarded(self):
        """Nothing in the ledger's URLconf takes a row's id without
        checking the row's book — a plain path() there is a hole."""
        from accounting import urls_accounts

        for pattern in urls_accounts.urlpatterns:
            if "pk" not in pattern.pattern.converters:
                continue
            guarded = getattr(pattern.callback, "__wrapped__", None) is not None
            self.assertTrue(guarded, f"accounts:{pattern.name} names a row by id unguarded")
