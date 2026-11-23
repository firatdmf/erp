"""Weights for export papers: a roll's own kilos when its label gave them,
else what its variant's weighed rolls say, else the fabric's GSM over its
width, else nothing; the sack's weight off
the scale; and the packing list's net and gross totals."""
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import openpyxl
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import (Product, ProductCategory, ProductVariant,
                              ProductVariantAttribute,
                              ProductVariantAttributeValue)
from operating.models import (Order, OrderItem, OrderStockReservation, Pack,
                              Warehouse, WarehouseProduct, WarehouseProductItem)
from operating.views import _order_weights, _pack_roll_rows, _pack_weights
from operating.views_warehouse import _add_stock_to_variant
from operating.weights import measured_gsm, net_kg


def _value(attr_name, value):
    attr, _ = ProductVariantAttribute.objects.get_or_create(name=attr_name)
    row, _ = ProductVariantAttributeValue.objects.get_or_create(
        product_variant_attribute=attr, product_variant_attribute_value=value)
    return row


class NetKg(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="Velvet", sku="VEL", unit="m",
                                              gsm=Decimal("320"))
        self.variant = ProductVariant.objects.create(product=self.product,
                                                     variant_sku="VEL.RED-280")
        self.variant.product_variant_attribute_values.add(_value("width", "280"))
        wh = Warehouse.objects.create(
            name="WH", accounting_book=Book.objects.get_or_create(name="Laleli")[0])
        self.wp = WarehouseProduct.objects.create(warehouse=wh, name="Velvet", sku="VEL.RED-280")

    def roll(self, weight=None):
        return WarehouseProductItem.objects.create(unit_cost_base=Decimal("1"),
            product=self.wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            weight_kg=weight)

    def test_a_weighed_roll_shares_its_weight_by_length(self):
        self.assertEqual(net_kg(Decimal("30"), self.roll(Decimal("45")), self.product, self.variant),
                         (Decimal("27.00"), False))

    def test_an_unweighed_roll_is_worked_out_from_gsm_and_width(self):
        # 0.32 kg/m² × 2.8 m × 30 m
        self.assertEqual(net_kg(Decimal("30"), self.roll(), self.product, self.variant),
                         (Decimal("26.88"), True))

    def test_nothing_known_is_none_not_zero(self):
        self.product.gsm = None
        self.assertEqual(net_kg(Decimal("30"), self.roll(), self.product, self.variant),
                         (None, False))

    def test_no_width_no_estimate(self):
        self.variant.product_variant_attribute_values.clear()
        self.assertEqual(net_kg(Decimal("30"), self.roll(), self.product, self.variant),
                         (None, False))

    def test_goods_counted_in_pieces_are_not_estimated(self):
        self.product.unit = "piece"
        self.assertEqual(net_kg(Decimal("3"), self.roll(), self.product, self.variant),
                         (None, False))


