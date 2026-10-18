"""Stock handed from one book's warehouse to another's, at cost.

Ergene sends rolls to Laleli. Laleli gets a purchase at Ergene's cost and
the rolls on its shelves; Ergene is owed the same amount on the paired
inter-company account and its stock is down by what the rolls cost — no
sale, no profit, and nothing left standing in Inter-company Clearing.

Run with:
    python manage.py test operating.tests.test_stock_transfer
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, Invoice
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.models_ledger import JournalLine
from accounting.models_transfer import StockTransfer
from accounting.services_mirror import pair_accounts
from accounting.services_stock_transfer import (
    TransferError, transfer_stock, undo_stock_transfer,
)
from accounting.views_purchase import cancel_purchase_invoice
from marketing.models import Product, ProductVariant

from operating.models import (
    StockMovement, Warehouse, WarehouseProduct, WarehouseProductItem,
)

SKU = "K24644.G07"


class TransferBase(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.shop_side = CurrentAccount.objects.create(
            book=self.laleli, code="KARFF", name="DEMFIRAT KARVEN | ERGENE",
            type="intercompany", default_currency=self.usd)
        self.factory_side = CurrentAccount.objects.create(
            book=self.ergene, code="ACC-065", name="DEMFIRAT | LALELI",
            type="intercompany", default_currency=self.usd)
        pair_accounts(self.shop_side, self.factory_side)

        product = Product.objects.create(title="Krep", sku="K24644")
        self.variant = ProductVariant.objects.create(product=product, variant_sku=SKU)
        self.factory = Warehouse.objects.create(name="Ergene Fabrika", accounting_book=self.ergene)
        self.shop = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=self.laleli)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.factory, name="Krep", sku=SKU, quantity=Decimal("0"),
            cost_usd=Decimal("3.40"), catalog_variant=self.variant)
        # 62.37 m at 3.40 is 212.058: owed 212.06, carried at a fraction less.
        self.first = self.roll("E-0001", "62.37")
        self.second = self.roll("E-0002", "50")

        User = get_user_model()
        self.user = User.objects.create_superuser("firat", "f@t.com", "pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.client.force_login(self.user)

    def roll(self, barcode, meters, cost="3.40"):
        roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal(meters), quantity_remaining=Decimal(meters),
            barcode=barcode, status="in_stock", unit_cost_base=Decimal(cost))
        self.wp.quantity += Decimal(meters)
        self.wp.save(update_fields=["quantity"])
        return roll

    def send(self, *rolls, **kw):
        return transfer_stock(self.factory, self.shop, [r.pk for r in rolls or (self.first, self.second)],
                              user=self.user, member=self.user.member, **kw)

    def ledger(self, book, code):
        """Debits less credits on one account of one book."""
        totals = (JournalLine.objects.filter(entry__book=book, account__code=code)
                  .aggregate(d=Sum("debit"), c=Sum("credit")))
        return (totals["d"] or Decimal("0")) - (totals["c"] or Decimal("0"))

    def balance(self, account):
        account.refresh_from_db()
        return account.cached_balance


class TheReceivingBook(TransferBase):
    def test_it_gets_a_purchase_at_the_senders_cost(self):
        transfer = self.send()
        invoice = transfer.purchase
        self.assertEqual((invoice.type, invoice.status), ("purchase", "issued"))
        self.assertEqual(invoice.book, self.laleli)
        self.assertEqual(invoice.current_account, self.shop_side)
        # 112.37 m × 3.40 = 382.058
        self.assertEqual(invoice.total, Decimal("382.06"))
        self.assertEqual(self.balance(self.shop_side), Decimal("-382.06"))

    def test_the_rolls_stand_on_its_shelves_behind_that_purchase(self):
        transfer = self.send()
        target = WarehouseProduct.objects.get(warehouse=self.shop, sku=SKU)
        self.assertEqual(target.quantity, Decimal("112.37"))
        self.assertEqual(target.catalog_variant, self.variant)
        for roll in (self.first, self.second):
            roll.refresh_from_db()
            self.assertEqual(roll.product, target)
            self.assertEqual(roll.purchase_invoice_item.invoice, transfer.purchase)
        self.assertEqual(self.first.barcode, "E-0001")

    def test_its_stock_is_carried_at_what_the_rolls_cost(self):
        self.send()
        self.assertEqual(self.ledger(self.laleli, "1300"), Decimal("382.058"))
        self.assertEqual(self.ledger(self.laleli, "1200"), Decimal("-382.06"))

    def test_the_account_stays_inter_company(self):
        self.send()
        self.shop_side.refresh_from_db()
        self.assertEqual(self.shop_side.type, "intercompany")

    def test_rolls_at_two_costs_get_a_line_each(self):
        dearer = self.roll("E-0003", "10", cost="4.00")
        transfer = self.send(self.first, dearer)
        prices = sorted(transfer.purchase.items.values_list("unit_price", flat=True))
        self.assertEqual(prices, [Decimal("3.40"), Decimal("4.00")])


class TheSendingBook(TransferBase):
    def test_it_is_owed_the_same_amount(self):
        self.send()
        self.assertEqual(self.balance(self.factory_side), Decimal("382.06"))
        mirror = CurrentAccountMovement.objects.get(current_account=self.factory_side)
        self.assertEqual(mirror.movement_type, "intercompany")

    def test_the_rolls_leave_its_shelves(self):
        self.send()
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.quantity, Decimal("0"))
        self.assertFalse(self.wp.stock_items.exists())

    def test_its_stock_goes_down_by_what_the_rolls_cost(self):
        self.send()
        self.assertEqual(self.ledger(self.ergene, "1300"), Decimal("-382.058"))
        self.assertEqual(self.ledger(self.ergene, "1200"), Decimal("382.06"))

    def test_nothing_is_left_in_inter_company_clearing(self):
        self.send()
        self.assertEqual(self.ledger(self.ergene, "1950"), Decimal("0"))

    def test_no_sale_and_no_cost_of_sale_is_recorded(self):
        self.send()
        self.assertEqual(self.ledger(self.ergene, "4000"), Decimal("0"))
        self.assertEqual(self.ledger(self.ergene, "5000"), Decimal("0"))

    def test_the_two_books_owe_each_other_nothing_net(self):
        self.send()
        self.assertEqual(self.balance(self.shop_side) + self.balance(self.factory_side), Decimal("0"))

    def test_the_transfer_keeps_what_was_given_up(self):
        transfer = self.send()
        self.assertEqual(transfer.value, Decimal("382.058"))
        self.assertEqual(
            sorted(transfer.lines.values_list("barcode", "quantity", "unit_cost")),
            [("E-0001", Decimal("62.37"), Decimal("3.40")),
             ("E-0002", Decimal("50"), Decimal("3.40"))])

    def test_both_warehouses_show_the_move_in_their_history(self):
        transfer = self.send(self.first)
        out = StockMovement.objects.get(product=self.wp)
        self.assertEqual(out.quantity, Decimal("-62.37"))
        self.assertIn(transfer.number, out.reason)
        self.first.refresh_from_db()
        came = StockMovement.objects.get(product=self.first.product)
        self.assertEqual(came.quantity, Decimal("62.37"))


class WhatCannotGo(TransferBase):
    def refused(self, *rolls):
        with self.assertRaises(TransferError) as caught:
            self.send(*rolls)
        self.assertFalse(StockTransfer.objects.exists())
        self.assertFalse(Invoice.objects.exists())
        return caught.exception

    def test_a_roll_part_of_which_has_been_used(self):
        self.first.quantity_remaining = Decimal("40")
        self.first.save(update_fields=["quantity_remaining"])
        error = self.refused(self.first, self.second)
        self.assertEqual([b["barcode"] for b in error.blocked], ["E-0001"])
        self.second.refresh_from_db()
        self.assertEqual(self.second.product, self.wp)

    def test_a_roll_with_no_cost(self):
        self.wp.cost_usd = None
        self.wp.save(update_fields=["cost_usd"])
        self.first.unit_cost_base = None
        self.first.save(update_fields=["unit_cost_base"])
        self.assertEqual(len(self.refused(self.first).blocked), 1)

    def test_a_roll_that_is_in_another_warehouse(self):
        elsewhere = Warehouse.objects.create(name="Ready-made Shop", accounting_book=self.ergene)
        other = WarehouseProduct.objects.create(warehouse=elsewhere, name="Krep", sku=SKU)
        self.first.product = other
        self.first.save(update_fields=["product"])
        self.assertEqual(len(self.refused(self.first).blocked), 1)

    def test_books_with_no_paired_account(self):
        almaty = Book.objects.create(name="Almaty", base_currency=self.usd)
        depot = Warehouse.objects.create(name="Almaty", accounting_book=almaty)
        with self.assertRaises(TransferError):
            transfer_stock(self.factory, depot, [self.first.pk], user=self.user,
                           member=self.user.member)
        self.first.refresh_from_db()
        self.assertEqual(self.first.product, self.wp)

    def test_two_warehouses_of_the_same_book(self):
        elsewhere = Warehouse.objects.create(name="Ready-made Shop", accounting_book=self.ergene)
        with self.assertRaises(TransferError):
            transfer_stock(self.factory, elsewhere, [self.first.pk], user=self.user,
                           member=self.user.member)


class TakingItBack(TransferBase):
    def test_undo_puts_everything_back(self):
        transfer = self.send()
        undo_stock_transfer(transfer, user=self.user, member=self.user.member)

        for roll in (self.first, self.second):
            roll.refresh_from_db()
            self.assertEqual(roll.product, self.wp)
            self.assertIsNone(roll.purchase_invoice_item)
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.quantity, Decimal("112.37"))
        self.assertEqual(self.balance(self.shop_side), Decimal("0"))
        self.assertEqual(self.balance(self.factory_side), Decimal("0"))
        for book in (self.laleli, self.ergene):
            for code in ("1200", "1300", "1950", "4950", "5150"):
                self.assertEqual(self.ledger(book, code), Decimal("0"), (book.name, code))
        transfer.refresh_from_db()
        self.assertTrue(transfer.is_undone)
        self.assertEqual(transfer.purchase.status, "cancelled")

    def test_undo_is_refused_once_a_roll_has_been_used(self):
        transfer = self.send()
        self.first.refresh_from_db()
        self.first.quantity_remaining = Decimal("10")
        self.first.save(update_fields=["quantity_remaining"])
        with self.assertRaises(TransferError) as caught:
            undo_stock_transfer(transfer, user=self.user, member=self.user.member)
        self.assertEqual([b["barcode"] for b in caught.exception.blocked], ["E-0001"])
        self.assertEqual(self.balance(self.factory_side), Decimal("382.06"))

    def test_the_purchase_cannot_be_cancelled_on_its_own(self):
        """Cancelling a purchase deletes its rolls. These are Ergene's
        goods: they go back, not away."""
        transfer = self.send()
        with self.assertRaises(ValueError):
            cancel_purchase_invoice(transfer.purchase.pk, self.user)
        self.assertEqual(WarehouseProductItem.objects.count(), 2)
        self.assertEqual(self.balance(self.factory_side), Decimal("382.06"))

    def test_the_rolls_can_be_sent_again_after_an_undo(self):
        undo_stock_transfer(self.send(), user=self.user, member=self.user.member)
        again = self.send()
        self.assertEqual(self.balance(self.factory_side), Decimal("382.06"))
        self.assertEqual(self.ledger(self.ergene, "1950"), Decimal("0"))
        self.assertEqual(again.lines.count(), 2)


class ThePage(TransferBase):
    def url(self, name="stock_transfer_create", pk=None):
        return reverse(f"operating:{name}", args=[pk or self.factory.pk])

    def test_it_offers_the_other_books_warehouse(self):
        resp = self.client.get(self.url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([w.pk for w in resp.context["targets"]], [self.shop.pk])

    def test_a_scan_finds_the_roll_and_a_sku_finds_all_of_them(self):
        one = self.client.get(self.url("stock_transfer_find"), {"q": "e-0001"}).json()
        self.assertEqual([r["barcode"] for r in one["rolls"]], ["E-0001"])
        self.assertEqual(one["rolls"][0]["unit_cost"], 3.4)
        every = self.client.get(self.url("stock_transfer_find"), {"q": SKU}).json()
        self.assertEqual([r["barcode"] for r in every["rolls"]], ["E-0001", "E-0002"])

    def test_a_pasted_list_adds_every_roll_and_names_what_it_skipped(self):
        """One bad line must not lose the rest of the list."""
        elsewhere = Warehouse.objects.create(name="Ready-made Shop", accounting_book=self.ergene)
        other = WarehouseProduct.objects.create(warehouse=elsewhere, name="Krep", sku="OTHER")
        WarehouseProductItem.objects.create(
            product=other, quantity=Decimal("5"), quantity_remaining=Decimal("5"),
            barcode="R-0001", status="in_stock")
        resp = self.client.post(
            self.url("stock_transfer_find"),
            json.dumps({"codes": ["E-0002", "NOPE", "e-0001", "R-0001", "E-0002"]}),
            content_type="application/json").json()
        self.assertEqual([r["barcode"] for r in resp["rolls"]], ["E-0002", "E-0001"])
        self.assertEqual([s["code"] for s in resp["skipped"]], ["NOPE", "R-0001"])
        self.assertIn("Ready-made Shop", resp["skipped"][1]["why"])

    def test_a_roll_named_twice_in_a_list_is_added_once(self):
        resp = self.client.post(
            self.url("stock_transfer_find"), json.dumps({"codes": ["E-0001", SKU]}),
            content_type="application/json").json()
        self.assertEqual(sorted(r["barcode"] for r in resp["rolls"]), ["E-0001", "E-0002"])
        self.assertEqual(resp["skipped"], [])

    def test_sending_makes_the_transfer_and_opens_it(self):
        resp = self.client.post(self.url(), json.dumps({
            "to_warehouse": self.shop.pk, "roll_ids": [self.first.pk, self.second.pk],
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)
        transfer = StockTransfer.objects.get()
        self.assertEqual(resp.json()["url"],
                         reverse("operating:stock_transfer_detail", args=[transfer.pk]))
        page = self.client.get(resp.json()["url"])
        self.assertContains(page, transfer.number)
        self.assertContains(page, "E-0001")
        self.assertTrue(page.context["can_undo"])

    def test_a_blocked_roll_is_named(self):
        self.first.quantity_remaining = Decimal("40")
        self.first.save(update_fields=["quantity_remaining"])
        resp = self.client.post(self.url(), json.dumps({
            "to_warehouse": self.shop.pk, "roll_ids": [self.first.pk],
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["blocked"][0]["barcode"], "E-0001")

    def test_undo_from_the_page(self):
        transfer = self.send()
        resp = self.client.post(self.url("stock_transfer_undo", transfer.pk))
        self.assertEqual(resp.json(), {"success": True})
        transfer.refresh_from_db()
        self.assertTrue(transfer.is_undone)

    def test_someone_in_one_book_only_cannot_send_or_undo(self):
        transfer = self.send(self.second)
        clerk = get_user_model().objects.create_user("clerk", "c@t.com", "pw")
        clerk.member.books.add(self.ergene)
        self.client.force_login(clerk)
        # No warehouse to send to, and the post is refused all the same.
        self.assertEqual(self.client.get(self.url()).context["targets"], [])
        resp = self.client.post(self.url(), json.dumps({
            "to_warehouse": self.shop.pk, "roll_ids": [self.first.pk],
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.client.post(self.url("stock_transfer_undo", transfer.pk)).status_code, 404)
        # They may still read what their own book gave up.
        page = self.client.get(self.url("stock_transfer_detail", transfer.pk))
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context["can_undo"])

    def test_the_warehouse_page_links_to_it(self):
        resp = self.client.get(reverse("operating:warehouse_detail", args=[self.factory.pk]))
        self.assertContains(resp, self.url())
