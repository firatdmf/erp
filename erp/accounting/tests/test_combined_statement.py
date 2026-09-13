"""One customer, several books, one sheet.

A customer holds at most one account per book, and which book an order
shipped from is our arrangement rather than theirs. Tatyana Varşova holds
one account in Laleli and another in Ergene; asked what she owes, the two
statements answer 756.70 and -529.66 and neither is the number. The CRM
page lists both accounts, so it is where they get picked and printed as
the one statement she would recognise.

Run with:
    python manage.py test accounting.test_combined_statement
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import combined_statement
from crm.models import Company, Contact


class CombinedStatementBase(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)

        self.user = get_user_model().objects.create_user(username="ledger", password="pw")
        self.member = self.user.member
        self.member.books.set([self.laleli, self.ergene])
        self.member.default_book = self.laleli
        self.member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

        self.contact = Contact.objects.create(name="TATYANA VARSOVA")
        self.laleli_account = CurrentAccount.objects.create(
            book=self.laleli, code="LAL-069", name="TATYANA VARSOVA",
            contact=self.contact, default_currency=self.usd)
        self.ergene_account = CurrentAccount.objects.create(
            book=self.ergene, code="ACC-050", name="TATYANA VARSOVA",
            contact=self.contact, default_currency=self.usd)

    def _move(self, account, amount, day, **kw):
        return CurrentAccountMovement.objects.create(
            current_account=account, book=account.book,
            date=f"2026-03-{day:02d}", amount=Decimal(amount),
            currency=kw.pop("currency", self.usd),
            movement_type=kw.pop("movement_type", "order_sale"), **kw)

    def _both(self):
        self._move(self.laleli_account, "756.70", 1)
        self._move(self.ergene_account, "-529.66", 2)

    def _ids(self, *accounts):
        return ",".join(str(a.pk) for a in accounts)


class TheMerge(CombinedStatementBase):
    def test_the_two_books_are_added_up(self):
        self._both()
        data = combined_statement([self.laleli_account, self.ergene_account])
        self.assertEqual(data["closing"], Decimal("227.04"))

    def test_the_closing_balance_is_the_sum_of_the_accounts_own_balances(self):
        """Both come from .live(), so the sheet and the cards it was picked
        from cannot print different numbers."""
        self._both()
        data = combined_statement([self.laleli_account, self.ergene_account])
        self.laleli_account.refresh_from_db()
        self.ergene_account.refresh_from_db()
        self.assertEqual(
            self.laleli_account.cached_balance + self.ergene_account.cached_balance,
            data["closing"])

    def test_rows_are_interleaved_by_date_with_a_running_balance(self):
        self._move(self.laleli_account, "20.00", 1)
        self._move(self.ergene_account, "100.00", 3)
        self._move(self.laleli_account, "-50.00", 5)
        data = combined_statement([self.laleli_account, self.ergene_account])
        self.assertEqual([str(r["mv"].date) for r in data["rows"]],
                         ["2026-03-01", "2026-03-03", "2026-03-05"])
        self.assertEqual([r["balance_after"] for r in data["rows"]],
                         [Decimal("20.00"), Decimal("120.00"), Decimal("70.00")])

    def test_debit_and_credit_foot_to_the_closing_balance(self):
        self._both()
        data = combined_statement([self.laleli_account, self.ergene_account])
        self.assertEqual(data["debit_total"] - data["credit_total"], data["closing"])

    def test_a_cancelled_row_counts_nowhere(self):
        self._move(self.laleli_account, "500.00", 1)
        self._move(self.laleli_account, "-500.00", 2, is_void=True)
        self._move(self.laleli_account, "500.00", 2, is_void=True)
        data = combined_statement([self.laleli_account])
        self.assertEqual(data["closing"], Decimal("500.00"))
        self.assertEqual(len(data["rows"]), 1)

    def test_a_foreign_currency_row_is_added_at_its_own_recorded_rate(self):
        """amount_base normalises to the deployment base currency, not the
        book's — which is what makes two books summable at all."""
        try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="₺")
        # advance_in: an order_sale (the helper's default) must be in the
        # account's currency now — CurrentAccountMovement.check_currency.
        mv = self._move(self.ergene_account, "1000.00", 4, currency=try_,
                        movement_type="advance_in")
        mv.refresh_from_db()
        data = combined_statement([self.ergene_account])
        self.assertEqual(data["closing"], mv.amount_base)
        self.assertNotEqual(mv.amount_base, Decimal("1000.00"))

    def test_one_account_is_a_perfectly_good_selection(self):
        self._both()
        data = combined_statement([self.laleli_account])
        self.assertEqual(data["closing"], Decimal("756.70"))


