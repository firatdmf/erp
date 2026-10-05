"""A stock item's quantity changing says why, and posts where that belongs.

One number in the item's edit box can move for four reasons — a sample, a
sale, a loss, a supplier who delivered something other than they billed —
and each is a different entry. Before the box asked, the edit posted
nothing at all: the shelves lost the value and Inventory (1300) kept it.

Run with:
    python manage.py test accounting.tests.test_roll_change_reason
"""
from decimal import Decimal

from django.urls import reverse

from accounting.services_ledger import balance_sheet, reconcile
from accounting.tests import test_received_purchase_edit as base
from crm.models import Company, Contact
from operating.models import StockMovement, WarehouseProduct, WarehouseProductItem


class RollChangeReasonTest(base.TestCase):
    """The purchase: 30 m (KRV-A) and 20 m (KRV-B) at 3.50, 175.00 owed."""
    setUp = base.ReceivedPurchaseEditTest.setUp
    _invoice = base.ReceivedPurchaseEditTest._invoice
    _roll = base.ReceivedPurchaseEditTest._roll

    def _edit(self, barcode, metres, **extra):
        roll = self._roll(barcode)
        return self.client.post(
            reverse("operating:warehouse_roll_edit",
                    args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": str(metres), **extra})

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def _assert_shelves_match_the_ledger(self):
        self.assertTrue(balance_sheet(self.book)["balanced"])
        inventory = reconcile(self.book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])

    # ── ours to bear ─────────────────────────────────────────────
    def test_a_loss_goes_to_shrinkage_and_leaves_the_purchase_alone(self):
        r = self._edit("KRV-A", 28, change_reason="correction", note="water damage")
        self.assertTrue(r.json()["success"], r.json())

        roll = self._roll("KRV-A")
        self.assertEqual((roll.quantity, roll.quantity_remaining), (Decimal("28.00"), Decimal("28.00")))
        mv = StockMovement.objects.get(purpose="correction")
        self.assertEqual((mv.movement_type, mv.quantity, mv.stock_item), ("adjustment", Decimal("-2.00"), roll))
        self.assertIn("water damage", mv.reason)

        b = self._balances()
        self.assertEqual(b["5120"], Decimal("7.00"))          # 2 m x 3.50
        self.assertEqual(b["1300"], Decimal("168.00"))        # 175 - 7
        inv = self._invoice()
        self.assertEqual(inv.total, Decimal("175.00"))
        self.assertEqual(inv.posted_movement.amount, Decimal("-175.00"))
        self._assert_shelves_match_the_ledger()

    def test_no_reason_given_is_a_correction(self):
        """The scan list's quick edit sends none, and neither did this
        endpoint's callers before it asked."""
        self.assertTrue(self._edit("KRV-A", 28).json()["success"])
        self.assertEqual(self._balances()["5120"], Decimal("7.00"))
        self.assertEqual(self._invoice().total, Decimal("175.00"))

    def test_more_than_was_recorded_comes_back_off_shrinkage(self):
        self.assertTrue(self._edit("KRV-A", 31, change_reason="correction").json()["success"])
        b = self._balances()
        self.assertEqual(b["5120"], Decimal("-3.50"))
        self.assertEqual(b["1300"], Decimal("178.50"))
        self._assert_shelves_match_the_ledger()

    # ── the supplier's ───────────────────────────────────────────
    def test_a_short_delivery_moves_the_purchase_and_what_is_owed(self):
        r = self._edit("KRV-A", 28, change_reason="supplier")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(r.json()["purchase"]["total"], 168.0)

        inv = self._invoice()
        self.assertEqual(inv.items.get().quantity, Decimal("48.000"))
        self.assertEqual(inv.total, Decimal("168.00"))
        self.assertEqual(inv.posted_movement.amount, Decimal("-168.00"))
        # The purchase carries it to 1300; the stock row must not as well.
        self.assertFalse(StockMovement.objects.filter(purpose="correction").exists())
        b = self._balances()
        self.assertFalse(b.get("5120"))
        self.assertEqual(b["1300"], Decimal("168.00"))
        self._assert_shelves_match_the_ledger()

    def test_the_supplier_cannot_be_charged_for_an_item_with_no_purchase(self):
        wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name="loose", sku="LOOSE-1", quantity=Decimal("10"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("10"), quantity_remaining=Decimal("10"),
            barcode="LOOSE-A", status="in_stock", unit_cost_base=Decimal("2.00"))

        r = self._edit("LOOSE-A", 8, change_reason="supplier")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._roll("LOOSE-A").quantity, Decimal("10.00"))

    def test_the_supplier_cannot_be_charged_once_metres_have_gone_out(self):
        self.assertTrue(self._edit("KRV-A", 25, change_reason="display").json()["success"])

        r = self._edit("KRV-A", 29, change_reason="supplier")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._invoice().total, Decimal("175.00"))

    # ── stock taken out ──────────────────────────────────────────
    def _sample(self, barcode, metres, client, **extra):
        kind = "contact" if isinstance(client, Contact) else "company"
        return self._edit(barcode, metres, change_reason="sample",
                          client_type=kind, client_pk=client.pk, **extra)

    def test_a_sample_leaves_the_received_length_as_it_was(self):
        georgiana = Contact.objects.create(name="Georgiana")
        r = self._sample("KRV-A", 27, georgiana)
        self.assertTrue(r.json()["success"], r.json())

        roll = self._roll("KRV-A")
        self.assertEqual((roll.quantity, roll.quantity_remaining, roll.status),
                         (Decimal("30.00"), Decimal("27.00"), "partial"))
        mv = StockMovement.objects.get(movement_type="out")
        self.assertEqual((mv.purpose, mv.quantity, mv.reference), ("sample", Decimal("3.00"), "Georgiana"))
        # Filed against the record, not only named.
        self.assertEqual((mv.contact, mv.company), (georgiana, None))
        roll.product.refresh_from_db()
        self.assertEqual(roll.product.quantity, Decimal("47.00"))
        self.assertEqual(self._balances()["5110"], Decimal("10.50"))
        self._assert_shelves_match_the_ledger()

    def test_a_sample_needs_its_client(self):
        r = self._edit("KRV-A", 27, change_reason="sample")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._roll("KRV-A").quantity_remaining, Decimal("30.00"))
        self.assertFalse(StockMovement.objects.filter(movement_type="out").exists())

    def test_a_name_is_not_a_client(self):
        """A typed name cannot be read back off anybody's page, and a record
        that does not exist is not made here."""
        for extra in ({"reference": "Georgiana"},
                      {"client_type": "contact", "client_pk": "999999"},
                      {"client_type": "nobody", "client_pk": "1"}):
            r = self._edit("KRV-A", 27, change_reason="sample", **extra)
            self.assertEqual(r.status_code, 400, extra)
        self.assertFalse(StockMovement.objects.filter(movement_type="out").exists())
        self.assertFalse(Contact.objects.exists())

    # ── on the client's page ─────────────────────────────────────
    def test_a_contacts_page_lists_what_they_were_given(self):
        georgiana = Contact.objects.create(name="Georgiana")
        other = Contact.objects.create(name="Somebody Else")
        self.assertTrue(self._sample("KRV-A", 27, georgiana, note="new collection").json()["success"])
        self.assertTrue(self._sample("KRV-B", 19, other).json()["success"])

        r = self.client.get(reverse("crm:contact_detail", args=[georgiana.pk]))

        self.assertEqual(r.status_code, 200)
        samples = r.context["samples"]
        self.assertEqual([(s.quantity, s.stock_item.barcode, s.sample_note) for s in samples],
                         [(Decimal("3.00"), "KRV-A", "new collection")])
        html = r.content.decode()
        self.assertIn("Samples sent", html)
        self.assertIn("KRV-A", html)
        self.assertNotIn("KRV-B", html)

    def test_a_companys_page_includes_what_went_to_its_people(self):
        karaca = Company.objects.create(name="Karaca Home")
        buyer = Contact.objects.create(name="Selin", company=karaca)
        self.assertTrue(self._sample("KRV-A", 28, karaca).json()["success"])
        self.assertTrue(self._sample("KRV-B", 19, buyer).json()["success"])

        r = self.client.get(reverse("crm:company_detail", args=[karaca.pk]))

        self.assertEqual(r.status_code, 200)
        self.assertEqual({s.stock_item.barcode for s in r.context["samples"]}, {"KRV-A", "KRV-B"})
        self.assertIn("Selin", r.content.decode())

    def test_a_display_piece_is_on_nobodys_page(self):
        georgiana = Contact.objects.create(name="Georgiana")
        self.assertTrue(self._edit("KRV-A", 28, change_reason="display").json()["success"])
        r = self.client.get(reverse("crm:contact_detail", args=[georgiana.pk]))
        self.assertEqual(list(r.context["samples"]), [])
        self.assertIn("No samples sent yet.", r.content.decode())

    def test_a_piece_for_display_is_marketing_with_nobody_behind_it(self):
        """A cut for the showroom or a trade show is not a loss and went to
        no client — it is what selling costs."""
        r = self._edit("KRV-A", 28, change_reason="display", note="Heimtextil stand")
        self.assertTrue(r.json()["success"], r.json())

        mv = StockMovement.objects.get(movement_type="out")
        self.assertEqual((mv.purpose, mv.quantity, mv.reason),
                         ("display", Decimal("2.00"), "Display — Heimtextil stand"))
        b = self._balances()
        self.assertEqual(b["5110"], Decimal("7.00"))
        self.assertFalse(b.get("5120"))
        self._assert_shelves_match_the_ledger()

    def test_lost_or_damaged_stock_left_the_item_and_is_shrinkage(self):
        """Unlike a re-measure, the item did hold it: the received length
        stays and the loss is something that came off it."""
        r = self._edit("KRV-A", 25, change_reason="loss", note="water damage")
        self.assertTrue(r.json()["success"], r.json())

        roll = self._roll("KRV-A")
        self.assertEqual((roll.quantity, roll.quantity_remaining), (Decimal("30.00"), Decimal("25.00")))
        mv = StockMovement.objects.get(movement_type="out")
        self.assertEqual((mv.purpose, mv.quantity, mv.reason),
                         ("loss", Decimal("5.00"), "Lost, damaged or defective — water damage"))
        b = self._balances()
        self.assertEqual(b["5120"], Decimal("17.50"))
        self.assertFalse(b.get("5000"))
        self.assertEqual(self._invoice().total, Decimal("175.00"))
        self._assert_shelves_match_the_ledger()

    def test_a_sale_is_not_recorded_from_the_item(self):
        """Goods sold leave on an order, which posts their cost when it
        ships. Saying "sold" here as well would be cost with no revenue."""
        r = self._edit("KRV-A", 25, change_reason="out")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._roll("KRV-A").quantity_remaining, Decimal("30.00"))
        self.assertFalse(StockMovement.objects.filter(movement_type="out").exists())

    def test_nothing_is_taken_out_by_a_larger_figure(self):
        r = self._edit("KRV-A", 31, change_reason="loss")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(StockMovement.objects.filter(movement_type="out").exists())

    # ── the box ──────────────────────────────────────────────────
    def test_a_lot_number_alone_asks_nothing_and_posts_nothing(self):
        before = StockMovement.objects.count()
        roll = self._roll("KRV-A")
        r = self.client.post(
            reverse("operating:warehouse_roll_edit", args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": "30.00", "lot_number": "L-9"})
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(StockMovement.objects.count(), before)
        self.assertFalse(self._balances().get("5120"))

    def test_the_box_names_the_purchase_and_opens_no_panel_of_its_own(self):
        roll = self._roll("KRV-A")
        html = self.client.get(reverse(
            "operating:warehouse_product_detail",
            kwargs={"warehouse_pk": self.wh.pk, "product_pk": roll.product_id})).content.decode()
        self.assertIn(f'data-purchase="{self._invoice().display_number}"', html)
        self.assertIn('id="reWhy" hidden', html)
        self.assertNotIn('id="reOutPurpose"', html)
        # What the entry beside the form is priced with.
        self.assertIn('id="reEntry" hidden', html)
        self.assertIn('data-cost="3.500000"', html)
        self.assertIn('data-purchase-price="3.500000"', html)
