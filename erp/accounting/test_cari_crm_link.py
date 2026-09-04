"""An account has to be able to say who it stands for — after the fact.

Creating an account through the UI has always minted the matching CRM
record alongside it. Nothing did that for the 1,148 accounts carried in
from the legacy Laleli ledger, and until this existed nothing could:
CariEdit never touched contact/company/supplier, so those accounts had no
CRM record and no route to one short of a shell. Downstream code had
started working around the hole (warehouse intake resolves through
cari.supplier, empty on every imported account) rather than closing it.

Run with:
    python manage.py test accounting.test_cari_crm_link
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from crm.models import Company, Contact, Supplier


class CrmLinkPicker(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Ergene Fabric")

        self.user = get_user_model().objects.create_user(username="ledger", password="pw")
        self.member = self.user.member
        self.member.books.set([self.book, self.other_book])
        self.member.default_book = self.book
        self.member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

        self.cari = CariAccount.objects.create(
            book=self.book, code="00554", name="GÜRHAN ROMANYA",
            default_currency=self.usd, cached_balance=Decimal("608.26"),
            email="gurhan@example.com", phone="5551234567",
            billing_address="Laleli", billing_country="Romania",
        )

    def _link(self, **post):
        return self.client.post(
            reverse("accounts:crm_link", args=[self.cari.pk]), post, follow=True)

    def _search(self, q):
        r = self.client.get(reverse("accounts:crm_search", args=[self.cari.pk]), {"q": q})
        self.assertEqual(r.status_code, 200)
        return r.json()["results"]

    # ── the model's own answer ────────────────────────────────────────
    def test_an_unlinked_account_says_so_rather_than_raising(self):
        self.assertIsNone(self.cari.crm_link)
        self.assertEqual(self.cari.crm_link_field, "")

    def test_a_linked_account_names_the_one_field_that_holds_it(self):
        self.cari.company = Company.objects.create(name="Gürhan Tekstil")
        self.assertEqual(self.cari.crm_link_field, "company")
        self.assertEqual(self.cari.crm_link.name, "Gürhan Tekstil")

    # ── attaching ─────────────────────────────────────────────────────
    def test_attaching_an_existing_record(self):
        company = Company.objects.create(name="Gürhan Tekstil")
        self._link(action="attach", kind="company", id=company.pk)
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.company_id, company.pk)

    def test_re_pointing_a_link_clears_the_old_one(self):
        """clean() refuses two links at once, so switching has to drop the
        first — otherwise the account would be a contact AND a company."""
        contact = Contact.objects.create(name="Gürhan")
        company = Company.objects.create(name="Gürhan Tekstil")
        self._link(action="attach", kind="contact", id=contact.pk)
        self._link(action="attach", kind="company", id=company.pk)
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.company_id, company.pk)
        self.assertIsNone(self.cari.contact_id)

    def test_a_record_already_taken_in_this_book_is_refused_by_name(self):
        """The constraint would raise IntegrityError and say nothing the
        reader can act on. What they need is the account holding it —
        which is usually the duplicate they were about to make by hand."""
        company = Company.objects.create(name="MARKİSS TEKSTİL")
        holder = CariAccount.objects.create(
            book=self.book, code="00163", name="MARKİSS TEKSTİL",
            company=company, default_currency=self.usd)
        r = self._link(action="attach", kind="company", id=company.pk)
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.company_id)
        self.assertContains(r, holder.code)

    def test_the_same_record_may_hold_one_account_per_book(self):
        """Per-book, not global — a customer trades with both businesses."""
        company = Company.objects.create(name="Karven")
        CariAccount.objects.create(book=self.other_book, code="E-001",
                                   name="Karven", company=company,
                                   default_currency=self.usd)
        self._link(action="attach", kind="company", id=company.pk)
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.company_id, company.pk)

    def test_a_record_that_has_been_deleted_meanwhile_is_reported(self):
        r = self._link(action="attach", kind="company", id=999999)
        self.assertEqual(r.status_code, 200)
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.company_id)

    # ── creating ──────────────────────────────────────────────────────
    def test_creating_carries_what_the_account_already_knows(self):
        """On an imported account the name, address and phone are the only
        record of that customer anyone has. Retyping them into a CRM form
        is how they come out different."""
        self._link(action="create", kind="company", name=self.cari.name)
        self.cari.refresh_from_db()
        company = self.cari.company
        self.assertIsNotNone(company)
        self.assertEqual(company.name, "GÜRHAN ROMANYA")
        self.assertEqual(company.email, ["gurhan@example.com"])
        self.assertEqual(company.phone, ["5551234567"])
        self.assertEqual(company.country, "Romania")

    def test_creating_a_contact_and_a_supplier_too(self):
        self._link(action="create", kind="contact", name="Gürhan")
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.contact.name, "Gürhan")

        self._link(action="create", kind="supplier", name="Karven Mensucat")
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.contact_id)
        self.assertEqual(self.cari.supplier.company_name, "Karven Mensucat")

    def test_a_duplicate_company_name_is_refused_not_silently_reused(self):
        """Company.name is unique. Attaching to someone else's company
        because the names match is a judgement only the reader can make,
        and the search box above the button is how they make it."""
        Company.objects.create(name="GÜRHAN ROMANYA")
        self._link(action="create", kind="company", name="GÜRHAN ROMANYA")
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.company_id)
        self.assertEqual(Company.objects.filter(name="GÜRHAN ROMANYA").count(), 1)

    def test_a_name_the_crm_cannot_hold_is_said_out_loud(self):
        """Contact.name holds 50 characters and plenty of the imported
        account names are longer. Cutting one in half here is how a record
        becomes unfindable later, so it fails instead."""
        long_name = "İNNA GALA KOTOBSK 63 KARGO KOD 3325 " * 3
        r = self._link(action="create", kind="contact", name=long_name)
        self.assertEqual(r.status_code, 200)
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.contact_id)
        self.assertFalse(Contact.objects.exists())

    # ── detaching ─────────────────────────────────────────────────────
    def test_detaching_leaves_the_ledger_alone(self):
        company = Company.objects.create(name="Gürhan Tekstil")
        self._link(action="attach", kind="company", id=company.pk)
        self._link(action="detach")
        self.cari.refresh_from_db()
        self.assertIsNone(self.cari.company_id)
        self.assertEqual(self.cari.cached_balance, Decimal("608.26"))
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())

    # ── the card on the page ──────────────────────────────────────────
    def test_the_card_is_drawn_on_an_unlinked_account(self):
        """It used to render only when a link existed, so the accounts that
        most need attention were the ones showing nothing at all."""
        r = self.client.get(reverse("accounts:detail", args=[self.cari.pk]))
        self.assertEqual(r.status_code, 200)
        # The search URL is only ever emitted by the picker's markup.
        self.assertContains(r, reverse("accounts:crm_search", args=[self.cari.pk]))
        self.assertNotContains(r, 'value="detach"')

    def test_a_linked_account_shows_the_record_and_a_way_out(self):
        self.cari.company = Company.objects.create(name="Gürhan Tekstil")
        self.cari.save(update_fields=["company"])
        r = self.client.get(reverse("accounts:detail", args=[self.cari.pk]))
        self.assertContains(r, "Gürhan Tekstil")
        self.assertContains(r, 'value="detach"')
        self.assertNotContains(r, reverse("accounts:crm_search", args=[self.cari.pk]))

    def test_an_other_account_is_not_warned_about(self):
        """The walk-in counter and an inter-company position stand alone by
        design. Warning about a CRM record they will never have is an alarm
        nobody can ever clear, so it reads as noise on every other account
        too."""
        self.cari.type = "other"
        self.cari.save(update_fields=["type"])
        r = self.client.get(reverse("accounts:detail", args=[self.cari.pk]))
        # class="..." rather than the bare name — the CSS block names
        # both selectors on every render.
        self.assertNotContains(r, 'class="cd-crm-none"')
        self.assertContains(r, 'class="cd-crm-standalone"')
        # The picker stays — the type itself can be wrong.
        self.assertContains(r, reverse("accounts:crm_search", args=[self.cari.pk]))

    def test_the_retail_counter_is_created_as_other(self):
        from accounting.services_accounts import get_or_create_retail_cari
        self.assertEqual(get_or_create_retail_cari(member=self.member).type, "other")

    # ── searching ─────────────────────────────────────────────────────
    def test_search_finds_a_turkish_name_typed_on_any_keyboard(self):
        Company.objects.create(name="GÜRHAN TEKSTİL")
        labels = [r["label"] for r in self._search("gurhan")]
        self.assertIn("GÜRHAN TEKSTİL", labels)

    def test_search_covers_all_three_kinds(self):
        Contact.objects.create(name="Karven Ahmet")
        Company.objects.create(name="Karven Tekstil")
        Supplier.objects.create(company_name="Karven Mensucat")
        kinds = {r["kind"] for r in self._search("karven")}
        self.assertEqual(kinds, {"contact", "company", "supplier"})

    def test_search_names_the_account_already_holding_a_candidate(self):
        company = Company.objects.create(name="MARKİSS TEKSTİL")
        CariAccount.objects.create(book=self.book, code="00163", name="MARKİSS",
                                   company=company, default_currency=self.usd)
        row = next(r for r in self._search("markiss") if r["kind"] == "company")
        self.assertEqual(row["taken"]["code"], "00163")

    def test_a_candidate_taken_in_another_book_is_still_offered(self):
        company = Company.objects.create(name="Karven")
        CariAccount.objects.create(book=self.other_book, code="E-001", name="Karven",
                                   company=company, default_currency=self.usd)
        row = next(r for r in self._search("karven") if r["kind"] == "company")
        self.assertIsNone(row["taken"])

    def test_an_empty_query_returns_nothing_rather_than_everything(self):
        Company.objects.create(name="Karven")
        self.assertEqual(self._search(""), [])


class CrmLinkFilter(TestCase):
    """The list has to be able to show what is still unidentified — 85% of
    the Laleli book on the day this was written."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.user = get_user_model().objects.create_user(username="ledger", password="pw")
        member = self.user.member
        member.books.set([self.book])
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

        CariAccount.objects.create(book=self.book, code="00554", name="Imported",
                                   default_currency=self.usd)
        CariAccount.objects.create(
            book=self.book, code="00555", name="Known", default_currency=self.usd,
            company=Company.objects.create(name="Known Tekstil"))

    def _codes(self, **params):
        r = self.client.get(reverse("accounts:list", kwargs={"book_id": self.book.pk}),
                            params)
        self.assertEqual(r.status_code, 200)
        return {c.code for c in r.context["caris"]}

    def test_no_crm_link(self):
        self.assertEqual(self._codes(crm="none"), {"00554"})

    def test_linked(self):
        self.assertEqual(self._codes(crm="linked"), {"00555"})

    def test_unfiltered_shows_both(self):
        self.assertEqual(self._codes(), {"00554", "00555"})

    def test_a_supplier_link_counts_as_linked_too(self):
        CariAccount.objects.create(
            book=self.book, code="00556", name="Mill", default_currency=self.usd,
            supplier=Supplier.objects.create(company_name="Mill"))
        self.assertEqual(self._codes(crm="linked"), {"00555", "00556"})
