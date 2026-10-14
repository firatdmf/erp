"""A retail order is paid in full at the counter, into a named cash account.

There is no reason for money to pile up on the shared Retail Sales
account: a walk-in customer pays there and then, and anyone who leaves
owing gets an account of their own. So the order form asks which cash
account the money went into — filled in for the person — and the order
cannot be made without one. The collection is tied to the order by key
(OrderPayment), never by text: the old automatic collection matched on
notes reading "ORD-<pk>" and took order 286's money twice.

When the order is edited or called off afterwards, the page says what
the counter took against what the order now bills, and the person decides
whether the difference changes hands. Nothing settles it on its own.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CurrentAccountSettings, Payment
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import (Order, OrderPayment, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

EAN = "8681910572867"


class PaidAtTheCounter(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.kzt = CurrencyCategory.objects.create(code="KZT", name="Kazakhstani Tenge", symbol="₸")
        self.book = Book.objects.create(name="Almaty", base_currency=self.usd)
        settings = CurrentAccountSettings.for_book(self.book)
        settings.default_currency = self.kzt
        settings.save()
        self.tenge = CashAccount.objects.create(book=self.book, name="Tenge", currency=self.kzt)
        self.dollars = CashAccount.objects.create(book=self.book, name="Kasa Dolar", currency=self.usd)
        shelves = Warehouse.objects.create(name="Almaty", accounting_book=self.book)
        sheet = Product.objects.create(title="Sheet", featured=False, unit="piece", pack_type="loose")
        variant = ProductVariant.objects.create(product=sheet, variant_sku=EAN, variant_barcode=EAN)
        row = WarehouseProduct.objects.create(
            warehouse=shelves, name="Sheet", sku=EAN, barcode=EAN,
            quantity=Decimal("5"), catalog_variant=variant)
        self.batch = WarehouseProductItem.objects.create(
            product=row, quantity=Decimal("5"), quantity_remaining=Decimal("5"), status="in_stock")
        user = get_user_model().objects.create_superuser("counter", "c@t.r", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def post(self, box=None, qty=2, price=10000, **extra):
        data = {
            "customer_type": "retail", "book": self.book.pk,
            "product_json_input": json.dumps([{
                "item_no": 1, "product": {"sku": EAN, "variant": True},
                "description": "", "quantity": qty, "outsourced": 0, "price": price,
                "is_custom_curtain": False,
                "rolls": [{"barcode": f"#{self.batch.pk}", "quantity": qty, "book": self.book.pk}],
            }]),
        }
        if box is not None:
            data["deposit_cash_account"] = box.pk
        data.update(extra)
        return self.client.post(reverse("operating:create_order"), data)

    # ── taking the order ────────────────────────────────────────
    def test_no_cash_account_no_order(self):
        self.post()
        self.assertFalse(Order.objects.exists())

    def test_a_cash_account_in_another_currency_will_not_do(self):
        self.post(self.dollars)
        self.assertFalse(Order.objects.exists())

    def test_the_whole_total_goes_into_the_cash_account(self):
        # What the form sent as an amount does not matter: retail pays it all.
        self.post(self.tenge, deposit_amount="1")
        order = Order.objects.get()
        link = OrderPayment.objects.get(order=order)
        pay = link.payment
        self.assertEqual((pay.type, pay.status, pay.cash_account, pay.currency),
                         ("collection", "confirmed", self.tenge, self.kzt))
        self.assertEqual(pay.amount, Decimal("20000.00"))
        self.assertIsNone(order.counter_gap())

    def test_the_sale_is_over_when_it_is_made(self):
        # Paid and handed over: completed at once, the stock gone, and the
        # Retail Sales account square — the payment never runs ahead.
        self.post(self.tenge)
        order = Order.objects.get()
        self.assertEqual(order.order_status, "shipped")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.quantity_remaining, Decimal("3"))
        counter = order.current_account
        counter.refresh_from_db()
        self.assertEqual(Decimal(str(counter.own_currency_balance() or 0)), Decimal("0"))

    def test_a_customer_s_order_is_not_completed_for_them(self):
        dana = Contact.objects.create(name="Dana Akhmet")
        self.post(self.tenge, customer_type="contact", customer_pk=dana.pk)
        self.assertNotEqual(Order.objects.get().order_status, "shipped")

    def test_a_deposit_on_a_customer_s_order_is_linked_too(self):
        dana = Contact.objects.create(name="Dana Akhmet")
        self.post(self.tenge, customer_type="contact", customer_pk=dana.pk,
                  deposit_received="1", deposit_amount="5000")
        order = Order.objects.get()
        self.assertEqual(OrderPayment.objects.get(order=order).payment.amount, Decimal("5000.00"))
        self.assertIsNone(order.counter_gap())          # not retail: nothing to settle

    # ── when it changes afterwards ──────────────────────────────
    def _made(self):
        self.post(self.tenge)
        return Order.objects.get()

    def test_an_edit_opens_a_gap_the_page_shows_and_a_person_settles(self):
        order = self._made()
        order.items.update(price=Decimal("9000"))
        self.assertEqual(order.counter_gap(),
                         (Decimal("20000.00"), Decimal("18000.00"), Decimal("-2000.00")))
        page = self.client.get(reverse("operating:order_detail", kwargs={"pk": order.pk}))
        self.assertContains(page, 'id="od-counter-gap"')
        self.assertContains(page, "Give it back")
        # Nothing has moved on its own.
        self.assertEqual(Payment.objects.count(), 1)
        self.client.post(reverse("operating:settle_counter", kwargs={"pk": order.pk}))
        refund = Payment.objects.get(type="refund_in")
        self.assertEqual((refund.amount, refund.cash_account, refund.status),
                         (Decimal("2000.00"), self.tenge, "confirmed"))
        self.assertIsNone(order.counter_gap())
        page = self.client.get(reverse("operating:order_detail", kwargs={"pk": order.pk}))
        self.assertNotContains(page, 'id="od-counter-gap"')

    def test_a_dearer_order_collects_the_rest(self):
        order = self._made()
        order.items.update(price=Decimal("11000"))
        self.client.post(reverse("operating:settle_counter", kwargs={"pk": order.pk}))
        more = Payment.objects.filter(type="collection").order_by("-pk").first()
        self.assertEqual((more.amount, more.cash_account), (Decimal("2000.00"), self.tenge))
        self.assertIsNone(order.counter_gap())

    def test_a_cancelled_sale_gives_it_all_back_when_asked(self):
        order = self._made()
        Order.objects.filter(pk=order.pk).update(order_status="cancelled")
        order.refresh_from_db()
        self.assertEqual(order.counter_gap()[2], Decimal("-20000.00"))
        self.client.post(reverse("operating:settle_counter", kwargs={"pk": order.pk}))
        self.assertEqual(order.counter_takings(), Decimal("0.00"))

    def test_an_older_retail_order_never_linked_says_nothing(self):
        order = self._made()
        OrderPayment.objects.filter(order=order).delete()
        order.items.update(price=Decimal("1"))
        self.assertIsNone(order.counter_gap())

    def test_the_form_offers_the_counter_payment(self):
        page = self.client.get(reverse("operating:create_order_page", kwargs={"book_id": self.book.pk}))
        html = page.content.decode()
        self.assertIn('id="co-counter-note"', html)
        self.assertIn('"currency": "KZT"', html)
