"""A company or contact we buy from shows what we bought, on its own page.

The CRM Supplier record was retired (CR14, 2026-11-17): we buy from it →
supplier, it buys from us → customer, both → both. So the page shows
Purchase history when its accounts have purchases, Order history when they
have orders, and both for both — not by the kind of record it is.

Run with:
    scripts/test_local.sh crm.tests.test_purchase_history_card
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from crm.models import Company, Contact


class PurchaseHistoryCard(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene")
        self.client.force_login(get_user_model().objects.create_superuser(
            username="ph", password="pw", email="p@h.t"))

    def _account(self, **crm):
        return CurrentAccount.objects.create(book=self.book, code=f"A-{len(crm)}{list(crm.values())[0].pk}",
                                             name=str(list(crm.values())[0]), type="supplier",
                                             default_currency=self.usd, **crm)

    def _purchase(self, account, number, status="ordered"):
        return Invoice.objects.create(
            current_account=account, book=self.book, series="PUR", number=number,
            type="purchase", status=status, date=date(2026, 11, 16), due_date=date(2026, 12, 16),
            currency=self.usd, total=Decimal("155.00"))

    def test_a_company_we_buy_from_shows_its_purchases_not_an_empty_order_card(self):
        hakan = Company.objects.create(name="Hakan Atölye")
        account = self._account(company=hakan)
        self._purchase(account, "000214")
        self._purchase(account, "000215", status="cancelled")
        r = self.client.get(reverse("crm:company_detail", args=[hakan.pk]))
        self.assertContains(r, "Purchase history")
        self.assertContains(r, "000214")
        # Cancelled is not something we bought.
        self.assertNotContains(r, "000215")
        self.assertNotContains(r, "No orders yet for this company.")

    def test_a_contact_we_buy_from_shows_them_too(self):
        samira = Contact.objects.create(name="Samira")
        self._purchase(self._account(contact=samira), "000301")
        r = self.client.get(reverse("crm:contact_detail", args=[samira.pk]))
        self.assertContains(r, "Purchase history")
        self.assertContains(r, "000301")

    def test_a_customer_keeps_its_order_card_and_has_no_purchase_card(self):
        buyer = Company.objects.create(name="Steppe Home")
        r = self.client.get(reverse("crm:company_detail", args=[buyer.pk]))
        self.assertContains(r, "No orders yet for this company.")
        self.assertNotContains(r, "Purchase history")
