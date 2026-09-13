# to run this test, use the command:
# python manage.py test accounting.test_purchase_order_flow

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from authentication.models import Permission
from marketing.models import Product
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class PurchaseOrderFlowTest(TestCase):
    """Order → confirm. A saved order is a document and nothing else; only
    confirming it reaches the warehouse."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.current_account = CurrentAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

        self.admin = get_user_model().objects.create_superuser(
            username="firat_t", password="pw", email="a@b.c")
        self.granted = get_user_model().objects.create_user(username="mirzael_t", password="pw")
        perm, _ = Permission.objects.get_or_create(name="purchase_confirm")
        # A Member row is created for every user by a signal.
        self.granted.member.permissions.add(perm)
        self.plain = get_user_model().objects.create_user(username="cuma_t", password="pw")
        # The admin is a superuser and reaches every book implicitly; the
        # other two have to be assigned this one.
        self.granted.member.books.add(self.book)
        self.plain.member.books.add(self.book)

        self.client.force_login(self.admin)

    def _plan(self, qty_a=30, qty_b=25):
        return {
            "warehouse_id": self.wh.pk,
            "current_account_id": self.current_account.pk,
            "unit": "mt",
            "date": "2026-08-21",
            "delivery_date": "2026-09-01",
            "notes": "Kamyon sabah gelecek",
            "products": [{
                "main_product": {"mode": "new", "name": "K24644", "sku": "K24644"},
                "has_variants": True,
                "variants": [{
                    "name": "G07", "sku": "K24644.G07", "price": "3.50", "currency": "USD",
                    "tops": [{"qty": qty_a, "barcode": ""}, {"qty": qty_b, "barcode": ""}],
                }],
            }],
        }

    def _save_order(self, plan=None, pk=None):
        url = (reverse("accounts:purchase_order_update", args=[pk]) if pk
               else reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}))
        return self.client.post(url, data=json.dumps(plan or self._plan()),
                                content_type="application/json")

    # ── Saving an order ─────────────────────────────────────────────
    def test_saving_an_order_touches_nothing_but_its_own_document(self):
        r = self._save_order()
        self.assertEqual(r.status_code, 200, r.content)
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])

        self.assertEqual(inv.status, "draft")
        self.assertEqual(inv.intake_warehouse, self.wh)
        self.assertEqual(inv.total, Decimal("192.50"))          # 55 × 3.50
        self.assertEqual(inv.items.count(), 1)
        self.assertEqual(inv.notes, "Kamyon sabah gelecek")
        self.assertEqual(str(inv.delivery_date), "2026-09-01")

        # Nothing anywhere else.
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertFalse(Product.objects.exists())
        self.current_account.refresh_from_db()
        self.assertEqual(self.current_account.cached_balance, Decimal("0.00"))
        self.assertIsNone(inv.posted_movement)

    def test_an_order_stays_editable(self):
        inv_id = self._save_order().json()["invoice_id"]
        plan = self._plan(qty_a=10, qty_b=5)
        plan["products"][0]["variants"][0]["price"] = "4.00"
        r = self._save_order(plan, pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())

        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.total, Decimal("60.00"))           # 15 × 4.00
        self.assertEqual(inv.items.count(), 1)
        self.assertEqual(inv.number, r.json()["number"])         # same document

    def test_the_form_reopens_a_saved_order(self):
        inv_id = self._save_order().json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["order_invoice"].pk, inv_id)
        self.assertIsNone(r.context["edit_invoice"])            # not the locked mode
        self.assertEqual(r.context["intake_plan"]["products"][0]["main_product"]["sku"], "K24644")

    # ── Confirming ──────────────────────────────────────────────────
    def test_confirming_receives_the_goods(self):
        inv_id = self._save_order().json()["invoice_id"]
        r = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["success"], r.json())

        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.status, "issued")
        self.assertEqual(inv.total, Decimal("192.50"))
        self.assertIsNotNone(inv.posted_movement)               # the debt is posted now
        self.current_account.refresh_from_db()
        self.assertEqual(self.current_account.cached_balance, Decimal("-192.50"))

        # ...and the warehouse has it.
        wp = WarehouseProduct.objects.get(warehouse=self.wh)
        self.assertEqual(wp.sku, "K24644.G07")
        self.assertEqual(wp.quantity, Decimal("55.00"))
        self.assertEqual(WarehouseProductItem.objects.count(), 2)
        self.assertEqual(Product.objects.get().sku, "K24644")
        # Every stock item traces back to a line of THIS document — one invoice, not two.
        self.assertEqual(Invoice.objects.filter(type="purchase").count(), 1)
        for roll in WarehouseProductItem.objects.all():
            self.assertEqual(roll.purchase_invoice_item.invoice_id, inv_id)

    def test_confirming_twice_is_refused(self):
        inv_id = self._save_order().json()["invoice_id"]
        self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        r = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(WarehouseProductItem.objects.count(), 2)   # not doubled

    def test_a_confirmed_order_is_no_longer_editable_as_an_order(self):
        inv_id = self._save_order().json()["invoice_id"]
        self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        r = self._save_order(pk=inv_id)
        self.assertEqual(r.status_code, 400)
        r2 = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertIsNotNone(r2.context["edit_invoice"])            # edited against its rolls now
        self.assertIsNone(r2.context["order_invoice"])

    def test_a_failed_confirm_leaves_the_order_untouched(self):
        """The typed SKU clashes at confirm time — nothing may be written."""
        inv_id = self._save_order().json()["invoice_id"]
        Product.objects.create(title="Başka Ürün", sku="K24644", featured=False)

        r = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertEqual(r.status_code, 400)
        inv = Invoice.objects.get(pk=inv_id)
        self.assertEqual(inv.status, "draft")                    # still confirmable
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertIsNone(inv.posted_movement)

    # ── Who may confirm ─────────────────────────────────────────────
    def test_a_granted_member_may_confirm(self):
        inv_id = self._save_order().json()["invoice_id"]
        self.client.force_login(self.granted)
        r = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertTrue(r.json()["success"], r.json())

    def test_everyone_else_may_write_the_order_but_not_receive_it(self):
        self.client.force_login(self.plain)
        r = self._save_order()
        self.assertTrue(r.json()["success"], r.json())            # writing it: fine

        inv_id = r.json()["invoice_id"]
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertEqual(c.status_code, 403)
        self.assertFalse(WarehouseProductItem.objects.exists())

        form = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}))
        self.assertFalse(form.context["can_confirm"])

    # ── The printed document ────────────────────────────────────────
    def test_the_order_prints_as_an_order_and_then_as_a_receipt(self):
        inv_id = self._save_order().json()["invoice_id"]
        r = self.client.get(reverse("accounts:purchase_order_print", args=[inv_id]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_order"])
        self.assertContains(r, "Karven")
        self.assertContains(r, "Kamyon sabah gelecek")
        self.assertContains(r, "Fabrika")

        self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        r2 = self.client.get(reverse("accounts:purchase_order_print", args=[inv_id]))
        self.assertFalse(r2.context["is_order"])


class PurchaseListBookScopeTest(TestCase):
    """The purchases list shows ONE book's purchases.

    /accounting/books/5/purchases/ used to list every purchase invoice in
    the database, whichever book was named in the URL, and sum their
    totals into that book's figure — so Ergene's page showed Laleli's
    suppliers and Laleli's money.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.admin = get_user_model().objects.create_superuser(
            username="scope_admin", password="pw", email="s@b.c")
        self.client.force_login(self.admin)
        self.karven = self._purchase(self.laleli, "Karven", "600.00")

    def _purchase(self, book, supplier, total):
        current_account = CurrentAccount.objects.create(
            book=book, code=f"C-{supplier[:3].upper()}-{book.pk}", name=supplier,
            type="supplier", default_currency=self.usd)
        Invoice.objects.create(
            book=book, current_account=current_account, type="purchase", status="draft",
            date="2026-08-21", due_date="2026-09-21",
            currency=self.usd, total=Decimal(total))
        return current_account

    def _page(self, book):
        resp = self.client.get(
            reverse("accounts:purchase_order_list", kwargs={"book_id": book.pk}))
        self.assertEqual(resp.status_code, 200)
        return resp.context

    def test_a_book_with_no_purchases_of_its_own_shows_none(self):
        self.assertEqual(list(self._page(self.ergene)["invoices"]), [])

    def test_another_books_money_is_not_totalled_into_this_one(self):
        self.assertEqual(self._page(self.ergene)["total_sum"], 0)

    def test_the_owning_book_still_shows_its_own(self):
        ctx = self._page(self.laleli)
        self.assertEqual(len(ctx["invoices"]), 1)
        self.assertEqual(ctx["total_sum"], Decimal("600.00"))

    def test_the_supplier_filter_offers_only_this_books_suppliers(self):
        """A supplier the page can never show must not sit in its
        dropdown: picking one would return an empty list with no
        explanation."""
        self.assertEqual(
            [s["current_account__name"] for s in self._page(self.ergene)["suppliers"]], [])
        self.assertEqual(
            [s["current_account__name"] for s in self._page(self.laleli)["suppliers"]],
            ["Karven"])

    def test_each_book_sees_only_its_own_when_both_have_purchases(self):
        self._purchase(self.ergene, "Bursa Tekstil", "150.00")
        self.assertEqual(
            [i.current_account.name for i in self._page(self.ergene)["invoices"]],
            ["Bursa Tekstil"])
        self.assertEqual(self._page(self.ergene)["total_sum"], Decimal("150.00"))
        self.assertEqual(
            [i.current_account.name for i in self._page(self.laleli)["invoices"]], ["Karven"])