class MeasuredWeights(TestCase):
    """No label weight on an item: the same variant's weighed items say
    what it weighs, before any typed GSM; the product page shows the GSM
    they work out to."""

    def setUp(self):
        self.product = Product.objects.create(title="Bamboo", sku="BAM", unit="m")
        wh = Warehouse.objects.create(
            name="WH", accounting_book=Book.objects.get_or_create(name="Laleli")[0])
        self.variants, self.wps = {}, {}
        for sku in ("BAM.ECRU-305", "BAM.WHITE-305"):
            v = ProductVariant.objects.create(product=self.product, variant_sku=sku)
            v.product_variant_attribute_values.add(_value("width", "305"))
            self.variants[sku] = v
            self.wps[sku] = WarehouseProduct.objects.create(
                warehouse=wh, name=sku, sku=sku, catalog_variant=v)

    def roll(self, sku, qty, weight=None, status="in_stock"):
        return WarehouseProductItem.objects.create(
            unit_cost_base=Decimal("1"), product=self.wps[sku], quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), weight_kg=weight, status=status)

    def fresh(self, sku):
        return ProductVariant.objects.get(variant_sku=sku)

    def test_an_unweighed_roll_takes_its_variants_median_kg_per_meter(self):
        self.roll("BAM.ECRU-305", "50", Decimal("8.3"))
        self.roll("BAM.ECRU-305", "50", Decimal("8.4"))
        self.roll("BAM.ECRU-305", "36", Decimal("6"), status="consumed")  # used up, still weighed
        # Another variant's rolls are another cloth.
        self.roll("BAM.WHITE-305", "50", Decimal("20"))
        # Median of 0.166, 0.168, 0.1667 kg/m = 0.1667 × 30 m.
        self.assertEqual(net_kg(Decimal("30"), self.roll("BAM.ECRU-305", "50"),
                                self.product, self.fresh("BAM.ECRU-305")),
                         (Decimal("5.00"), True))

    def test_the_variants_weighed_rolls_come_before_a_typed_gsm(self):
        self.product.gsm = Decimal("320")
        self.roll("BAM.ECRU-305", "50", Decimal("8.3"))
        self.assertEqual(net_kg(Decimal("30"), self.roll("BAM.ECRU-305", "50"),
                                self.product, self.fresh("BAM.ECRU-305")),
                         (Decimal("4.98"), True))

    def test_no_weighed_roll_falls_back_to_gsm(self):
        self.product.gsm = Decimal("54")
        # 0.054 kg/m² × 3.05 m × 30 m
        self.assertEqual(net_kg(Decimal("30"), self.roll("BAM.ECRU-305", "50"),
                                self.product, self.fresh("BAM.ECRU-305")),
                         (Decimal("4.94"), True))

    def test_measured_gsm_is_the_median_over_every_variant(self):
        self.roll("BAM.ECRU-305", "50", Decimal("8.3"))   # 54.4
        self.roll("BAM.WHITE-305", "50", Decimal("8.4"))  # 55.1
        self.roll("BAM.WHITE-305", "52", Decimal("8.6"))  # 54.2
        self.roll("BAM.WHITE-305", "50")                  # not weighed
        self.assertEqual(measured_gsm(self.product), (Decimal("54"), 3))

    def test_measured_gsm_needs_a_width_and_meters(self):
        self.roll("BAM.ECRU-305", "50", Decimal("8.3"))
        self.product.unit = "piece"
        self.assertEqual(measured_gsm(self.product), (None, 0))
        self.product.unit = "m"
        for v in self.variants.values():
            v.product_variant_attribute_values.clear()
        self.assertEqual(measured_gsm(self.product), (None, 0))

    def test_the_product_page_shows_it_when_none_is_typed(self):
        self.client.force_login(User.objects.create_superuser("g", "g@t.com", "pw"))
        self.roll("BAM.ECRU-305", "50", Decimal("8.3"))
        url = reverse("marketing:product_detail", kwargs={"pk": self.product.pk})
        page = self.client.get(url).content.decode()
        self.assertIn("≈ 54", page)
        self.assertIn("from 1 weighed roll", page)
        self.product.gsm = Decimal("60")
        self.product.save(update_fields=["gsm"])
        gsm_item = self.client.get(url).content.decode().split("GSM (g/m²)", 1)[1][:120]
        self.assertIn("60", gsm_item)
        self.assertNotIn("≈", gsm_item)
        edit = self.client.get(reverse("marketing:product_edit", kwargs={"pk": self.product.pk}))
        self.assertContains(edit, "≈ 54 g/m²")


