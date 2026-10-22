"""The mini packing list stuck on each package: its contents added up per
SKU, and the label PDFs for one package and for the whole order."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import Product, ProductCategory
from operating import pack_label
from operating.models import (Order, OrderItem, OrderStockReservation, Pack, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


class PackLabel(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.wh = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.order = Order.objects.create(order_number="ORD-2026-000347")
        self.pack1 = Pack.objects.create(order=self.order, pack_number=1)
        self.pack2 = Pack.objects.create(order=self.order, pack_number=2)

        bergamo = self._line("Bergamo", "BRG-01", "m")
        towel = self._line("Towel", "TWL-WHITE", "piece")
        self._reserve(bergamo, "BC1", Decimal("40.00"), self.pack1)
        self._reserve(bergamo, "BC2", Decimal("12.50"), self.pack1)
        self._reserve(towel, "BC3", Decimal("22"), self.pack1)
        self._reserve(bergamo, "BC4", Decimal("25.00"), self.pack2)

        self.client.force_login(User.objects.create_superuser("packer", "p@a.b", "pw"))

    def _line(self, title, sku, unit):
        product = Product.objects.create(
            title=title, sku=sku, price=10, unit=unit,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        wp = WarehouseProduct.objects.create(
            warehouse=self.wh, name=title, sku=sku, quantity=Decimal("100.00"))
        item = OrderItem.objects.create(order=self.order, product=product,
                                        quantity=Decimal("100.00"), price=10)
        return item, wp

    def _reserve(self, line, barcode, quantity, pack):
        item, wp = line
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=quantity, quantity_remaining=quantity, barcode=barcode)
        OrderStockReservation.objects.create(
            order=self.order, order_item=item, stock_item=roll,
            warehouse_product=wp, quantity=quantity, pack=pack)

    def test_rolls_of_one_sku_are_added_up(self):
        lines = pack_label._pack_lines(self.pack1)
        self.assertEqual([(l["sku"], l["items"], l["quantity"]) for l in lines],
                         [("BRG-01", 2, Decimal("52.50")), ("TWL-WHITE", 1, Decimal("22"))])
        self.assertEqual(pack_label._describe(2, Decimal("52.50"), "m", "roll"), "2 rolls · 52.50 m")
        self.assertEqual(pack_label._total(lines), "2 rolls · 52.50 m · 22 pcs")

    def test_one_package_prints_one_label(self):
        resp = self.client.get(reverse("operating:pack_label", kwargs={"pack_pk": self.pack1.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertEqual(resp.content.count(b"/Type /Page\n"), 1)

    def test_the_order_prints_a_label_per_package(self):
        resp = self.client.get(reverse("operating:order_pack_labels", kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.count(b"/Type /Page\n"), 2)

    def test_a_package_too_full_for_one_label_runs_onto_a_second(self):
        with patch.object(pack_label, "LINES_PER_LABEL", 1):
            pdf = pack_label.labels_pdf_bytes([self.pack1], title="t")
        self.assertEqual(pdf.count(b"/Type /Page\n"), 2)
