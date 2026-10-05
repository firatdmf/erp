"""Several samples sent to one client together are a sample package.

Made from the client's CRM page. Each piece is cut off its own stock item
when the package is saved and posts as any sample does; the package adds
what the pieces share — the date, a note, and how the parcel travelled.

Run with:
    python manage.py test accounting.tests.test_sample_package
"""
import json
from decimal import Decimal

from django.urls import reverse

from accounting.services_ledger import balance_sheet, reconcile
from accounting.tests import test_received_purchase_edit as base
from crm.models import Company, Contact
from operating.models import Carrier, SamplePackage, StockMovement


class SamplePackageTest(base.TestCase):
    """The stock: 30 m (KRV-A) and 20 m (KRV-B) of one product, at 3.50."""
    setUp = base.ReceivedPurchaseEditTest.setUp
    _roll = base.ReceivedPurchaseEditTest._roll

    def _create(self, client, lines, **extra):
        kind = "contact" if isinstance(client, Contact) else "company"
        body = {"client_type": kind, "client_pk": client.pk,
                "lines": [{"stock_item_id": self._roll(barcode).pk, "quantity": qty}
                          for barcode, qty in lines], **extra}
        return self.client.post(reverse("operating:sample_package_create"),
                                data=json.dumps(body), content_type="application/json")

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    # ── making one ───────────────────────────────────────────────
    def test_every_piece_is_cut_and_filed_against_the_client(self):
        georgiana = Contact.objects.create(name="Georgiana")

        r = self._create(georgiana, [("KRV-A", "2"), ("KRV-B", "1.5")],
                         date="2026-10-01", note="autumn colours")
        self.assertTrue(r.json()["success"], r.json())

        package = SamplePackage.objects.get()
        self.assertEqual((package.contact, package.company, package.status, package.note),
                         (georgiana, None, "prepared", "autumn colours"))
        self.assertEqual(str(package.date), "2026-10-01")
        self.assertEqual(r.json()["package"]["number"], package.number)

        pieces = {m.stock_item.barcode: m for m in package.movements.all()}
        self.assertEqual({b: (m.movement_type, m.purpose, m.quantity, m.contact)
                          for b, m in pieces.items()},
                         {"KRV-A": ("out", "sample", Decimal("2.00"), georgiana),
                          "KRV-B": ("out", "sample", Decimal("1.50"), georgiana)})
        self.assertEqual(self._roll("KRV-A").quantity_remaining, Decimal("28.00"))
        self.assertEqual(self._roll("KRV-B").quantity_remaining, Decimal("18.50"))
        # Both rolls are one product: its total loses both cuts, not the last.
        product = self._roll("KRV-A").product
        self.assertEqual(product.quantity, Decimal("46.50"))

    def test_it_posts_as_samples_do_and_the_shelves_still_match(self):
        self.assertTrue(self._create(Contact.objects.create(name="Georgiana"),
                                     [("KRV-A", "2"), ("KRV-B", "1.5")]).json()["success"])
        b = self._balances()
        self.assertEqual(b["5110"], Decimal("12.25"))        # 3.5 m x 3.50
        self.assertEqual(b["1300"], Decimal("162.75"))       # 175 - 12.25
        self.assertTrue(balance_sheet(self.book)["balanced"])
        inventory = reconcile(self.book)["rows"][2]
        self.assertEqual(inventory["ledger"], inventory["subsidiary"])

    def test_the_same_roll_named_twice_is_one_cut(self):
        self.assertTrue(self._create(Contact.objects.create(name="Georgiana"),
                                     [("KRV-A", "2"), ("KRV-A", "3")]).json()["success"])
        self.assertEqual(StockMovement.objects.get(purpose="sample").quantity, Decimal("5.00"))

    def test_one_piece_that_cannot_be_cut_refuses_the_whole_package(self):
        r = self._create(Contact.objects.create(name="Georgiana"),
                         [("KRV-A", "2"), ("KRV-B", "25")])
        self.assertEqual(r.status_code, 400)
        self.assertIn("KRV-B", r.json()["error"])
        self.assertFalse(SamplePackage.objects.exists())
        self.assertFalse(StockMovement.objects.filter(purpose="sample").exists())
        self.assertEqual(self._roll("KRV-A").quantity_remaining, Decimal("30.00"))

    def test_it_needs_a_client_and_something_in_it(self):
        georgiana = Contact.objects.create(name="Georgiana")
        self.assertEqual(self._create(georgiana, []).status_code, 400)
        self.assertEqual(self._create(georgiana, [("KRV-A", "0")]).status_code, 400)
        nobody = self.client.post(
            reverse("operating:sample_package_create"),
            data=json.dumps({"client_type": "contact", "client_pk": 999999,
                             "lines": [{"stock_item_id": self._roll("KRV-A").pk, "quantity": "1"}]}),
            content_type="application/json")
        self.assertEqual(nobody.status_code, 400)
        self.assertFalse(SamplePackage.objects.exists())

    # ── shipping ─────────────────────────────────────────────────
    def test_a_package_sent_straight_away_says_so(self):
        r = self._create(Company.objects.create(name="Karaca Home"), [("KRV-A", "1")],
                         date="2026-10-01", carrier="DHL Express", tracking_number="JD0146", sent=True)
        self.assertTrue(r.json()["success"], r.json())
        package = SamplePackage.objects.get()
        self.assertEqual((package.status, str(package.shipped_at), package.tracking_number),
                         ("sent", "2026-10-01", "JD0146"))
        # A carrier typed here joins the list, as one typed on an order does.
        self.assertEqual(package.carrier_name, "DHL Express")
        self.assertTrue(Carrier.objects.filter(name="DHL Express").exists())

    def test_shipping_is_filled_in_later_and_moves_no_stock(self):
        self.assertTrue(self._create(Contact.objects.create(name="Georgiana"),
                                     [("KRV-A", "1")]).json()["success"])
        package = SamplePackage.objects.get()
        moves = StockMovement.objects.count()

        r = self.client.post(reverse("operating:sample_package_shipping", args=[package.pk]),
                             data={"status": "sent", "carrier": "UPS", "tracking_number": "1Z999"})

        self.assertTrue(r.json()["success"], r.json())
        package.refresh_from_db()
        self.assertEqual((package.status, package.carrier_name, package.tracking_number),
                         ("sent", "UPS", "1Z999"))
        self.assertIsNotNone(package.shipped_at)
        self.assertEqual(StockMovement.objects.count(), moves)

    # ── finding items ────────────────────────────────────────────
    def test_items_are_found_by_barcode_or_sku_with_what_is_left(self):
        url = reverse("operating:sample_roll_search")
        by_barcode = self.client.get(url, {"q": "KRV-A"}).json()["rolls"]
        self.assertEqual([(r["barcode"], r["left"]) for r in by_barcode], [("KRV-A", 30.0)])
        by_sku = self.client.get(url, {"q": "K24644.G07"}).json()["rolls"]
        self.assertEqual({r["barcode"] for r in by_sku}, {"KRV-A", "KRV-B"})
        self.assertEqual(self.client.get(url, {"q": "K"}).json()["rolls"], [])

    # ── on the client's page ─────────────────────────────────────
    def test_the_card_gathers_a_packages_pieces_and_keeps_single_cuts_apart(self):
        karaca = Company.objects.create(name="Karaca Home")
        buyer = Contact.objects.create(name="Selin", company=karaca)
        self.assertTrue(self._create(karaca, [("KRV-A", "2"), ("KRV-B", "1")],
                                     note="autumn colours").json()["success"])
        roll = self._roll("KRV-A")
        single = self.client.post(
            reverse("operating:warehouse_roll_edit", args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": "29", "change_reason": "sample",
                  "client_type": "contact", "client_pk": buyer.pk})
        self.assertTrue(single.json()["success"], single.json())

        r = self.client.get(reverse("crm:company_detail", args=[karaca.pk]))

        self.assertEqual(r.status_code, 200)
        history = r.context["sample_history"]
        self.assertEqual([(bool(e["package"]), len(e["items"])) for e in history],
                         [(False, 1), (True, 2)])
        html = r.content.decode()
        package = SamplePackage.objects.get()
        for text in (package.number, "autumn colours", "New sample package",
                     'id="smpOverlay"', "Selin"):
            self.assertIn(text, html)

    def test_a_contacts_page_opens_with_the_form_and_no_samples(self):
        georgiana = Contact.objects.create(name="Georgiana")
        r = self.client.get(reverse("crm:contact_detail", args=[georgiana.pk]))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("No samples sent yet.", html)
        self.assertIn('CLIENT = { type: "contact", pk: "%d" }' % georgiana.pk, html)
        self.assertIn("openSamplePackage()", html)
