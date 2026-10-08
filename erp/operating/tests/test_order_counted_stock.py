"""Goods sold by count are ordered by quantity, not item by item.

A roll of cloth has a barcode of its own, and an order names the rolls it
takes. A duvet set does not: the barcode printed on it is its VARIANT's,
the same on every set, and the sets are alike. So the stock entries of
such a product carry no barcode — and the order form, which named every
stock item by its barcode, could not pick them at all.

They now go by a key of their own (WarehouseProductItem.pick_key), the
form takes a quantity from the oldest stock, and a scan of the printed
barcode means "one more of these".
"""
import json
import shutil
import subprocess
import tempfile
import re
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from crm.models import Contact
from marketing.models import Product, ProductVariant
from operating.models import (Order, OrderStockReservation, Pack, Warehouse,
                              WarehouseProduct, WarehouseProductItem)

EAN = "8681910572867"
ROLL = "R-0001"


class CountedStock(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Almaty")
        self.shelves = Warehouse.objects.create(name="Almaty", accounting_book=self.book)
        self.customer = Contact.objects.create(name="Dana Akhmet")

        duvet = Product.objects.create(
            title="Duvet set", featured=False, unit="piece", pack_type="loose")
        self.variant = ProductVariant.objects.create(
            product=duvet, variant_sku=EAN, variant_barcode=EAN)
        self.duvets = WarehouseProduct.objects.create(
            warehouse=self.shelves, name="Duvet set", sku=EAN, barcode=EAN,
            quantity=Decimal("8"), catalog_variant=self.variant)
        # Two batches, neither with a barcode of its own. The first is older.
        self.old = WarehouseProductItem.objects.create(
            product=self.duvets, quantity=Decimal("3"),
            quantity_remaining=Decimal("3"), status="in_stock")
        self.new = WarehouseProductItem.objects.create(
            product=self.duvets, quantity=Decimal("5"),
            quantity_remaining=Decimal("5"), status="in_stock")

        cloth = Product.objects.create(title="Krep", sku="K1", featured=False)
        cloth_variant = ProductVariant.objects.create(product=cloth, variant_sku="K1.G1")
        self.cloth = WarehouseProduct.objects.create(
            warehouse=self.shelves, name="Krep", sku="K1.G1",
            quantity=Decimal("50"), catalog_variant=cloth_variant)
        self.roll = WarehouseProductItem.objects.create(
            product=self.cloth, quantity=Decimal("50"),
            quantity_remaining=Decimal("50"), barcode=ROLL, status="in_stock")

        user = get_user_model().objects.create_superuser("seller_c", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    # ── helpers ─────────────────────────────────────────────────
    def key(self, item):
        return f"#{item.pk}"

    def get(self, name, **params):
        return self.client.get(reverse(f"operating:{name}"), params)

    def line(self, picks, sku=EAN, **over):
        qty = sum(q for _k, q in picks)
        data = {
            "item_no": 1, "product": {"sku": sku, "variant": True},
            "description": "", "quantity": qty, "outsourced": 0, "price": 60,
            "is_custom_curtain": False,
            "rolls": [{"barcode": k, "quantity": q, "book": self.book.pk}
                      for k, q in picks],
        }
        data.update(over)
        return data

    def post(self, lines):
        return self.client.post(reverse("operating:create_order"), {
            "customer_type": "contact", "customer_pk": self.customer.pk,
            "book": self.book.pk, "product_json_input": json.dumps(lines)})

    def holds(self, order=None):
        qs = OrderStockReservation.objects.filter(consumed=False)
        if order is not None:
            qs = qs.filter(order=order)
        return {r.stock_item_id: r.quantity for r in qs}

    # ── a stock item's name ─────────────────────────────────────
    def test_a_batch_goes_by_its_id_and_a_roll_by_its_barcode(self):
        self.assertEqual(self.old.pick_key, self.key(self.old))
        self.assertEqual(self.roll.pick_key, ROLL)

    def test_which_products_are_sold_by_count(self):
        self.assertTrue(self.duvets.sold_by_count)
        self.assertFalse(self.cloth.sold_by_count)
        self.assertEqual(self.duvets.printed_barcode, EAN)

    # ── the pick list ───────────────────────────────────────────
    def test_the_list_offers_the_batches_oldest_first(self):
        data = self.get("order_create_roll_list", sku=EAN).json()
        self.assertTrue(data["counted"])
        self.assertEqual(data["printed_barcode"], EAN)
        self.assertEqual([r["barcode"] for r in data["rolls"]],
                         [self.key(self.old), self.key(self.new)])
        self.assertEqual([r["available"] for r in data["rolls"]], [3.0, 5.0])

    def test_cloth_is_listed_as_it_always_was(self):
        data = self.get("order_create_roll_list", sku="K1.G1").json()
        self.assertFalse(data["counted"])
        self.assertEqual([r["barcode"] for r in data["rolls"]], [ROLL])

    # ── the product search ──────────────────────────────────────
    def test_the_search_says_at_once_that_a_product_is_sold_by_count(self):
        """So the card is drawn in its own shape when the product is
        picked. Left to the stock list, it was drawn as a roll card first
        and changed a moment later."""
        def picks(query):
            body = self.client.get(reverse("operating:product_autocomplete"),
                                   {"product": query, "book": self.book.pk}).content.decode()
            return re.findall(r"selectProduct\(([^)]*)\)", body)
        duvet = picks("Duvet")
        self.assertEqual(len(duvet), 1, duvet)
        self.assertTrue(duvet[0].endswith(",true"), duvet[0])
        cloth = picks("Krep")
        self.assertEqual(len(cloth), 1, cloth)
        self.assertTrue(cloth[0].endswith(",false"), cloth[0])

    def test_the_edit_form_is_told_too(self):
        self.post([self.line([(self.key(self.old), 3)])])
        order = Order.objects.get()
        page = self.client.get(reverse("operating:edit_order", kwargs={"pk": order.pk}))
        self.assertContains(page, '"counted": true')

    # ── checking one item ───────────────────────────────────────
    def test_a_batch_is_found_by_its_key(self):
        data = self.get("order_create_barcode_check",
                        barcode=self.key(self.new), sku=EAN).json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["stock_item_id"], self.new.pk)
        self.assertEqual(data["key"], self.key(self.new))

    def test_the_printed_barcode_stands_for_the_oldest_batch(self):
        data = self.get("order_create_barcode_check", barcode=EAN, sku=EAN).json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["counted"])
        self.assertEqual(data["key"], self.key(self.old))

    def test_and_for_the_next_one_once_the_oldest_is_spoken_for(self):
        other = Order.objects.create(order_number="700")
        OrderStockReservation.objects.create(
            order=other, stock_item=self.old, warehouse_product=self.duvets,
            quantity=Decimal("3"))
        data = self.get("order_create_barcode_check", barcode=EAN, sku=EAN).json()
        self.assertEqual(data["key"], self.key(self.new))

    def test_a_printed_barcode_on_another_products_line_is_the_wrong_product(self):
        response = self.get("order_create_barcode_check", barcode=EAN, sku="K1.G1")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["kind"], "wrong_product")

    def test_a_roll_is_checked_as_it_always_was(self):
        data = self.get("order_create_barcode_check", barcode=ROLL, sku="K1.G1").json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["counted"])
        self.assertEqual(data["key"], ROLL)

    def test_an_unknown_code_is_still_not_found(self):
        response = self.get("order_create_barcode_check", barcode="NOPE", sku=EAN)
        self.assertEqual(response.status_code, 404)

    # ── the main scanner ────────────────────────────────────────
    def test_scanning_the_printed_barcode_names_the_product(self):
        data = self.get("order_create_barcode_resolve", barcode=EAN).json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["counted"])
        self.assertEqual(data["sku"], EAN)
        self.assertEqual(data["roll"]["barcode"], self.key(self.old))

    def test_scanning_a_roll_is_what_it_always_was(self):
        data = self.get("order_create_barcode_resolve", barcode=ROLL).json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["counted"])
        self.assertEqual(data["roll"]["barcode"], ROLL)

    def test_cloth_is_never_found_by_a_product_barcode(self):
        self.cloth.barcode = "4444444444444"
        self.cloth.save()
        response = self.get("order_create_barcode_resolve", barcode="4444444444444")
        self.assertEqual(response.status_code, 404)

    # ── saving an order ─────────────────────────────────────────
    def test_an_order_holds_the_batches_it_was_given(self):
        # Four duvets: the three of the old batch and one of the new.
        self.post([self.line([(self.key(self.old), 3), (self.key(self.new), 1)])])
        order = Order.objects.get()
        self.assertEqual(self.holds(order),
                         {self.old.pk: Decimal("3"), self.new.pk: Decimal("1")})
        self.assertEqual(order.items.get().quantity, Decimal("4"))

    def test_it_cannot_hold_more_than_a_batch_has(self):
        self.post([self.line([(self.key(self.old), 9)])])
        self.assertEqual(self.holds(), {self.old.pk: Decimal("3")})

    def test_editing_takes_fewer_and_lets_a_batch_go(self):
        self.post([self.line([(self.key(self.old), 3), (self.key(self.new), 1)])])
        order = Order.objects.get()
        item = order.items.get()
        response = self.client.post(
            reverse("operating:edit_order", kwargs={"pk": order.pk}), {
                "customer_type": "contact", "customer_pk": self.customer.pk,
                "book": self.book.pk, "notes": "", "deleted_items": "[]",
                "product_json_input": json.dumps([
                    self.line([(self.key(self.old), 2)], item_id=item.pk)]),
            })
        self.assertLess(response.status_code, 400)
        self.assertEqual(self.holds(order), {self.old.pk: Decimal("2")})

    def test_the_edit_form_is_handed_its_holds_by_key(self):
        self.post([self.line([(self.key(self.old), 3)])])
        order = Order.objects.get()
        page = self.client.get(reverse("operating:edit_order", kwargs={"pk": order.pk}))
        self.assertContains(page, self.key(self.old))

    # ── packing ─────────────────────────────────────────────────
    def test_scanning_the_printed_barcode_puts_the_hold_in_the_sack(self):
        self.post([self.line([(self.key(self.old), 3)])])
        order = Order.objects.get()
        pack = Pack.objects.create(order=order, pack_number=1)
        response = self.client.post(
            reverse("operating:order_pack_reserve_add", args=[order.pk]),
            {"barcode": EAN, "pack_id": pack.pk, "place_only": "1"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["moved"])
        self.assertEqual(
            OrderStockReservation.objects.get(order=order).pack_id, pack.pk)

    def test_a_printed_barcode_the_order_does_not_hold_is_not_found(self):
        order = Order.objects.create(order_number="701")
        order.items.create(product=self.cloth.catalog_variant.product,
                           product_variant=self.cloth.catalog_variant,
                           quantity=Decimal("1"), price=Decimal("2"))
        response = self.client.post(
            reverse("operating:order_pack_reserve_add", args=[order.pk]),
            {"barcode": EAN, "place_only": "1"})
        self.assertEqual(response.status_code, 404)

    # ── the form itself ─────────────────────────────────────────
    @skipUnless(shutil.which("node"), "node is not installed")
    def test_the_forms_script_still_parses(self):
        """The form is three thousand lines of script inside a template;
        a stray quote in it is a blank order page. Rendered, then handed
        to node to parse — it is not run."""
        page = self.client.get(
            reverse("operating:create_order_page", kwargs={"book_id": self.book.pk}))
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn("coTakeQuantity", html)
        tags = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", html, re.S)
        # Data blocks (type="application/json") are not script.
        scripts = [body for attrs, body in tags if "json" not in attrs]
        self.assertTrue(scripts)
        for body in scripts:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(body)
            result = subprocess.run(["node", "--check", fh.name],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:600])
