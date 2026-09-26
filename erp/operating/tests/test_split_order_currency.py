"""A split order is in one currency.

Each book holds its own account for the same customer, and each account
has its own currency, so the halves of an order split across books could
end up priced in two. They must not: the halves are one request, shown and
totalled together. Every half is in the lead order's currency — the
account in the other book is made in it, or switched to it while it has
no transactions — and a split whose other account is already trading in
another currency is refused before anything is written.

Run with:
    python manage.py test operating.tests.test_split_order_currency
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import Order, Warehouse, WarehouseProduct, WarehouseProductItem

LALELI_SKU = "K24644.G07"
ERGENE_SKU = "K24777.B02"


class SplitCurrencyBase(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Anna Lugansk")
        self._stock(self.laleli, LALELI_SKU, "Krep", "L-0001")
        self._stock(self.ergene, ERGENE_SKU, "Tul", "E-0001")

        user = get_user_model().objects.create_superuser("firat", "f@t.com", "pw")
        user.member.books.add(self.laleli, self.ergene)
        user.member.default_book = self.laleli
        user.member.save()
        self.client.force_login(user)

    def _stock(self, book, sku, title, barcode):
        parent, _ = Product.objects.get_or_create(
            sku=sku.split(".")[0], defaults={"title": title})
        variant, _ = ProductVariant.objects.get_or_create(product=parent, variant_sku=sku)
        wh, _ = Warehouse.objects.get_or_create(
            name=f"{book.name} depo", defaults={"accounting_book": book})
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name=title, sku=sku, quantity=Decimal("50"), catalog_variant=variant)
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _line(self, sku, book, barcode):
        return {
            "item_no": 1, "product": {"sku": sku, "variant": True},
            "description": "", "quantity": 10, "outsourced": 0, "price": 2,
            "is_custom_curtain": False,
            "rolls": [{"barcode": barcode, "quantity": 10, "book": book.pk}],
        }

    def _both_lines(self):
        return [self._line(LALELI_SKU, self.laleli, "L-0001"),
                self._line(ERGENE_SKU, self.ergene, "E-0001")]

    def _account(self, book, currency, code):
        return CurrentAccount.objects.create(
            book=book, code=code, name=f"Anna ({book.name})", type="customer",
            contact=self.customer, default_currency=currency)

    def _trade(self, account):
        """Give an account a transaction, which locks its currency."""
        CurrentAccountMovement.objects.create(
            current_account=account, book=account.book, date="2026-09-01",
            amount=Decimal("10"), currency=account.default_currency,
            movement_type="opening", description="opening")


class AtCreate(SplitCurrencyBase):
    def _post(self):
        return self.client.post(reverse("operating:create_order"), {
            "customer_type": "contact", "customer_pk": self.customer.pk,
            "book": self.laleli.pk, "product_json_input": json.dumps(self._both_lines()),
        })

    def test_the_new_account_in_the_other_book_takes_the_lead_s_currency(self):
        self._account(self.laleli, self.eur, "L-1")
        self._post()
        self.assertEqual(Order.objects.count(), 2)
        ergene_account = CurrentAccount.objects.get(book=self.ergene, contact=self.customer)
        self.assertEqual(ergene_account.default_currency, self.eur)
        self.assertEqual({o.currency.code for o in Order.objects.all()}, {"EUR"})

    def test_an_unused_account_in_another_currency_is_switched(self):
        self._account(self.laleli, self.eur, "L-1")
        unused = self._account(self.ergene, self.usd, "E-1")
        self._post()
        unused.refresh_from_db()
        self.assertEqual(unused.default_currency, self.eur)
        self.assertEqual({o.currency.code for o in Order.objects.all()}, {"EUR"})

    def test_a_trading_account_in_another_currency_blocks_the_split(self):
        self._account(self.laleli, self.eur, "L-1")
        self._trade(self._account(self.ergene, self.usd, "E-1"))
        resp = self._post()
        self.assertEqual(Order.objects.count(), 0)   # nothing written
        said = " ".join(str(m) for m in get_messages(resp.wsgi_request))
        self.assertIn("must be in one currency", said)
        self.assertIn("Ergene Fabric", said)

    def test_no_lead_account_yet_follows_the_trading_one(self):
        """The customer trades in euros on Ergene and has no Laleli account
        yet: the split follows the euros instead of blocking for nothing."""
        self._trade(self._account(self.ergene, self.eur, "E-1"))
        self._post()
        self.assertEqual(Order.objects.count(), 2)
        laleli_account = CurrentAccount.objects.get(book=self.laleli, contact=self.customer)
        self.assertEqual(laleli_account.default_currency, self.eur)
        self.assertEqual({o.currency.code for o in Order.objects.all()}, {"EUR"})


class AtEdit(SplitCurrencyBase):
    def setUp(self):
        super().setUp()
        self.lead_account = self._account(self.laleli, self.eur, "L-1")
        self.order = Order.objects.create(
            current_account=self.lead_account, contact=self.customer, currency=self.eur)

    def _save(self):
        return self.client.post(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}), {
                "customer_type": "contact", "customer_pk": self.customer.pk,
                "book": self.laleli.pk, "notes": "",
                "product_json_input": json.dumps(self._both_lines()),
                "deleted_items": "[]",
            })

    def test_the_spun_off_half_is_in_the_edited_order_s_currency(self):
        """It used to be left with no currency at all, read as dollars."""
        self._save()
        sibling = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual(sibling.currency, self.eur)
        self.assertEqual(sibling.current_account.default_currency, self.eur)

    def test_a_trading_account_in_another_currency_blocks_the_edit(self):
        self._trade(self._account(self.ergene, self.usd, "E-1"))
        resp = self._save()
        said = " ".join(str(m) for m in get_messages(resp.wsgi_request))
        self.assertIn("must be in one currency", said)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.order.items.count(), 0)   # rolled back whole

    def test_the_edited_half_stays_on_its_own_book_s_account(self):
        """An editor whose default book is the OTHER one must not move the
        order onto an account there."""
        member = get_user_model().objects.get(username="firat").member
        member.default_book = self.ergene
        member.save()
        self._save()
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_account, self.lead_account)
