"""Packing an order without its prices or customer.

A role holding Orders but not Prices and customers — Operations — packs
and ships: the packing screen, the packing list and its exports, the
picking list and the partial shipment all open and work for it, and none
of them names the customer or a price. Where the sacks go (the delivery
details) is what it is shown instead. A role with the permission sees what
it always did. See erp.roles.sees_order_money.

Run with:
    python manage.py test operating.tests.test_order_money_hidden_packing
"""
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import openpyxl
import reportlab.platypus
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Contact
from marketing.models import Product, ProductCategory, ProductVariant
from operating.models import Order, OrderAdjustment, OrderItem, Pack

CDN = "https://cdn.test/qr.png"
CUSTOMER = "Zircon Buyer Ltd"
EMAIL = "orders@zircon-buyer.test"
PRICE = "1234.56"
DELIVERY = "Quartz Street 9"


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class PackingWithoutPricesOrCustomer(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
    def setUp(self, _upload):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric")
        customer = Contact.objects.create(name=CUSTOMER, email=[EMAIL])
        account = CurrentAccount.objects.create(
            book=self.book, code="C-ZIRCON", name=CUSTOMER, type="customer",
            contact=customer, default_currency=usd)
        self.order = Order.objects.create(
            order_number="ORD-2026-000901", current_account=account, contact=customer,
            currency=usd, status="preparing",
            delivery_address_title="Zircon depot", delivery_address=DELIVERY,
            delivery_city="Tbilisi", delivery_phone="+995 555 000")
        product = Product.objects.create(
            title="Sheer Voile", sku="SHEER-1", price=1,
            category=ProductCategory.objects.get_or_create(name="fabric")[0])
        variant = ProductVariant.objects.create(product=product, variant_sku="SHEER-1.WHITE")
        self.item = OrderItem.objects.create(
            order=self.order, product=product, product_variant=variant,
            quantity=Decimal("12"), price=Decimal(PRICE))
        self.pack = Pack.objects.create(order=self.order, pack_number=1)

    def sign_in(self, name, *grants):
        user = User.objects.create_user(name, password="pw")
        user.member.books.add(self.book)
        for grant in grants:
            user.member.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        self.client.force_login(user)
        return user

    def operations(self):
        # The Operations role: its grants, and the restriction of the one it
        # leaves out (authentication.member_roles).
        return self.sign_in("mustafa", "orders", "beyond_sales", "print_labels", "packing_only")

    def staff(self):
        return self.sign_in("cuma", "orders", "beyond_sales", "print_labels", "prices_customers")

    def get(self, name, **query):
        response = self.client.get(reverse(f"operating:{name}", args=[self.order.pk]), query)
        self.assertEqual(response.status_code, 200, name)
        return response

    def excel_text(self):
        book = openpyxl.load_workbook(BytesIO(self.get("export_packing_list_excel").content))
        return " ".join(str(c.value) for ws in book for row in ws.iter_rows() for c in row
                        if c.value is not None)

    def pdf_text(self):
        """Every paragraph the PDF is built from — its text is not readable
        in the bytes, the font being embedded."""
        seen = []
        original = reportlab.platypus.Paragraph

        def recording(text, *args, **kwargs):
            seen.append(str(text))
            return original(text, *args, **kwargs)

        with patch.object(reportlab.platypus, "Paragraph", recording):
            self.get("order_packing_list_pdf")
        return " ".join(seen)

    def assert_nothing_of_the_sale(self, text, where):
        for secret in (CUSTOMER, EMAIL, PRICE, "1,234.56", "1.234,56"):
            self.assertNotIn(secret, text, f"{where} shows {secret}")

    def test_operations_packs_without_seeing_the_customer_or_a_price(self, _upload):
        self.operations()
        for name in ("order_pack_scan", "order_packing_list", "order_ship_part"):
            with self.subTest(page=name):
                self.assert_nothing_of_the_sale(self.get(name).content.decode(), name)
        # A printed document: ?html=1 is the same template as a page.
        self.assert_nothing_of_the_sale(
            self.get("order_picking_list", html=1).content.decode(), "picking list")
        self.assert_nothing_of_the_sale(self.excel_text(), "Excel")
        self.assert_nothing_of_the_sale(self.pdf_text(), "PDF")

    def test_operations_is_told_where_the_goods_go(self, _upload):
        self.operations()
        self.assertContains(self.get("order_packing_list"), DELIVERY)
        self.assertIn(DELIVERY, self.excel_text())
        self.assertIn(DELIVERY, self.pdf_text())

    def test_operations_still_packs(self, _upload):
        self.operations()
        response = self.client.post(
            reverse("operating:order_pack_assign_item", args=[self.order.pk]),
            {"item_id": self.item.pk, "pack_id": self.pack.pk})
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.pack_id, self.pack.pk)

    def test_an_extra_line_shows_no_amount_to_operations(self, _upload):
        OrderAdjustment.objects.create(order=self.order, label="Cargo fee", amount=Decimal("77.25"))
        self.operations()
        page = self.get("order_ship_part").content.decode()
        self.assertIn("Cargo fee", page)
        self.assertNotIn("77.25", page)
        self.staff()
        self.assertContains(self.get("order_ship_part"), "77.25")

    def test_staff_sees_the_customer_as_before(self, _upload):
        self.staff()
        page = self.get("order_packing_list").content.decode()
        self.assertNotIn(DELIVERY, page)  # nothing added for them
        self.assertIn(CUSTOMER, self.excel_text())
        self.assertIn(CUSTOMER, self.pdf_text())
