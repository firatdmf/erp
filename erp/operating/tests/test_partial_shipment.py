"""Part of an order ships; the rest continues on a follow-up order.

The ticked packages stay on the order, which is then completed as any
order is; every roll, line, package and unreceived purchase not going now
moves to a new open order pointing back at it. A split order splits as one.

Run with:
    scripts/test_local.sh operating.tests.test_partial_shipment
"""
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_ledger import ensure_chart
from crm.models import Contact
from marketing.models import Product, ProductCategory, ProductVariant
from operating.models import (Order, OrderAdjustment, OrderItem, OrderStockReservation, Pack,
                              Warehouse, WarehouseProduct, WarehouseProductItem)
from operating.partial_shipment import PartialShipError, split_off
from operating.views_warehouse import apply_order_status_change

CDN = "https://cdn.test/qr.png"


class PartialShipmentBase(TestCase):
    def setUp(self):
        cdn = patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
        cdn.start()
        self.addCleanup(cdn.stop)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        ensure_chart()
        self.customer = Contact.objects.create(name="Anna Lugansk")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.user = User.objects.create_user("firat", password="pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.client.force_login(self.user)
        self._n = 0

    def order(self, book, group=None):
        account, _ = CurrentAccount.objects.get_or_create(
            book=book, contact=self.customer, type="customer",
            defaults={"code": f"C-{book.pk}", "name": "Anna", "default_currency": self.usd})
        return Order.objects.create(current_account=account, contact=self.customer,
                                    currency=self.usd, split_group=group)

    def line(self, order, sku, rolls, price="2", packs=None):
        """A line of `rolls` meters each, one roll per entry, each in the
        matching package of `packs` (None = not packed)."""
        self._n += 1
        product = Product.objects.create(
            title=sku, sku=sku, price=1,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        variant = ProductVariant.objects.create(product=product, variant_sku=sku)
        item = OrderItem.objects.create(
            order=order, product=product, product_variant=variant,
            quantity=sum(Decimal(r) for r in rolls), price=Decimal(price),
            outsourced_quantity=Decimal("0"))
        book = order.current_account.book
        wh, _ = Warehouse.objects.get_or_create(name=book.name, accounting_book=book)
        wp = WarehouseProduct.objects.create(warehouse=wh, name=sku, sku=sku,
                                             quantity=Decimal("500"), catalog_variant=variant)
        for i, meters in enumerate(rolls):
            roll = WarehouseProductItem.objects.create(
                product=wp, quantity=Decimal(meters), quantity_remaining=Decimal(meters),
                barcode=f"B{self._n}-{i}")
            OrderStockReservation.objects.create(
                order=order, order_item=item, stock_item=roll, warehouse_product=wp,
                quantity=Decimal(meters), pack=(packs[i] if packs else None))
        return item

    def pack(self, order, n):
        return Pack.objects.create(order=order, pack_number=n)


class PlainOrder(PartialShipmentBase):
    def setUp(self):
        super().setUp()
        self.o = self.order(self.laleli)
        self.p1, self.p2 = self.pack(self.o, 1), self.pack(self.o, 2)
        # A: both rolls in package 1. B: one roll in each.
        self.a = self.line(self.o, "A.1", ["30", "20"], packs=[self.p1, self.p1])
        self.b = self.line(self.o, "B.1", ["10", "15"], packs=[self.p1, self.p2])
        self.delivery = OrderAdjustment.objects.create(order=self.o, label="Delivery",
                                                       amount=Decimal("150"))
        self.discount = OrderAdjustment.objects.create(order=self.o, label="Discount",
                                                       amount=Decimal("-20"))

    def test_the_ticked_package_stays_and_the_rest_moves_on(self):
        [f] = split_off(self.o, [self.p1.pk], moving_adjustments=[self.discount.pk],
                        user=self.user)
        f.refresh_from_db()
        self.assertEqual(f.continued_from_id, self.o.pk)
        self.assertNotEqual(f.order_number, self.o.order_number)
        self.assertTrue(f.order_number)
        self.assertEqual(f.current_account_id, self.o.current_account_id)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.order_id, self.a.quantity), (self.o.pk, Decimal("50")))
        self.assertEqual((self.b.order_id, self.b.quantity), (self.o.pk, Decimal("10")))
        [rest] = f.items.all()
        self.assertEqual((rest.product_variant_id, rest.quantity),
                         (self.b.product_variant_id, Decimal("15")))
        # The roll that stays behind goes with its line and package.
        self.assertEqual(list(rest.stock_reservations.values_list("quantity", flat=True)),
                         [Decimal("15")])
        self.assertEqual(list(f.stock_reservations.values_list("order_item_id", flat=True)),
                         [rest.pk])
        self.p2.refresh_from_db()
        self.assertEqual((self.p2.order_id, self.p2.pack_number), (f.pk, 2))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.order_id, self.o.pk)
        # Extra lines stay unless moved.
        self.assertEqual(list(self.o.adjustments.values_list("label", flat=True)), ["Delivery"])
        self.assertEqual(list(f.adjustments.values_list("label", flat=True)), ["Discount"])

    def test_the_shipped_order_bills_only_what_went(self):
        [f] = split_off(self.o, [self.p1.pk], user=self.user)
        ok, code = apply_order_status_change(self.o, "shipped", user=self.user,
                                             require_cargo_for_ship=False)
        self.assertTrue(ok, code)
        sale = CurrentAccountMovement.objects.get(movement_type="order_sale")
        # 60 m × 2 + delivery 150 − discount 20.
        self.assertEqual(sale.amount, Decimal("250.00"))
        f.refresh_from_db()
        self.assertEqual(f.order_status, "pending")
        self.assertFalse(f.stock_reservations.filter(consumed=True).exists())

    def test_a_line_none_of_which_ships_moves_whole(self):
        c = self.line(self.o, "C.1", ["40"], packs=[self.p2])
        split_off(self.o, [self.p1.pk], user=self.user)
        c.refresh_from_db()
        self.assertNotEqual(c.order_id, self.o.pk)
        self.assertEqual(c.stock_reservations.get().order_id, c.order_id)

    def test_refusals_leave_everything_as_it_was(self):
        with self.assertRaisesMessage(PartialShipError, "Nothing would ship"):
            split_off(self.o, [], user=self.user)
        with self.assertRaisesMessage(PartialShipError, "Everything ships"):
            split_off(self.o, [self.p1.pk, self.p2.pk], user=self.user)
        with self.assertRaisesMessage(PartialShipError, "at least"):
            split_off(self.o, [self.p1.pk], quantities={self.b.pk: "5"}, user=self.user)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.o.items.count(), 2)

    def test_a_line_without_rolls_ships_what_is_typed(self):
        d = OrderItem.objects.create(order=self.o, product=self.a.product,
                                     product_variant=self.a.product_variant,
                                     quantity=Decimal("8"), price=Decimal("1"))
        [f] = split_off(self.o, [self.p1.pk, self.p2.pk], quantities={d.pk: "3"},
                        user=self.user)
        d.refresh_from_db()
        self.assertEqual(d.quantity, Decimal("3"))
        self.assertEqual(f.items.get().quantity, Decimal("5"))

    def test_ship_ships_the_ticked_packages_and_carries_the_rest(self):
        url = reverse("operating:order_ship_part", args=[self.o.pk])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.context["pack_rows"]), 2)
        # Packages are changed on the packing screen, which leads back here.
        pack_url = reverse("operating:order_pack_scan", args=[self.o.pk]) + "?back=ship"
        self.assertContains(page, pack_url)
        self.assertContains(self.client.get(pack_url), f'href="{url}"')
        # The cargo receipt is picked, photographed or pasted (and shrunk)
        # by the same picker as on the order page.
        self.assertContains(page, "operating/js/cargo_receipts.js")
        self.assertContains(page, "paste it here")
        r = self.client.post(url, {"pack": [self.p1.pk], "tracking_number": "TRK-1"})
        self.assertRedirects(r, reverse("operating:order_detail", args=[self.o.pk]),
                             fetch_redirect_response=False)
        self.o.refresh_from_db()
        self.assertEqual((self.o.order_status, self.o.tracking_number), ("shipped", "TRK-1"))
        # Only the rolls that went are cut.
        self.assertEqual(set(self.o.stock_reservations.values_list("consumed", flat=True)), {True})
        f = Order.objects.get(continued_from=self.o)
        self.assertEqual(f.order_status, "pending")
        self.assertIsNone(f.tracking_number)
        self.assertFalse(f.stock_reservations.filter(consumed=True).exists())
        detail = self.client.get(reverse("operating:order_detail", args=[f.pk]))
        self.assertContains(detail, self.o.order_number)

    def test_a_refused_shipment_leaves_the_order_unsplit(self):
        url = reverse("operating:order_ship_part", args=[self.o.pk])
        with patch("operating.views_partial_shipment.apply_order_status_change",
                   return_value=(False, "goods_not_received")):
            r = self.client.post(url, {"pack": [self.p1.pk]})
        self.assertRedirects(r, url, fetch_redirect_response=False)
        self.assertEqual(Order.objects.count(), 1)
        self.b.refresh_from_db()
        self.assertEqual(self.b.quantity, Decimal("25"))
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.order_id, self.o.pk)

    def test_someone_without_the_book_cannot_open_it(self):
        other = User.objects.create_user("ruzana", password="pw")
        other.member.books.add(self.ergene)
        self.client.force_login(other)
        r = self.client.get(reverse("operating:order_ship_part", args=[self.o.pk]))
        self.assertEqual(r.status_code, 404)


