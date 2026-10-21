"""Who an order is charged to when its contact is filed under a company.

Fadime Akdas orders for Akdas Gardinen. Her orders went on the company's
account by a rule nobody saw, so her own page showed two orders and no
account. The rule stays the default — most people who order are buying
for their shop — but it is now a choice shown on the order ("Charge to"),
and the person can be picked instead. Every later re-resolve of the
account reads the choice, so none of them quietly puts it back.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from accounting.services_accounts import (
    existing_customer_account, get_or_create_current_account_for_order,
)
from crm.models import Company, Contact
from marketing.models import Product
from operating.models import Order


class ChargeToBase(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        Product.objects.create(title="Krep", sku="KRP", featured=False)
        user = get_user_model().objects.create_superuser("seller_charge", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.member = user.member
        self.client.force_login(user)

        self.company = Company.objects.create(name="Akdas Gardinen")
        self.fadime = Contact.objects.create(name="Fadime Akdas", company=self.company)

    def _create(self, contact, **extra):
        line = {"item_no": 1, "product": {"sku": "KRP", "variant": False},
                "description": "", "quantity": 10, "outsourced": 0,
                "price": 2, "is_custom_curtain": False, "rolls": []}
        data = {"customer_type": "contact", "customer_pk": contact.pk,
                "book": self.book.pk, "product_json_input": json.dumps([line])}
        data.update(extra)
        resp = self.client.post(reverse("operating:create_order"), data,
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertIn(resp.status_code, (200, 302), resp.content)
        return Order.objects.latest("pk")

    def _card(self, order, **data):
        return self.client.post(
            reverse("operating:order_customer_card", args=[order.pk]), data)


class TheOrderForm(ChargeToBase):
    def test_the_company_is_charged_by_default(self):
        order = self._create(self.fadime)
        self.assertFalse(order.charge_contact_personally)
        self.assertEqual(order.current_account.company, self.company)
        self.assertFalse(CurrentAccount.objects.filter(contact=self.fadime).exists())

    def test_picking_her_charges_her_own_account(self):
        order = self._create(self.fadime, charge_to="contact")
        self.assertTrue(order.charge_contact_personally)
        self.assertEqual(order.current_account.contact, self.fadime)
        self.assertFalse(CurrentAccount.objects.filter(company=self.company).exists())

    def test_the_choice_means_nothing_for_someone_with_no_company(self):
        walk_in = Contact.objects.create(name="Ayse Yilmaz")
        order = self._create(walk_in, charge_to="contact")
        self.assertFalse(order.charge_contact_personally)
        self.assertEqual(order.current_account.contact, walk_in)

    def test_the_form_offers_the_choice_only_on_a_new_order(self):
        page = self.client.get(reverse("operating:create_order"), {"book": self.book.pk})
        self.assertContains(page, 'id="co-charge-to"')


class TheCurrencyLookUp(ChargeToBase):
    """The form prices in the currency of the account the order will go
    on, so it has to follow the choice too."""

    def _facts(self, **extra):
        return self.client.get(reverse("operating:customer_currency"), {
            "book": self.book.pk, "type": "contact", "pk": self.fadime.pk, **extra}).json()

    def test_it_names_the_company_so_the_form_can_offer_the_choice(self):
        self.assertEqual(self._facts()["company"], "Akdas Gardinen")

    def test_it_follows_the_account_that_will_be_charged(self):
        eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        CurrentAccount.objects.create(book=self.book, company=self.company,
                                      name="Akdas Gardinen", default_currency=eur)
        self.assertEqual(self._facts()["currency"], "EUR")
        self.assertEqual(self._facts(personally="1")["currency"], "USD")

    def test_existing_customer_account_reads_the_choice(self):
        company_account = CurrentAccount.objects.create(
            book=self.book, company=self.company, name="Akdas Gardinen",
            default_currency=self.usd)
        own = CurrentAccount.objects.create(
            book=self.book, contact=self.fadime, name="Fadime Akdas",
            default_currency=self.usd)
        self.assertEqual(existing_customer_account(book=self.book, contact=self.fadime),
                         company_account)
        self.assertEqual(existing_customer_account(book=self.book, contact=self.fadime,
                                                   personally=True), own)


class TheCustomerCard(ChargeToBase):
    def test_the_card_shows_the_choice_for_a_contact_under_a_company(self):
        order = self._create(self.fadime)
        page = self.client.get(reverse("operating:order_customer_card", args=[order.pk]))
        self.assertContains(page, "Charge to")
        self.assertContains(page, "Fadime Akdas personally")

    def test_the_card_does_not_for_an_individual(self):
        order = self._create(Contact.objects.create(name="Ayse Yilmaz"))
        page = self.client.get(reverse("operating:order_customer_card", args=[order.pk]))
        self.assertNotContains(page, "Charge to")

    def test_switching_to_her_moves_the_order_onto_her_account(self):
        order = self._create(self.fadime)
        resp = self._card(order, action="charge_to", charge_to="contact")
        self.assertEqual(resp["HX-Refresh"], "true")
        order.refresh_from_db()
        self.assertTrue(order.charge_contact_personally)
        self.assertEqual(order.current_account.contact, self.fadime)

    def test_and_back_to_the_company(self):
        order = self._create(self.fadime, charge_to="contact")
        self._card(order, action="charge_to", charge_to="company")
        order.refresh_from_db()
        self.assertFalse(order.charge_contact_personally)
        self.assertEqual(order.current_account.company, self.company)

    def test_a_new_customer_starts_on_the_default_again(self):
        order = self._create(self.fadime, charge_to="contact")
        colleague = Contact.objects.create(name="Ali Akdas", company=self.company)
        self._card(order, action="switch", customer_type="contact", customer_pk=colleague.pk)
        order.refresh_from_db()
        self.assertFalse(order.charge_contact_personally)
        self.assertEqual(order.current_account.company, self.company)


class EveryReResolveKeepsTheChoice(ChargeToBase):
    def test_resolving_the_account_again_does_not_put_it_back_on_the_company(self):
        order = self._create(self.fadime, charge_to="contact")
        again = get_or_create_current_account_for_order(order, member=self.member,
                                                        book=self.book)
        self.assertEqual(again, order.current_account)
        self.assertEqual(again.contact, self.fadime)

    def test_an_edit_keeps_it_on_her(self):
        order = self._create(self.fadime, charge_to="contact")
        line = {"item_no": 1, "item_id": order.items.get().pk,
                "product": {"sku": "KRP", "variant": False},
                "description": "", "quantity": 12, "outsourced": 0,
                "price": 2, "is_custom_curtain": False, "rolls": []}
        self.client.post(reverse("operating:edit_order", kwargs={"pk": order.pk}),
                         {"customer_type": "contact", "customer_pk": self.fadime.pk,
                          "book": self.book.pk, "product_json_input": json.dumps([line])})
        order.refresh_from_db()
        self.assertEqual(order.items.get().quantity, 12)
        self.assertEqual(order.current_account.contact, self.fadime)
        self.assertFalse(CurrentAccount.objects.filter(company=self.company).exists())
