"""Capital can be paid in goods: the stock an owner hands over is capital
as a bank transfer would have been, and moves no cash at all."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounting.models import (
    Book, CashAccount, CashTransactionEntry, CurrencyCategory, EquityCapital,
    StakeholderBook,
)
from accounting.models_ledger import JournalEntry, JournalLine
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class CapitalPaidInGoods(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.book = Book.objects.create(name="Almaty", base_currency=self.usd)
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("0.00"))
        user = get_user_model().objects.create_superuser(username="owner_g", password="pw")
        self.member = user.member
        StakeholderBook.objects.create(member=self.member, book=self.book)
        self.client.force_login(user)
        self.shelves = Warehouse.objects.create(name="Almaty", accounting_book=self.book)
        product = WarehouseProduct.objects.create(
            warehouse=self.shelves, name="Duvet set", sku="D-1", quantity=Decimal("25"))
        self.item = WarehouseProductItem.objects.create(
            product=product, quantity=Decimal("25"), quantity_remaining=Decimal("25"),
            status="in_stock", unit_cost_base=Decimal("44.00"))

    def add(self, **over):
        data = {"book": self.book.pk, "member": self.member.pk,
                "date_invested": "2026-09-14", "paid_in": "goods",
                "warehouse": self.shelves.pk}
        data.update(over)
        return self.client.post(
            reverse("accounting:add_equity_capital", kwargs={"pk": self.book.pk}),
            data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def ledger(self, code):
        rows = JournalLine.objects.filter(entry__book=self.book, account__code=code)
        return sum((r.debit - r.credit for r in rows), Decimal("0"))

    def url(self, name, capital):
        return reverse(f"accounting:{name}",
                       kwargs={"pk": self.book.pk, "source_pk": capital.pk})

    def test_the_goods_on_the_shelf_become_the_owners_capital(self):
        response = self.add()
        self.assertEqual(response.status_code, 200, response.content)
        capital = EquityCapital.objects.get()
        # The amount is the shelves', not something typed: 25 x 44.
        self.assertEqual(capital.amount, Decimal("1100.00"))
        self.assertEqual(capital.currency, self.usd)
        self.assertTrue(capital.in_goods)
        self.assertIsNone(capital.cash_account)
        self.assertEqual(self.ledger("1300"), Decimal("1100"))
        self.assertEqual(self.ledger("3000"), Decimal("-1100"))
        entry = JournalEntry.objects.get(book=self.book)
        self.assertEqual(entry.source_id, capital.pk)
        self.assertEqual(entry.source_type, ContentType.objects.get_for_model(EquityCapital))

    def test_no_cash_moves(self):
        self.add()
        self.assertFalse(CashTransactionEntry.objects.exists())
        self.cash.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal("0.00"))
        self.assertEqual(self.ledger("1000"), Decimal("0"))

    def test_the_same_shelves_cannot_be_capital_twice(self):
        self.add()
        response = self.add()
        self.assertEqual(response.status_code, 400)
        self.assertIn("already in the ledger", response.content.decode())
        self.assertEqual(EquityCapital.objects.count(), 1)
        self.assertEqual(self.ledger("1300"), Decimal("1100"))

    def test_an_empty_warehouse_is_nothing_to_contribute(self):
        self.item.delete()
        response = self.add()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EquityCapital.objects.exists())

    def test_another_books_warehouse_is_not_offered(self):
        other = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        theirs = Warehouse.objects.create(name="Laleli", accounting_book=other)
        response = self.add(warehouse=theirs.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EquityCapital.objects.exists())

    def test_its_page_says_goods_and_offers_no_edit(self):
        self.add()
        capital = EquityCapital.objects.get()
        page = self.client.get(self.url("equity_capital_detail", capital))
        self.assertContains(page, "Goods")
        self.assertContains(page, "no cash moved")
        self.assertNotContains(page, self.url("edit_equity_capital", capital))
        response = self.client.get(self.url("edit_equity_capital", capital))
        self.assertEqual(response.status_code, 302)

    def test_deleting_it_takes_the_entry_and_leaves_the_goods(self):
        self.add()
        capital = EquityCapital.objects.get()
        self.client.post(self.url("delete_equity_capital", capital))
        self.assertFalse(EquityCapital.objects.exists())
        self.assertFalse(JournalEntry.objects.filter(book=self.book).exists())
        self.assertTrue(WarehouseProductItem.objects.filter(pk=self.item.pk).exists())

    def test_a_cash_deposit_is_what_it_always_was(self):
        # Posted as an open tab from before the choice existed would post
        # it: no `paid_in` at all.
        response = self.add(paid_in="", warehouse="", cash_account=self.cash.pk,
                            amount="600.00")
        self.assertEqual(response.status_code, 200, response.content)
        capital = EquityCapital.objects.get()
        self.assertFalse(capital.in_goods)
        self.cash.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal("600.00"))
        self.assertEqual(self.ledger("3000"), Decimal("-600"))

    def test_a_cash_deposit_still_needs_its_account(self):
        response = self.add(paid_in="cash", warehouse="", amount="600.00")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EquityCapital.objects.exists())
