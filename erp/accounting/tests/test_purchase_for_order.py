# to run this test, use the command:
# python manage.py test accounting.tests.test_purchase_for_order

"""A purchase bought for a customer.

A client asks for something the shelves don't have. The purchase is written
with the customer and a sale price per variant, and saving it creates the
customer's order too. Receiving the purchase reserves the arriving rolls for
that order — up to what it still needs — so they can't be packed into
another one first.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import (
    Order, OrderItem, OrderStockReservation, Warehouse, WarehouseProduct,
    WarehouseProductItem,
)


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class PurchaseForCustomerTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Ergene")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.other_wh = Warehouse.objects.create(name="Ergene depo",
                                                 accounting_book=self.other_book)
        self.customer = Contact.objects.create(name="Oleg Motuzenko")

        self.admin = get_user_model().objects.create_superuser(
            username="firat_po", password="pw", email="a@b.c")
        self.client.force_login(self.admin)

    def _plan(self, variants=None, customer=True, warehouse=None, product=None):
        main = ({"mode": "existing", "id": product.pk, "sku": product.sku}
                if product else {"mode": "new", "name": "K24644", "sku": "K24644"})
        return {
            "warehouse_id": (warehouse or self.wh).pk,
            "current_account_id": self.supplier.pk,
            "customer": ({"type": "contact", "pk": self.customer.pk} if customer else None),
            "unit": "mt",
            "date": "2026-09-17",
            "products": [{
                "main_product": main,
                "has_variants": True,
                "variants": variants if variants is not None else [self._variant()],
            }],
        }

    @staticmethod
    def _variant(name="G07", sku="K24644.G07", tops=(30, 25), sale="5.00"):
        return {"name": name, "sku": sku, "price": "3.50", "currency": "USD",
                "sale_price": sale,
                "tops": [{"qty": q, "barcode": ""} for q in tops]}

    def _save(self, plan, pk=None):
        url = (reverse("accounts:purchase_order_update", args=[pk]) if pk
               else reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}))
        return self.client.post(url, data=json.dumps(plan), content_type="application/json")

    def _confirm(self, inv_id):
        return self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))

    def _held(self, order):
        return list(OrderStockReservation.objects.filter(order=order)
                    .order_by("stock_item_id").values_list("quantity", flat=True))

    # ── Saving creates the customer's order ─────────────────────────
    def test_saving_creates_the_customers_order(self):
        r = self._save(self._plan())
        self.assertEqual(r.status_code, 200, r.content)
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        order = inv.for_order
        self.assertIsNotNone(order)
        self.assertEqual(order.contact, self.customer)
        self.assertEqual(order.order_status, "pending")
        self.assertEqual(order.current_account.book, self.wh.accounting_book)

        [line] = order.items.all()
        self.assertEqual(line.product_variant.variant_sku, "K24644.G07")
        self.assertEqual(line.quantity, Decimal("55.00"))       # 30 + 25
        self.assertEqual(line.price, Decimal("5.00"))

        # The product is in the catalog now; the stock and the debt are not.
        self.assertEqual(Product.objects.get().sku, "K24644")
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertIsNone(inv.posted_movement)
        # The saved plan names what was created, so receiving finds it.
        card = inv.intake_plan["products"][0]
        self.assertEqual(card["main_product"]["mode"], "existing")
        self.assertEqual(card["main_product"]["id"], line.product_id)

    def test_an_auto_sku_is_fixed_at_save(self):
        r = self._save(self._plan(variants=[self._variant(sku="")]))
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        sku = inv.intake_plan["products"][0]["variants"][0]["sku"]
        self.assertTrue(sku)
        self.assertEqual(inv.for_order.items.get().product_variant.variant_sku, sku)

        self._confirm(inv.pk)
        self.assertEqual(ProductVariant.objects.count(), 1)
        self.assertEqual(WarehouseProduct.objects.get().sku, sku)

    def test_an_existing_product_can_be_bought_for_a_customer(self):
        product = Product.objects.create(title="Krep", sku="KRP1", featured=False)
        variant = ProductVariant.objects.create(product=product, variant_sku="KRP1.G07")
        r = self._save(self._plan(product=product,
                                  variants=[self._variant(sku="KRP1.G07")]))
        self.assertEqual(r.status_code, 200, r.content)
        order = Invoice.objects.get(pk=r.json()["invoice_id"]).for_order
        self.assertEqual(order.items.get().product_variant, variant)
        self.assertEqual(ProductVariant.objects.count(), 1)

    def test_a_purchase_for_stock_still_leaves_no_trace(self):
        r = self._save(self._plan(customer=False))
        self.assertIsNone(Invoice.objects.get(pk=r.json()["invoice_id"]).for_order)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Product.objects.exists())

    def test_an_unknown_customer_saves_nothing(self):
        plan = self._plan()
        plan["customer"]["pk"] = 999999
        r = self._save(plan)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Product.objects.exists())

    # ── Editing the draft keeps the order in step ───────────────────
    def test_editing_the_draft_updates_the_order(self):
        inv_id = self._save(self._plan(variants=[
            self._variant(), self._variant(name="G08", sku="K24644.G08", tops=(10,)),
        ])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        by_hand = OrderItem.objects.create(
            order=order, product=Product.objects.get(), quantity=Decimal("1"),
            price=Decimal("9"))

        # Reopened, the draft names the product it created as an existing one.
        plan = self._plan(variants=[self._variant(tops=(40,), sale="6.00")], customer=False,
                          product=Product.objects.get())
        r = self._save(plan, pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())

        self.assertEqual(Order.objects.count(), 1)
        lines = {it.product_variant.variant_sku if it.product_variant_id else None: it
                 for it in Order.objects.get().items.select_related("product_variant")}
        self.assertEqual(set(lines), {"K24644.G07", None})      # G08 dropped, hand line kept
        self.assertEqual(lines["K24644.G07"].quantity, Decimal("40.00"))
        self.assertEqual(lines["K24644.G07"].price, Decimal("6.00"))
        self.assertEqual(lines[None].pk, by_hand.pk)

    def test_an_order_being_packed_is_left_alone(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        Order.objects.update(order_status="packaging")
        r = self._save(self._plan(variants=[self._variant(tops=(5,))], customer=False,
                                  product=Product.objects.get()), pk=inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(OrderItem.objects.get().quantity, Decimal("55.00"))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "already being packed")

    def test_moving_the_draft_to_another_books_warehouse_is_refused(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self._save(self._plan(warehouse=self.other_wh, customer=False), pk=inv_id)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=inv_id).intake_warehouse, self.wh)

    # ── Receiving holds the rolls ───────────────────────────────────
    def test_confirming_holds_the_rolls_for_the_order(self):
        inv_id = self._save(self._plan(variants=[self._variant(tops=(30, 25))])).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        # The customer only wants 40 of the 55 coming in.
        order.items.update(quantity=Decimal("40"))

        r = self._confirm(inv_id)
        self.assertTrue(r.json()["success"], r.json())
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "2 rolls reserved for order %s." % order.order_number)

        self.assertEqual(self._held(order), [Decimal("30.00"), Decimal("10.00")])
        # Same variant the order points at — nothing minted twice.
        self.assertEqual(ProductVariant.objects.count(), 1)
        # Held, not cut.
        self.assertEqual(
            sorted(WarehouseProductItem.objects.values_list("quantity_remaining", flat=True)),
            [Decimal("25.00"), Decimal("30.00")])
        # The debt is posted — for_order is not the sales `order` link.
        inv = Invoice.objects.get(pk=inv_id)
        self.assertIsNone(inv.order)
        self.assertIsNotNone(inv.posted_movement)

    def test_rolls_the_order_does_not_need_stay_free(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        OrderItem.objects.filter(order=order).update(outsourced_quantity=Decimal("55"))
        r = self._confirm(inv_id)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(self._held(order), [])
        self.assertTrue(any("Nothing was reserved" in w for w in r.json()["warnings"]))

    # ── Around it ───────────────────────────────────────────────────
    # ── The sale price is in the customer's currency ────────────────
    def _currency(self, customer_type, pk, warehouse=None):
        """The currency and account the endpoint names, which is what this
        screen asks it. It answers more than that now — a symbol, and
        whether it is the book's own currency, both for the order form's
        warning — so this picks out the two keys these tests are about."""
        r = self.client.get(
            reverse("operating:warehouse_customer_currency", args=[(warehouse or self.wh).pk]),
            {"type": customer_type, "pk": pk})
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        return {"currency": d["currency"], "account": d["account"]}

    def test_a_customer_with_an_account_prices_in_its_currency(self):
        try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="₺")
        CurrentAccount.objects.create(book=self.book, code="C-OLG", name="Oleg",
                                      type="customer", contact=self.customer,
                                      default_currency=try_)
        self.assertEqual(self._currency("contact", self.customer.pk),
                         {"currency": "TRY", "account": "Oleg"})
        # In a book where they have no account yet, the one the order
        # would open is in the default currency.
        self.assertEqual(self._currency("contact", self.customer.pk, self.other_wh),
                         {"currency": "USD", "account": None})

    def test_a_contact_at_a_company_prices_in_the_companys_currency(self):
        """The order bills the company's account, not the person's."""
        from crm.models import Company
        eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        company = Company.objects.create(name="Motuzenko Ltd")
        self.customer.company = company
        self.customer.save()
        CurrentAccount.objects.create(book=self.book, code="C-MTZ", name="Motuzenko Ltd",
                                      type="customer", company=company, default_currency=eur)
        self.assertEqual(self._currency("contact", self.customer.pk)["currency"], "EUR")
        self.assertEqual(self._currency("company", company.pk)["currency"], "EUR")

    def test_an_unknown_customer_has_no_currency(self):
        r = self.client.get(reverse("operating:warehouse_customer_currency", args=[self.wh.pk]),
                            {"type": "contact", "pk": 999999})
        self.assertEqual(r.status_code, 404)

    def test_a_reopened_order_states_its_orders_currency(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertEqual(r.context["for_order_currency"], "USD")

    def test_the_order_page_lists_its_purchases(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        self.assertEqual(r.status_code, 200)
        [p] = r.context["supplier_purchases"]
        self.assertEqual(p.pk, inv_id)
        self.assertContains(r, "Awaiting delivery")

    def test_the_form_reopens_with_the_customer(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[inv_id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["for_order"], Invoice.objects.get(pk=inv_id).for_order)
        self.assertContains(r, "Oleg Motuzenko")
        self.assertEqual(r.context["intake_plan"]["products"][0]["variants"][0]["sale_price"],
                         "5.00")

    def test_cancelling_the_draft_says_the_order_is_still_open(self):
        inv_id = self._save(self._plan()).json()["invoice_id"]
        order = Invoice.objects.get(pk=inv_id).for_order
        r = self.client.post(reverse("accounts:purchase_cancel", args=[inv_id]))
        self.assertTrue(r.json()["success"], r.json())
        order.refresh_from_db()
        self.assertEqual(order.order_status, "pending")
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[inv_id]))
        self.assertContains(page, "is still open")