class SplitOrder(PartialShipmentBase):
    """Anna's order: a Laleli half and an Ergene half, one run of sacks on
    the Laleli half, a sack holding both books' rolls."""

    def setUp(self):
        super().setUp()
        group = uuid.uuid4()
        self.lal = self.order(self.laleli, group)
        self.erg = self.order(self.ergene, group)
        self.p1, self.p2 = self.pack(self.lal, 1), self.pack(self.lal, 2)

    def test_a_half_that_ships_whole_gets_no_follow_up(self):
        self.line(self.lal, "L.1", ["30"], packs=[self.p1])
        late = self.line(self.lal, "L.2", ["25"], packs=[self.p2])
        self.line(self.erg, "E.1", ["20"], packs=[self.p1])
        [f] = split_off(self.erg, [self.p1.pk], user=self.user)
        self.assertEqual(f.continued_from_id, self.lal.pk)
        self.assertEqual(list(f.items.values_list("pk", flat=True)), [late.pk])
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.order_id, f.pk)
        # The two halves still go out together; the follow-up is one order.
        self.lal.refresh_from_db()
        self.erg.refresh_from_db()
        self.assertEqual(self.lal.split_group, self.erg.split_group)
        self.assertIsNotNone(self.lal.split_group)
        f.refresh_from_db()
        self.assertIsNone(f.split_group)

    def test_both_halves_continue_as_one_follow_up(self):
        self.line(self.lal, "L.1", ["30", "10"], packs=[self.p1, self.p2])
        self.line(self.erg, "E.1", ["20", "5"], packs=[self.p1, self.p2])
        follow = split_off(self.lal, [self.p1.pk], user=self.user)
        self.assertEqual(len(follow), 2)
        for f in follow:
            f.refresh_from_db()
        self.assertEqual(follow[0].split_group, follow[1].split_group)
        self.assertIsNotNone(follow[0].split_group)
        self.assertEqual({f.current_account.book_id for f in follow},
                         {self.laleli.pk, self.ergene.pk})
        self.assertEqual(sorted(f.items.get().quantity for f in follow),
                         [Decimal("5"), Decimal("10")])

    def test_a_half_none_of_which_ships_joins_the_follow_up(self):
        self.line(self.lal, "L.1", ["30", "10"], packs=[self.p1, self.p2])
        e = self.line(self.erg, "E.1", ["20"], packs=[self.p2])
        follow = split_off(self.lal, [self.p1.pk], user=self.user)
        self.assertIn(self.erg.pk, [f.pk for f in follow])
        self.erg.refresh_from_db()
        self.lal.refresh_from_db()
        self.assertEqual(self.erg.continued_from_id, self.lal.pk)
        self.assertIsNone(self.lal.split_group)
        f_lal = next(f for f in follow if f.pk != self.erg.pk)
        f_lal.refresh_from_db()
        self.assertEqual(f_lal.split_group, self.erg.split_group)
        self.assertEqual(Order.objects.get(pk=self.erg.pk).items.get().pk, e.pk)
