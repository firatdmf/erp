"""Our own rolls sent out to a supplier to be worked on: goods out and in.

Plain fabric goes to Hakan, crystals or pearls go on it, and the work comes
back. On the purchase the plain rolls are goods out; what comes back is its
ordinary products (goods in), priced at the work. A goods-in roll with an
out roll's barcode is that roll come back; out rolls that don't come back
were used up in the work. The value of everything that went out is spread
per unit over everything that came in, and Hakan is owed only the work.

Run with:
    scripts/test_local.sh accounting.tests.test_purchase_processing
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory, ProcessingLine
from accounting.models_accounts import CurrentAccount, Invoice
from crm.models import Company
from marketing.models import Product
from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class GoodsOutTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene")
        self.mill = CurrentAccount.objects.create(
            book=self.book, code="C-KZL", name="Kizilirmak", type="supplier", default_currency=usd)
        self.hakan_co = Company.objects.create(name="Hakan Atölye")
        self.hakan = CurrentAccount.objects.create(
            book=self.book, code="C-HKN", name="Hakan Atölye", type="supplier",
            default_currency=usd, company=self.hakan_co)
        self.wh = Warehouse.objects.create(name="Fabrika", accounting_book=self.book)
        self.client.force_login(get_user_model().objects.create_superuser(
            username="processing", password="pw", email="p@r.t"))
        self._receive_fabric()
        self.product = Product.objects.get(sku="HAVANA")

    # ── helpers ──────────────────────────────────────────────────────────
    def _post(self, name, data, how):
        return self.client.post(reverse(name, **how), data=json.dumps(data),
                                content_type="application/json")

    @staticmethod
    def _variant(value, tops, price="2"):
        return {"attributes": [{"name": "color", "value": value}],
                "sku": "HAVANA." + value.upper().replace("+", "_"),
                "price": price, "currency": "USD", "tops": tops}

    def _receive_fabric(self):
        """Plain ecru at $2/m, and a roll each of crystal and pearl."""
        data = {
            "warehouse_id": self.wh.pk, "current_account_id": self.mill.pk,
            "unit": "m", "date": "2026-11-10",
            "products": [{
                "main_product": {"mode": "new", "name": "HAVANA", "sku": "HAVANA"},
                "has_variants": True,
                "variants": [self._variant("ecru", [{"qty": 50, "barcode": "KZL-A"},
                                                    {"qty": 40, "barcode": "KZL-B"}]),
                             self._variant("ecru+crystal", [{"qty": 10, "barcode": "KZL-C"}]),
                             self._variant("ecru+pearl", [{"qty": 10, "barcode": "KZL-P"}])],
            }],
        }
        r = self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})
        self.assertTrue(r.json()["success"], r.json())
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[r.json()["invoice_id"]]))
        self.assertTrue(c.json()["success"], c.json())

    def _goods_in(self, *variants):
        return [{"main_product": {"mode": "existing", "id": self.product.pk,
                                  "title": "HAVANA", "sku": "HAVANA"},
                 "has_variants": True, "variants": list(variants)}]

    def _save(self, out, goods_in=(), pk=None):
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.hakan.pk,
                "date": "2026-11-16", "unit": "m",
                "goods_out": [{"barcode": c} for c in out], "products": list(goods_in)}
        if pk:
            return self._post("accounts:purchase_order_update", data, {"args": [pk]})
        return self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})

    def _confirm(self, pk):
        return self.client.post(reverse("accounts:purchase_order_confirm", args=[pk]))

    def _roll(self, code):
        return WarehouseProductItem.objects.select_related("product").get(barcode=code)

    def _balance(self, account):
        account.recompute_balance(save=True)
        account.refresh_from_db()
        return account.cached_balance

    def _sent_and_back(self):
        """A and B go out; A comes back as 48 m of crystal at $1.50, and a
        new 38 m roll of pearl at $2; B was used up."""
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        r = self._save(["KZL-A", "KZL-B"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5"),
            self._variant("ecru+pearl", [{"qty": 38, "barcode": ""}], price="2")), pk=pk)
        self.assertTrue(r.json()["success"], r.json())
        c = self._confirm(pk)
        self.assertTrue(c.json()["success"], c.json())
        return pk

    # ── sending ──────────────────────────────────────────────────────────
    def test_goods_out_alone_is_an_order_and_the_rolls_are_away(self, _up):
        r = self._save(["KZL-A", "KZL-B"])
        self.assertTrue(r.json()["success"], r.json())
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        self.assertEqual((inv.status, inv.total), ("ordered", Decimal("0.00")))
        self.assertEqual(ProcessingLine.objects.filter(invoice=inv).count(), 2)
        roll = self._roll("KZL-A")
        self.assertTrue(roll.is_away)
        from operating.views import _roll_available_meters
        self.assertEqual(_roll_available_meters(roll), Decimal("0"))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    def test_a_roll_taken_off_goods_out_comes_home(self, _up):
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        self.assertTrue(self._save(["KZL-A"], pk=pk).json()["success"])
        self.assertFalse(self._roll("KZL-B").is_away)
        self.assertTrue(self._roll("KZL-A").is_away)

    def test_refusals_change_nothing(self, _up):
        self.assertTrue(self._save(["KZL-A"]).json()["success"])
        for out, words in ((["KZL-A"], "already away"), (["NOPE"], "Nothing in stock"),
                           (["KZL-B", "KZL-B"], "twice")):
            r = self._save(out)
            self.assertEqual(r.status_code, 400, (out, r.content))
            self.assertIn(words, r.json()["error"])
        self.assertEqual(Invoice.objects.filter(current_account=self.hakan).count(), 1)
        self.assertFalse(self._roll("KZL-B").is_away)

    def test_a_roll_reserved_for_an_order_is_refused(self, _up):
        roll = self._roll("KZL-B")
        OrderStockReservation.objects.create(order=Order.objects.create(), stock_item=roll,
                                             warehouse_product=roll.product, quantity=Decimal("40"))
        r = self._save(["KZL-B"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("reserved", r.json()["error"])

    def test_a_roll_of_another_book_is_refused(self, _up):
        far = Warehouse.objects.create(name="Laleli store",
                                       accounting_book=Book.objects.create(name="Laleli"))
        WarehouseProduct.objects.filter(warehouse=self.wh, sku="HAVANA.ECRU").update(warehouse=far)
        r = self._save(["KZL-A"])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Laleli", r.json()["error"])

    # ── receiving ────────────────────────────────────────────────────────
    def test_receiving_needs_goods_in(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self._confirm(pk)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("came back", r.json()["error"])
        self.assertTrue(self._roll("KZL-A").is_away)

    def test_a_returned_roll_keeps_its_record_and_the_rest_were_used_up(self, _up):
        pk = self._sent_and_back()
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity, a.quantity_remaining, a.is_away),
                         ("HAVANA.ECRU_CRYSTAL", Decimal("48"), Decimal("48"), False))
        self.assertEqual((b.status, b.quantity_remaining, b.is_away), ("consumed", 0, False))
        self.assertEqual(WarehouseProductItem.objects.filter(barcode="KZL-A").count(), 1)
        lines = {l.barcode: l.outcome for l in ProcessingLine.objects.filter(invoice_id=pk)}
        self.assertEqual(lines, {"KZL-A": "came_back", "KZL-B": "used"})

    def test_what_went_out_is_spread_over_what_came_in_and_only_the_work_is_owed(self, _up):
        pk = self._sent_and_back()
        # 90 m at $2 went out = $180, over 86 m that came in.
        share = Decimal("180") / Decimal("86")
        a = self._roll("KZL-A")
        pearl = (WarehouseProductItem.objects
                 .filter(product__sku="HAVANA.ECRU_PEARL", quantity=Decimal("38")).get())
        self.assertAlmostEqual(a.unit_cost_base, Decimal("1.5") + share, places=3)
        self.assertAlmostEqual(pearl.unit_cost_base, Decimal("2") + share, places=3)
        # 48 × 1.50 + 38 × 2
        self.assertEqual(Invoice.objects.get(pk=pk).total, Decimal("148.00"))
        self.assertEqual(self._balance(self.hakan), Decimal("-148.00"))

    def test_only_its_own_goods_out_may_come_back_under_their_barcode(self, _up):
        """KZL-A went out, so it may come back as KZL-A. KZL-C is in stock
        and did not go out: its barcode is someone else's, and is refused."""
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        self._save(["KZL-A"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-C"}], price="1.5")), pk=pk)
        r = self._confirm(pk)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("KZL-C", r.json()["error"])
        self.assertEqual(Invoice.objects.get(pk=pk).status, "ordered")
        self.assertTrue(self._roll("KZL-A").is_away)
        self.assertEqual(WarehouseProductItem.objects.filter(barcode="KZL-C").count(), 1)

    def test_the_ledger_still_matches_the_shelves(self, _up):
        from accounting.services_ledger import reconcile
        self._sent_and_back()
        row = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1300")
        # $220 of fabric before, plus $148 of work.
        self.assertAlmostEqual(row["ledger"], Decimal("368"), places=2)
        self.assertAlmostEqual(row["subsidiary"], row["ledger"], places=2)

    # ── goods counted in pieces: so many of a box ────────────────────────
    PRINTED = "8690000000017"

    def _receive_pillowcases(self):
        """Two boxes of white pillowcases at $3 a piece, 12 and 5, bought
        from the mill. They are counted, not labelled one by one: every
        piece carries the printed barcode of its variant."""
        data = {
            "warehouse_id": self.wh.pk, "current_account_id": self.mill.pk,
            "unit": "piece", "date": "2026-11-11",
            "products": [{
                "main_product": {"mode": "new", "name": "PILLOW", "sku": "PILLOW"},
                "tracking": "variant", "pack_type": "box",
                "has_variants": True,
                "variants": [{"attributes": [{"name": "color", "value": "white"}],
                              "sku": "PILLOW.WHITE", "price": "3", "currency": "USD",
                              "tops": [{"qty": 12, "barcode": ""}, {"qty": 5, "barcode": ""}]}],
            }],
        }
        r = self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})
        self.assertTrue(r.json()["success"], r.json())
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[r.json()["invoice_id"]]))
        self.assertTrue(c.json()["success"], c.json())
        Product.objects.get(sku="PILLOW").variants.filter(variant_sku="PILLOW.WHITE") \
            .update(variant_barcode=self.PRINTED)
        big, small = (WarehouseProductItem.objects.filter(product__sku="PILLOW.WHITE")
                      .order_by("-quantity"))
        self.assertEqual((big.barcode, big.quantity, small.quantity), (None, 12, 5))
        return big, small

    def _send(self, rows, goods_in=(), pk=None):
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.hakan.pk,
                "date": "2026-11-16", "unit": "piece", "goods_out": rows,
                "products": list(goods_in)}
        if pk:
            return self._post("accounts:purchase_order_update", data, {"args": [pk]})
        return self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})

    def _left_in(self, item):
        item.refresh_from_db()
        return item.quantity_remaining

    def test_part_of_a_box_goes_out_split_off_it(self, _up):
        big, small = self._receive_pillowcases()
        r = self._send([{"barcode": big.pick_key, "quantity": "4"}])
        self.assertTrue(r.json()["success"], r.json())
        line = ProcessingLine.objects.get(invoice_id=r.json()["invoice_id"])
        piece = line.stock_item
        self.assertEqual((line.split_from_id, line.quantity), (big.pk, Decimal("4")))
        self.assertEqual((piece.quantity_remaining, piece.unit_cost_base, piece.is_away, piece.barcode),
                         (Decimal("4"), Decimal("3"), True, None))
        self.assertEqual(self._left_in(big), Decimal("8"))
        self.assertFalse(big.is_away)
        # Still the same 17 pieces on the books, and nothing owed.
        self.assertEqual(sum(WarehouseProductItem.objects.filter(product=big.product)
                             .values_list("quantity_remaining", flat=True)), Decimal("17"))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    def test_saving_again_keeps_the_part_and_a_new_count_or_none_puts_it_back(self, _up):
        big, _small = self._receive_pillowcases()
        pk = self._send([{"barcode": big.pick_key, "quantity": "4"}]).json()["invoice_id"]
        first = ProcessingLine.objects.get(invoice_id=pk).stock_item_id
        self.assertTrue(self._send([{"barcode": big.pick_key, "quantity": "4"}], pk=pk).json()["success"])
        self.assertEqual(ProcessingLine.objects.get(invoice_id=pk).stock_item_id, first)
        self.assertTrue(self._send([{"barcode": big.pick_key, "quantity": "6"}], pk=pk).json()["success"])
        self.assertEqual(self._left_in(big), Decimal("6"))
        self.assertEqual(WarehouseProductItem.objects.get(pk=first).status, "consumed")
        r = self._send([{"barcode": "KZL-A"}], pk=pk)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual((self._left_in(big), big.quantity, big.status),
                         (Decimal("12"), Decimal("12"), "in_stock"))
        self.assertEqual(sum(WarehouseProductItem.objects.filter(product=big.product)
                             .values_list("quantity_remaining", flat=True)), Decimal("17"))

    def test_a_whole_box_goes_as_it_is(self, _up):
        _big, small = self._receive_pillowcases()
        pk = self._send([{"barcode": small.pick_key, "quantity": "5"}]).json()["invoice_id"]
        line = ProcessingLine.objects.get(invoice_id=pk)
        self.assertEqual((line.stock_item_id, line.split_from_id), (small.pk, None))
        self.assertTrue(WarehouseProductItem.objects.get(pk=small.pk).is_away)

    def test_the_printed_barcode_finds_the_oldest_box_with_some_free(self, _up):
        big, small = self._receive_pillowcases()
        url = reverse("accounts:processing_roll", args=[self.hakan.pk])
        d = self.client.get(url, {"code": self.PRINTED}).json()["roll"]
        self.assertEqual((d["stock_item_id"], d["counted"], d["free"], d["printed"], d["problem"]),
                         (big.pk, True, "12", self.PRINTED, None))
        nxt = self.client.get(url, {"code": self.PRINTED, "skip": big.pick_key}).json()["roll"]
        self.assertEqual(nxt["stock_item_id"], small.pk)
        # Typed into the box and saved as it is, the printed barcode is one piece.
        pk = self._send([{"barcode": self.PRINTED}]).json()["invoice_id"]
        self.assertEqual(ProcessingLine.objects.get(invoice_id=pk).quantity, Decimal("1"))
        # Saved, the box shows what this purchase takes out of it.
        d = self.client.get(url, {"code": big.pick_key, "purchase": pk}).json()["roll"]
        self.assertEqual((d["quantity"], d["free"]), ("12", "12"))

    def test_only_what_no_order_holds_may_go(self, _up):
        big, _small = self._receive_pillowcases()
        OrderStockReservation.objects.create(order=Order.objects.create(), stock_item=big,
                                             warehouse_product=big.product, quantity=Decimal("10"))
        r = self._send([{"barcode": big.pick_key, "quantity": "4"}])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Only 2", r.json()["error"])
        self.assertEqual(self._left_in(big), Decimal("12"))
        self.assertTrue(self._send([{"barcode": big.pick_key, "quantity": "2"}]).json()["success"])

    def test_a_labelled_roll_goes_out_whole_and_a_count_must_be_one(self, _up):
        for rows, words in (([{"barcode": "KZL-A", "quantity": "10"}], "goes out whole"),
                            ([{"barcode": "KZL-A", "quantity": "lots"}], "above 0"),
                            ([{"barcode": "KZL-A", "quantity": "60"}], "there aren't 60")):
            r = self._send(rows)
            self.assertEqual(r.status_code, 400, (rows, r.content))
            self.assertIn(words, r.json()["error"])
        self.assertFalse(self._roll("KZL-A").is_away)

    def test_a_part_comes_back_worked_and_undo_and_cancel_put_it_back_in_its_box(self, _up):
        from accounting.services_ledger import reconcile
        big, _small = self._receive_pillowcases()
        pk = self._send([{"barcode": big.pick_key, "quantity": "4"}]).json()["invoice_id"]
        back = [{"main_product": {"mode": "existing", "id": big.product.catalog_variant.product_id,
                                  "title": "PILLOW", "sku": "PILLOW"},
                 "has_variants": True,
                 "variants": [{"attributes": [{"name": "color", "value": "white+lace"}],
                               "sku": "PILLOW.WHITE_LACE", "price": "1", "currency": "USD",
                               "tops": [{"qty": 4, "barcode": ""}]}]}]
        self.assertTrue(self._send([{"barcode": big.pick_key, "quantity": "4"}], back,
                                   pk=pk).json()["success"])
        c = self._confirm(pk)
        self.assertTrue(c.json()["success"], c.json())
        line = ProcessingLine.objects.get(invoice_id=pk)
        self.assertEqual((line.outcome, line.stock_item.status), ("used", "consumed"))
        lace = WarehouseProductItem.objects.get(product__sku="PILLOW.WHITE_LACE")
        # $3 a piece went out, $1 of work on each.
        self.assertEqual((lace.quantity_remaining, lace.unit_cost_base), (Decimal("4"), Decimal("4")))
        row = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1300")
        self.assertAlmostEqual(row["subsidiary"], row["ledger"], places=2)

        self.assertEqual(self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
                         .status_code, 200)
        self.assertTrue(ProcessingLine.objects.get(invoice_id=pk).stock_item.is_away)
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "not sent"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._left_in(big), Decimal("12"))
        row = next(r for r in reconcile(self.book)["rows"] if r["control"] == "1300")
        self.assertAlmostEqual(row["subsidiary"], row["ledger"], places=2)

    # ── bought for an order ──────────────────────────────────────────────
    def _order_for_crystal(self):
        """A customer order with a line for the crystal variant, the way
        order 363 had one for GREK.WHITE-330-PEARL_CRYSTAL."""
        from crm.models import Contact
        from operating.models import OrderItem
        usd = self.hakan.default_currency
        buyer = Contact.objects.create(name="Oleg")
        account = CurrentAccount.objects.create(book=self.book, code="C-OLG", name="Oleg",
                                                default_currency=usd, contact=buyer)
        order = Order.objects.create(contact=buyer, current_account=account)
        crystal = self.product.variants.get(variant_sku="HAVANA.ECRU_CRYSTAL")
        OrderItem.objects.create(order=order, product=self.product, product_variant=crystal,
                                 quantity=Decimal("48"), price=Decimal("6"))
        return order

    def test_what_comes_back_for_an_order_is_held_for_it_and_let_go_on_undo(self, _up):
        order = self._order_for_crystal()
        data = {"warehouse_id": self.wh.pk, "current_account_id": self.hakan.pk,
                "date": "2026-11-19", "unit": "m", "for_order_id": order.pk,
                "goods_out": [{"barcode": "KZL-A"}], "products": []}
        r = self._post("accounts:purchase_order_save", data, {"kwargs": {"book_id": self.book.pk}})
        self.assertTrue(r.json()["success"], r.json())
        pk = r.json()["invoice_id"]
        r = self._save(["KZL-A"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5")), pk=pk)
        self.assertTrue(r.json()["success"], r.json())
        c = self._confirm(pk)
        self.assertTrue(c.json()["success"], c.json())
        holds = OrderStockReservation.objects.filter(order=order, consumed=False)
        self.assertEqual(list(holds.values_list("stock_item__barcode", flat=True)), ["KZL-A"])
        # The order's purchase card counts it: the roll came back on this
        # purchase, though its own purchase is the one that first bought it.
        page = self.client.get(reverse("operating:order_detail", args=[order.pk]))
        card = next(p for p in page.context["supplier_purchases"] if p.pk == pk)
        self.assertEqual(card.held_quantity, Decimal("48"))

        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(OrderStockReservation.objects.filter(order=order, consumed=False).exists())
        self.assertEqual(self._roll("KZL-A").product.sku, "HAVANA.ECRU")

    # ── undo and cancel ──────────────────────────────────────────────────
    def test_undo_receipt_puts_every_out_roll_back_and_away_again(self, _up):
        pk = self._sent_and_back()
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 200, r.content)
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity_remaining, a.unit_cost_base, a.is_away),
                         ("HAVANA.ECRU", Decimal("50"), Decimal("2"), True))
        self.assertEqual((b.status, b.quantity_remaining, b.is_away), ("in_stock", Decimal("40"), True))
        self.assertFalse(WarehouseProductItem.objects.filter(
            product__sku="HAVANA.ECRU_PEARL", quantity=Decimal("38")).exists())
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))
        self.assertTrue(self._confirm(pk).json()["success"])
        self.assertEqual(self._roll("KZL-A").product.sku, "HAVANA.ECRU_CRYSTAL")

    def test_undo_is_refused_once_a_returned_roll_is_cut(self, _up):
        pk = self._sent_and_back()
        WarehouseProductItem.objects.filter(barcode="KZL-A").update(quantity_remaining=Decimal("45"))
        r = self.client.post(reverse("accounts:purchase_undo_receipt", args=[pk]))
        self.assertEqual(r.status_code, 422, r.content)
        self.assertEqual(Invoice.objects.get(pk=pk).status, "received")

    def test_cancelling_a_draft_brings_the_rolls_home(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "not sent"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(self._roll("KZL-A").is_away)

    def test_cancelling_a_received_one_puts_the_rolls_back(self, _up):
        pk = self._sent_and_back()
        r = self.client.post(reverse("accounts:purchase_cancel", args=[pk]), {"reason": "wrong"})
        self.assertEqual(r.status_code, 200, r.content)
        a, b = self._roll("KZL-A"), self._roll("KZL-B")
        self.assertEqual((a.product.sku, a.quantity_remaining, a.is_away),
                         ("HAVANA.ECRU", Decimal("50"), False))
        self.assertEqual((b.status, b.is_away), ("in_stock", False))
        self.assertEqual(self._balance(self.hakan), Decimal("0.00"))

    # ── where it shows ───────────────────────────────────────────────────
    def test_the_form_looks_a_roll_up(self, _up):
        url = reverse("accounts:processing_roll", args=[self.hakan.pk])
        d = self.client.get(url, {"code": "KZL-A"}).json()
        self.assertEqual((d["roll"]["sku"], d["roll"]["quantity"], d["roll"]["problem"]),
                         ("HAVANA.ECRU", "50", None))
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        self.assertIn("already away", self.client.get(url, {"code": "KZL-A"}).json()["roll"]["problem"])
        self.assertIsNone(self.client.get(url, {"code": "KZL-A", "purchase": pk})
                          .json()["roll"]["problem"])
        self.assertEqual(self.client.get(url, {"code": "NOPE"}).status_code, 404)

    def test_the_purchase_page_shows_goods_out_and_what_became_of_them(self, _up):
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        page = reverse("accounts:purchase_order_detail", args=[pk])
        r = self.client.get(page)
        self.assertContains(r, "Our goods sent out")
        self.assertContains(r, "away")
        self._save(["KZL-A", "KZL-B"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5")), pk=pk)
        self.assertTrue(self._confirm(pk).json()["success"])
        r = self.client.get(page)
        self.assertContains(r, "came back")
        self.assertContains(r, "used up in the work")
        self.assertNotContains(r, reverse("accounts:goods_receipt_edit", args=[pk]))

    def test_a_returned_roll_shows_and_prints_under_the_line_it_came_back_as(self, _up):
        pk = self._sent_and_back()
        inv = Invoice.objects.get(pk=pk)
        crystal = inv.items.get(variant__variant_sku="HAVANA.ECRU_CRYSTAL")
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[pk]))
        self.assertContains(page, "<code>KZL-A</code>", html=False)
        with patch("operating.warehouse_label.labels_pdf_bytes", return_value=b"%PDF") as pdf:
            r = self.client.get(reverse("accounts:purchase_item_labels", args=[pk, crystal.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([roll.barcode for _wp, roll in pdf.call_args[0][0]], ["KZL-A"])

    def test_rolls_away_show_on_the_list_and_on_the_suppliers_page(self, _up):
        self._save(["KZL-A", "KZL-B"])
        lst = self.client.get(reverse("accounts:purchase_order_list", kwargs={"book_id": self.book.pk}))
        self.assertContains(lst, "2 items away · 90 m")
        crm = self.client.get(reverse("crm:company_detail", args=[self.hakan_co.pk]))
        self.assertContains(crm, "2 items away · 90 m")

    def test_the_warehouse_says_an_item_is_away_and_on_which_purchase(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        number = Invoice.objects.get(pk=pk).display_number
        roll = self._roll("KZL-A")
        page = reverse("accounts:purchase_order_detail", args=[pk])
        for url in (reverse("operating:warehouse_product_detail", args=[self.wh.pk, roll.product_id]),
                    reverse("operating:warehouse_product_rolls", args=[self.wh.pk, roll.product_id])):
            r = self.client.get(url)
            self.assertContains(r, "Away for work", count=1)
            self.assertContains(r, page)
            self.assertContains(r, number)
        found = self.client.get(reverse("operating:warehouse_barcode_lookup", args=[self.wh.pk]),
                                {"barcode": "KZL-A"}).json()
        self.assertEqual(found["roll"]["away"], {"number": number, "url": page})
        home = self.client.get(reverse("operating:warehouse_barcode_lookup", args=[self.wh.pk]),
                               {"barcode": "KZL-B"}).json()
        self.assertIsNone(home["roll"]["away"])

    def test_the_shelf_figures_say_what_is_away(self, _up):
        """The stock still counts an item away for work, so every figure
        that says what is in stock says how much of it is away too."""
        # With nothing away the warehouses list still leads to the page.
        before = self.client.get(reverse("operating:warehouse_list"), follow=True)
        self.assertContains(before, reverse("operating:warehouse_away"))
        self.assertNotContains(before, "1 away for work")
        self._save(["KZL-A"])
        roll = self._roll("KZL-A")
        page = self.client.get(reverse("operating:warehouse_detail", args=[self.wh.pk]))
        self.assertContains(page, "Away for work: 50")
        self.assertContains(page, "1 item away for work")
        product = self.client.get(reverse("operating:warehouse_product_detail",
                                          args=[self.wh.pk, roll.product_id]))
        self.assertContains(product, "50.00 m away for work")
        group = self.client.get(reverse("operating:warehouse_group_variants", args=[self.wh.pk]),
                                {"base": "HAVANA"})
        self.assertContains(group, "Away for work: 50")
        listing = self.client.get(reverse("operating:warehouse_list"), follow=True)
        self.assertContains(listing, reverse("operating:warehouse_away"))
        # The Excel export says it too, row and total.
        from operating.warehouse_excel import build_warehouse_workbook
        ws = build_warehouse_workbook(self.wh).active
        rows = [[c.value for c in row] for row in ws.iter_rows()]
        head = next(row for row in rows if row[0] == "SKU")
        col = head.index("Away for work (m)")
        mine = next(row for row in rows if row[0] == roll.product.sku)
        self.assertEqual(mine[col], 50.0)
        self.assertEqual(rows[-1][col], 50.0)

    def test_everything_away_is_listed_by_supplier(self, _up):
        pk = self._save(["KZL-A", "KZL-B"]).json()["invoice_id"]
        number = Invoice.objects.get(pk=pk).display_number
        r = self.client.get(reverse("operating:warehouse_away"))
        self.assertContains(r, "Hakan Atölye")
        self.assertContains(r, "2 items away · 90 m")
        self.assertContains(r, number)
        self.assertContains(r, "KZL-A")
        self.assertNotContains(r, "KZL-C")
        one = self.client.get(reverse("operating:warehouse_away"), {"warehouse": self.wh.pk})
        self.assertContains(one, "KZL-B")
        far = Warehouse.objects.create(name="Elsewhere", accounting_book=self.book)
        self.assertNotContains(self.client.get(reverse("operating:warehouse_away"),
                                               {"warehouse": far.pk}), "KZL-A")
        self.assertEqual(self.client.get(reverse("operating:warehouse_away"),
                                         {"warehouse": 999999}).status_code, 404)
        # Back from the work, it is off the list.
        self._save(["KZL-A", "KZL-B"], self._goods_in(
            self._variant("ecru+crystal", [{"qty": 48, "barcode": "KZL-A"}], price="1.5")), pk=pk)
        self.assertTrue(self._confirm(pk).json()["success"])
        self.assertContains(self.client.get(reverse("operating:warehouse_away")),
                            "Nothing is away for work.")

    def test_a_draft_opens_in_the_form_with_its_goods_out(self, _up):
        pk = self._save(["KZL-A"]).json()["invoice_id"]
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="npWorkSec"')
        # Several barcodes at once, one a line.
        self.assertContains(r, '<textarea id="npWorkCode"')
        self.assertContains(r, '"goods_out"')
