"""A split order's halves read the same, always.

Two orders in the books, one order on screen — so what is about the request
itself (its date, notes, addresses, the customer, the cargo it goes out in)
is one thing, and a change to it on either half is a change to both, from
whichever page or path made it. Each half keeps its own number, account and
invoice.

Run with:
    python manage.py test operating.tests.test_split_orders_alike
"""
import json
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import Order, Warehouse, WarehouseProduct, WarehouseProductItem


class SplitHalvesStayAlike(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.anna = Contact.objects.create(name="Anna Lugansk")
        group = uuid.uuid4()
        self.a = self._half(self.laleli, "ORD-A", self.anna, group)
        self.b = self._half(self.ergene, "ORD-B", self.anna, group)

        User = get_user_model()
        self.user = User.objects.create_superuser("alike", "a@t.com", "pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _account(self, book, contact):
        return CurrentAccount.objects.get_or_create(
            book=book, contact=contact,
            defaults={"code": f"C-{book.pk}-{contact.pk}", "name": contact.name,
                      "type": "customer", "default_currency": self.usd})[0]

    def _half(self, book, number, contact, group):
        return Order.objects.create(order_number=number, contact=contact, currency=self.usd,
                                    current_account=self._account(book, contact),
                                    split_group=group)

    def test_a_change_on_one_half_is_on_the_other(self):
        self.a.notes = "Deliver after 14:00"
        self.a.delivery_city = "Lugansk"
        self.a.order_date = date(2026, 10, 26)
        self.a.save()
        self.b.refresh_from_db()
        self.assertEqual((self.b.notes, self.b.delivery_city, self.b.order_date),
                         ("Deliver after 14:00", "Lugansk", date(2026, 10, 26)))

    def test_the_cargo_it_goes_out_in_is_one(self):
        self.b.carrier = "aras"
        self.b.tracking_number = "TRK-1"
        self.b.save(update_fields=["carrier", "tracking_number"])
        self.a.refresh_from_db()
        self.assertEqual((self.a.carrier, self.a.tracking_number), ("aras", "TRK-1"))

    def test_only_what_the_save_changed_is_passed_on(self):
        """A half saved from a copy loaded before the other half changed
        something does not undo that change."""
        stale_b = Order.objects.get(pk=self.b.pk)
        self.a.internal_notes = "Packed by Ali"
        self.a.save(update_fields=["internal_notes"])
        stale_b.tracking_number = "TRK-2"
        stale_b.save(update_fields=["tracking_number"])
        self.a.refresh_from_db()
        self.assertEqual((self.a.internal_notes, self.a.tracking_number), ("Packed by Ali", "TRK-2"))

    def test_each_half_keeps_its_own_number_and_account(self):
        self.a.notes = "x"
        self.a.save()
        self.b.refresh_from_db()
        self.assertEqual(self.b.order_number, "ORD-B")
        self.assertEqual(self.b.current_account.book_id, self.ergene.pk)

    def test_the_customer_changes_on_every_half_each_in_its_own_book(self):
        oleg = Contact.objects.create(name="Oleg Motuzenko")
        resp = self.client.post(reverse("operating:order_detail", kwargs={"pk": self.a.pk}),
                                {"action": "update_customer", "customer_type": "contact",
                                 "customer_pk": oleg.pk})
        self.assertEqual(resp.status_code, 200)
        for half, book in ((self.a, self.laleli), (self.b, self.ergene)):
            half.refresh_from_db()
            self.assertEqual(half.contact_id, oleg.pk)
            self.assertEqual((half.current_account.contact_id, half.current_account.book_id),
                             (oleg.pk, book.pk))

    def test_a_customer_whose_account_cannot_take_the_currency_is_refused(self):
        eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        oleg = Contact.objects.create(name="Oleg Motuzenko")
        account = self._account(self.ergene, oleg)
        account.default_currency = eur
        account.save()
        with patch.object(CurrentAccount, "currency_is_locked", True):
            resp = self.client.post(
                reverse("operating:order_detail", kwargs={"pk": self.a.pk}),
                {"action": "update_customer", "customer_type": "contact", "customer_pk": oleg.pk})
        self.assertEqual(resp.status_code, 400)
        for half in (self.a, self.b):
            half.refresh_from_db()
            self.assertEqual(half.contact_id, self.anna.pk)


class AHalfAddedLaterIsTheSameOrder(TestCase):
    """A half an edit adds, on a later day, to an order already being
    packed: it takes the order's date, notes and status, not today's and
    "open"."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Oleg Motuzenko")
        account = CurrentAccount.objects.create(
            book=self.laleli, code="C-1", name="Oleg", type="customer",
            contact=self.customer, default_currency=usd)
        self.order = Order.objects.create(
            order_number="ORD-L", current_account=account, contact=self.customer,
            order_date=date(2026, 10, 24), internal_notes="Ships with Supertekstil",
            order_status="packaging")
        parent = Product.objects.create(sku="K24777", title="Tul")
        variant = ProductVariant.objects.create(product=parent, variant_sku="K24777.B02")
        wh = Warehouse.objects.create(name="Ergene depo", accounting_book=self.ergene)
        wp = WarehouseProduct.objects.create(warehouse=wh, name="Tul", sku="K24777.B02",
                                             quantity=Decimal("50"), catalog_variant=variant)
        WarehouseProductItem.objects.create(product=wp, quantity=Decimal("50"),
                                            quantity_remaining=Decimal("50"),
                                            barcode="E-0001", status="in_stock")
        User = get_user_model()
        user = User.objects.create_superuser("later", "l@t.com", "pw")
        user.member.books.add(self.laleli, self.ergene)
        user.member.default_book = self.laleli
        user.member.save()
        self.client.force_login(user)

    @patch("operating.signals.notify_customer_of_status")
    def test_it_takes_the_order_s_date_notes_and_status(self, notify):
        self.client.post(reverse("operating:edit_order", kwargs={"pk": self.order.pk}), {
            "customer_type": "contact", "customer_pk": self.customer.pk,
            "book": self.laleli.pk, "notes": "", "internal_notes": "Ships with Supertekstil",
            "deleted_items": "[]",
            "product_json_input": json.dumps([{
                "item_no": 1, "product": {"sku": "K24777.B02", "variant": True},
                "description": "", "quantity": 20, "outsourced": 0, "price": 2,
                "is_custom_curtain": False,
                "rolls": [{"barcode": "E-0001", "quantity": 20, "book": self.ergene.pk}]}]),
        })
        added = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual((added.order_date, added.internal_notes, added.order_status),
                         (date(2026, 10, 24), "Ships with Supertekstil", "packaging"))
        # The customer already knows the order is being packed.
        notify.assert_not_called()