class PackingListWeights(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.client.force_login(User.objects.create_superuser("w", "w@t.com", "pw"))
        fabric = ProductCategory.objects.create(name="fabric")
        product = Product.objects.create(title="Velvet", sku="VEL", unit="m",
                                         gsm=Decimal("320"), category=fabric)
        variant = ProductVariant.objects.create(product=product, variant_sku="VEL.RED-280")
        variant.product_variant_attribute_values.add(_value("width", "280"))
        wh = Warehouse.objects.create(
            name="WH", accounting_book=Book.objects.get_or_create(name="Laleli")[0])
        wp = WarehouseProduct.objects.create(warehouse=wh, name="Velvet", sku="VEL.RED-280")
        self.order = Order.objects.create(order_number="DK0000900")
        item = OrderItem.objects.create(order=self.order, product=product,
                                        product_variant=variant, quantity=60, price=10)
        self.pack = Pack.objects.create(order=self.order, pack_number=1)
        for code, weight in (("R1", Decimal("45")), ("R2", None)):
            roll = WarehouseProductItem.objects.create(unit_cost_base=Decimal("1"),
                product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
                barcode=code, weight_kg=weight)
            OrderStockReservation.objects.create(
                order=self.order, order_item=item, stock_item=roll,
                warehouse_product=wp, quantity=Decimal("30"), pack=self.pack)

    def test_rows_and_package_add_up(self):
        rows = _pack_roll_rows(self.pack)
        self.assertEqual([(r["net_kg"], r["net_kg_estimated"]) for r in rows],
                         [(Decimal("27.00"), False), (Decimal("26.88"), True)])
        w = _pack_weights(self.pack, rows)
        self.assertEqual((w["net_kg"], w["net_kg_estimated"], w["gross_kg"]),
                         (Decimal("53.88"), True, None))

    def test_an_order_total_is_none_while_a_sack_is_unweighed(self):
        w = _pack_weights(self.pack, _pack_roll_rows(self.pack))
        self.assertEqual(_order_weights([w]), (Decimal("53.88"), None))
        self.pack.gross_kg = Decimal("55.5")
        w = _pack_weights(self.pack, _pack_roll_rows(self.pack))
        self.assertEqual(_order_weights([w]), (Decimal("53.88"), Decimal("55.5")))

    def test_an_unweighed_empty_sack_is_left_out(self):
        empty = Pack.objects.create(order=self.order, pack_number=2)
        self.pack.gross_kg = Decimal("55.5")
        weights = [_pack_weights(p, _pack_roll_rows(p)) for p in (self.pack, empty)]
        self.assertEqual(_order_weights(weights), (Decimal("53.88"), Decimal("55.5")))

    def test_the_packer_types_the_sack_weight(self):
        url = reverse("operating:order_packing_list", kwargs={"pk": self.order.pk})
        r = self.client.post(url, {"action": "set_gross_kg", "pack_id": self.pack.pk,
                                   "gross_kg": "55,5"})
        self.assertEqual(r.json(), {"ok": True, "gross_kg": "55.50"})
        self.pack.refresh_from_db()
        self.assertEqual(self.pack.gross_kg, Decimal("55.50"))
        r = self.client.post(url, {"action": "set_gross_kg", "pack_id": self.pack.pk,
                                   "gross_kg": ""})
        self.pack.refresh_from_db()
        self.assertIsNone(self.pack.gross_kg)

    def test_nonsense_is_refused(self):
        url = reverse("operating:order_packing_list", kwargs={"pk": self.order.pk})
        for bad in ("heavy", "-3", "0"):
            r = self.client.post(url, {"action": "set_gross_kg", "pack_id": self.pack.pk,
                                       "gross_kg": bad})
            self.assertEqual(r.status_code, 400, bad)

    def test_the_excel_carries_net_and_gross(self):
        Pack.objects.filter(pk=self.pack.pk).update(gross_kg=Decimal("55.5"))
        r = self.client.get(reverse("operating:export_packing_list_excel",
                                    kwargs={"pk": self.order.pk}))
        ws = openpyxl.load_workbook(BytesIO(r.content)).active
        self.assertEqual([c.value for c in ws[7]][8:10], ["Net kg", "Gross kg"])
        self.assertEqual([ws.cell(row=8, column=9).value, ws.cell(row=9, column=9).value],
                         [27.0, 26.88])
        self.assertEqual(ws.cell(row=8, column=10).value, 55.5)
        totals = {ws.cell(row=r, column=9).value: ws.cell(row=r, column=10).value
                  for r in range(10, ws.max_row + 1)}
        self.assertEqual((totals["Total Net kg"], totals["Total Gross kg"]), (53.88, 55.5))

    def test_the_page_and_pdf_render(self):
        page = self.client.get(reverse("operating:order_packing_list",
                                       kwargs={"pk": self.order.pk}))
        self.assertContains(page, "~26.88 kg")
        pdf = self.client.get(reverse("operating:order_packing_list_pdf",
                                      kwargs={"pk": self.order.pk}))
        self.assertTrue(pdf.content.startswith(b"%PDF"))


class ReceiptRollWeight(TestCase):
    def test_a_roll_keeps_the_weight_its_label_gave(self):
        wh = Warehouse.objects.create(
            name="WH", accounting_book=Book.objects.get_or_create(name="Laleli")[0])
        wp = WarehouseProduct.objects.create(warehouse=wh, name="Velvet", sku="VEL.RED-280",
                                             cost_usd=Decimal("2.00"))
        codes = iter(["A1", "A2"])
        _added, ids = _add_stock_to_variant(
            wp, [{"qty": 50, "weight_kg": "45,2"}, {"qty": 40, "weight_kg": None}],
            lambda: next(codes), None)
        self.assertEqual(
            list(WarehouseProductItem.objects.filter(pk__in=ids).order_by("pk")
                 .values_list("weight_kg", flat=True)),
            [Decimal("45.20"), None])