class WhatMayBePicked(CombinedStatementBase):
    """select_combined_accounts, shared by the sheet and its Excel — a rule
    enforced in only one of them is not a rule."""

    def _print(self, ids):
        return self.client.get(reverse("accounts:statement_print_combined"),
                               {"ids": ids})

    def _excel(self, ids):
        return self.client.get(reverse("accounts:statement_excel_combined"),
                               {"ids": ids})

    def test_nothing_picked_is_refused(self):
        for r in (self._print(""), self._excel("")):
            self.assertEqual(r.status_code, 400)

    def test_an_id_matching_no_account_is_not_quietly_dropped(self):
        """Footing two accounts onto a sheet that was asked for three would
        put a wrong balance in front of a customer."""
        self._both()
        ids = f"{self.laleli_account.pk},999999"
        for r in (self._print(ids), self._excel(ids)):
            self.assertEqual(r.status_code, 404)

    def test_two_different_customers_are_refused(self):
        other = CurrentAccount.objects.create(
            book=self.laleli, code="X-1", name="Someone Else",
            contact=Contact.objects.create(name="Someone Else"),
            default_currency=self.usd)
        ids = self._ids(self.laleli_account, other)
        for r in (self._print(ids), self._excel(ids)):
            self.assertEqual(r.status_code, 400)

    def test_an_account_attached_to_nobody_is_refused(self):
        orphan = CurrentAccount.objects.create(
            book=self.laleli, code="X-2", name="Walk-in",
            default_currency=self.usd)
        for r in (self._print(str(orphan.pk)), self._excel(str(orphan.pk))):
            self.assertEqual(r.status_code, 400)

    def test_a_book_the_member_is_not_assigned_is_refused(self):
        """The rule book_guarded applies to a single account's statement.
        Merging is not a way around it."""
        self._both()
        self.member.books.set([self.laleli])
        ids = self._ids(self.laleli_account, self.ergene_account)
        for r in (self._print(ids), self._excel(ids)):
            self.assertEqual(r.status_code, 404)

    def test_a_duplicate_id_is_counted_once_not_twice(self):
        """Otherwise the same movements would be added to the sheet twice
        and it would foot to double the real balance."""
        self._move(self.laleli_account, "100.00", 1)
        pk = self.laleli_account.pk
        r = self._print(f"{pk},{pk}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["closing"], Decimal("100.00"))

    def test_signing_out_is_required(self):
        self.client.logout()
        r = self._print(str(self.laleli_account.pk))
        self.assertEqual(r.status_code, 302)


class ThePrintedSheet(CombinedStatementBase):
    def _print(self, *accounts):
        r = self.client.get(reverse("accounts:statement_print_combined"),
                            {"ids": self._ids(*accounts)})
        self.assertEqual(r.status_code, 200)
        return r

    def test_it_prints_the_combined_balance(self):
        self._both()
        r = self._print(self.laleli_account, self.ergene_account)
        self.assertEqual(r.context["closing"], Decimal("227.04"))
        self.assertContains(r, "227.04")

    def test_the_header_names_each_book_beside_its_code(self):
        self._both()
        r = self._print(self.laleli_account, self.ergene_account)
        self.assertContains(r, "LAL-069 (Laleli Fabric)")
        self.assertContains(r, "ACC-050 (Ergene Fabric)")

    def test_every_row_names_the_account_it_came_from(self):
        """A merged sheet foots to one balance, so without this there is
        nothing on a line saying which of the two ledgers it sits in."""
        self._both()
        r = self._print(self.laleli_account, self.ergene_account)
        codes = [r["mv"].current_account.code for r in r.context["rows"]]
        self.assertEqual(codes, ["LAL-069", "ACC-050"])
        self.assertContains(r, '<td class="acct">LAL-069</td>', html=False)
        self.assertContains(r, '<td class="acct">ACC-050</td>', html=False)

    def test_it_is_addressed_to_the_crm_record_not_the_ledger_name(self):
        """The two drift — the accounts were imported as GÜRHAN ROMANYA
        and the CRM knows the customer by the name we actually call them."""
        self.contact.name = "Tatyana Warsaw"
        self.contact.save(update_fields=["name"])
        self._both()
        r = self._print(self.laleli_account)
        self.assertEqual(r.context["customer_name"], "Tatyana Warsaw")

    def test_it_writes_nothing_to_the_ledger(self):
        """A document that posted again would claim the same money twice —
        the receivable already sits on each account."""
        self._both()
        before = CurrentAccountMovement.objects.count()
        self._print(self.laleli_account, self.ergene_account)
        self.assertEqual(CurrentAccountMovement.objects.count(), before)
        self.laleli_account.refresh_from_db()
        self.assertEqual(self.laleli_account.cached_balance, Decimal("756.70"))

    def test_an_account_with_no_movements_still_renders(self):
        r = self._print(self.laleli_account)
        self.assertEqual(r.context["closing"], Decimal("0.00"))


class TheExcel(CombinedStatementBase):
    def _excel(self, *accounts):
        return self.client.get(reverse("accounts:statement_excel_combined"),
                               {"ids": self._ids(*accounts)})

    def test_it_comes_back_as_a_spreadsheet_attachment(self):
        self._both()
        r = self._excel(self.laleli_account, self.ergene_account)
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        self.assertIn("attachment", r["Content-Disposition"])

    def test_the_filename_is_the_customer(self):
        self.contact.name = "Tatyana Warsaw"
        self.contact.save(update_fields=["name"])
        self._both()
        r = self._excel(self.laleli_account)
        self.assertIn("Tatyana Warsaw", r["Content-Disposition"])

    def test_it_foots_to_the_same_balance_the_sheet_prints(self):
        """One document in two formats. A total that lived in only one of
        them would be a second answer waiting to disagree."""
        from io import BytesIO
        from openpyxl import load_workbook
        self._both()
        r = self._excel(self.laleli_account, self.ergene_account)
        ws = load_workbook(BytesIO(r.content)).active
        values = {c.value for row in ws.iter_rows() for c in row}
        self.assertIn(227.04, values)

    def test_it_carries_the_same_columns_the_sheet_does(self):
        """One document in two formats: a column in only one of them would
        be a second answer waiting to disagree with the first."""
        from io import BytesIO
        from openpyxl import load_workbook
        self._both()
        r = self._excel(self.laleli_account, self.ergene_account)
        ws = load_workbook(BytesIO(r.content)).active
        text = " ".join(str(c.value) for row in ws.iter_rows() for c in row
                        if c.value is not None)
        # The header names each book beside its code...
        self.assertIn("LAL-069 (Laleli Fabric)", text)
        self.assertIn("ACC-050 (Ergene Fabric)", text)
        # ...and every movement row names its own account.
        header = next(row for row in ws.iter_rows(values_only=True)
                      if row and row[0] == "Date")
        self.assertEqual(header[:5],
                         ("Date", "Account", "Type", "Description", "Reference"))
        self.assertEqual(header[7], "Balance")

    def test_the_totals_still_sit_under_the_columns_they_belong_to(self):
        """The Account column pushed debit, credit and balance one across;
        a Total row left where it was would foot the wrong columns."""
        from io import BytesIO
        from openpyxl import load_workbook
        self._both()
        r = self._excel(self.laleli_account, self.ergene_account)
        ws = load_workbook(BytesIO(r.content)).active
        total = next(row for row in ws.iter_rows(values_only=True)
                     if row and row[0] == "Total")
        self.assertEqual(total[5], 756.70)   # debit
        self.assertEqual(total[6], 529.66)   # credit
        self.assertEqual(total[7], 227.04)   # closing


class TheCardOnTheCrmPage(CombinedStatementBase):
    def test_the_contact_page_offers_the_accounts_to_pick(self):
        self._both()
        r = self.client.get(reverse("crm:contact_detail", args=[self.contact.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Account history")
        self.assertContains(r, "od-account-check")
        self.assertContains(r, f'value="{self.laleli_account.pk}"')
        self.assertContains(r, f'value="{self.ergene_account.pk}"')
        self.assertContains(r, reverse("accounts:statement_print_combined"))
        self.assertContains(r, reverse("accounts:statement_excel_combined"))

    def test_the_company_page_offers_them_too(self):
        company = Company.objects.create(name="Karven Tekstil")
        account = CurrentAccount.objects.create(
            book=self.laleli, code="C-1", name="Karven Tekstil",
            company=company, default_currency=self.usd)
        r = self.client.get(reverse("crm:company_detail", args=[company.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Account history")
        self.assertContains(r, f'value="{account.pk}"')

    def test_the_two_cards_do_not_share_a_checkbox_class(self):
        """Order history and Account history both sit on this page. One
        `.od-order-check` query for both would have Print selected on one
        card silently carrying the other card's ticks."""
        self._both()
        r = self.client.get(reverse("crm:contact_detail", args=[self.contact.pk]))
        body = r.content.decode()
        self.assertIn("pickedAccountIds", body)
        self.assertIn(".od-account-check:checked", body)

    def test_no_tools_are_drawn_when_there_is_nothing_to_pick(self):
        contact = Contact.objects.create(name="Nobody")
        r = self.client.get(reverse("crm:contact_detail", args=[contact.pk]))
        self.assertEqual(r.status_code, 200)
        # The element, not the bare name: the script below the card
        # refers to the button by id whether or not one was drawn.
        self.assertNotContains(r, 'id="printAccountsBtn"')
        self.assertNotContains(r, 'id="excelAccountsBtn"')
