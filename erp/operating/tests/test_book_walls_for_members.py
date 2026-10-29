"""A member of one book reaches nothing of another's from the operating side.

Each of these served every book to whoever asked: the purchase forms
offered every directory's suppliers and products (a ModelForm builds its
choices at import, outside the request the wall reads), the raw-material
receipt offered — and saved into — every book, and the order APIs and
QR sheet opened any order by id, some to visitors not signed in at all.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from crm.models import Supplier
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem, PurchaseOrder, RawMaterialGoodReceipt


class BookWallsForMembers(TestCase):
    @classmethod
    def setUpTestData(cls):
        # A new book gets a directory of its own, so these two share no
        # suppliers or products.
        cls.almaty = Book.objects.create(name="Almaty Branch")
        cls.laleli = Book.objects.create(name="Laleli Shopfront")
        cls.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")

        cls.own_supplier = Supplier.objects.create(
            company_name="Steppe Weavers", directory=cls.almaty.directory)
        cls.other_supplier = Supplier.objects.create(
            company_name="Bosphorus Mills", directory=cls.laleli.directory)
        cls.own_product = Product.objects.create(
            title="Steppe Linen", sku="STEPPE-LINEN", directory=cls.almaty.directory)
        cls.other_product = Product.objects.create(
            title="Bosphorus Tulle", sku="BOSPHORUS-TULLE", directory=cls.laleli.directory)

        cls.own_order = cls.order_in(cls.almaty, "ALM-1")
        cls.other_order = cls.order_in(cls.laleli, "LAL-1")
        cls.other_line = OrderItem.objects.create(
            order=cls.other_order, product=cls.other_product,
            product_variant=ProductVariant.objects.create(
                product=cls.other_product, variant_sku="BOSPHORUS-TULLE.1"),
            quantity=Decimal("3"), price=Decimal("7.50"))
        cls.own_line = OrderItem.objects.create(
            order=cls.own_order, product=cls.own_product,
            product_variant=ProductVariant.objects.create(
                product=cls.own_product, variant_sku="STEPPE-LINEN.1"),
            quantity=Decimal("3"), price=Decimal("7.50"))
        # From the storefront: no current account, so no book.
        cls.web_order = Order.objects.create(order_status="pending", is_guest_order=True)

        cls.user = User.objects.create_user("burak_op_walls", password="pw")
        member = cls.user.member
        member.books.set([cls.almaty])
        member.default_book = cls.almaty
        member.save(update_fields=["default_book"])
        # A branch's manager: what the Middle manager role is made of.
        member.permissions.add(*[Permission.objects.get_or_create(name=n)[0] for n in
                                 ("admin", "purchase_confirm", "view_profit", "print_labels")])

    @classmethod
    def order_in(cls, book, code):
        account = CurrentAccount.objects.create(
            book=book, code=code, name=f"Customer {code}", type="customer",
            default_currency=cls.usd)
        return Order.objects.create(current_account=account, order_status="pending")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    # ── Purchase forms ──────────────────────────────────────────────

    def test_the_purchase_order_form_offers_only_her_suppliers(self):
        for path in ("/operating/procurement/orders/create/",
                     "/operating/procurement/orders/create/partial/"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertContains(page, "Steppe Weavers")
                self.assertNotContains(page, "Bosphorus Mills")

    def test_a_purchase_order_for_another_books_supplier_is_refused(self):
        response = self.client.post("/operating/procurement/orders/create/partial/", {
            "supplier": self.other_supplier.pk, "currency": "USD",
            "items-TOTAL_FORMS": "0", "items-INITIAL_FORMS": "0",
        })
        self.assertFalse(response.json()["success"])
        self.assertIn("supplier", response.json()["errors"])
        self.assertFalse(PurchaseOrder.everywhere.exists())

    def test_the_purchase_request_form_offers_only_her_products(self):
        for path in ("/operating/procurement/requests/create/",
                     "/operating/procurement/requests/create/partial/"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertContains(page, "STEPPE-LINEN")
                self.assertNotContains(page, "BOSPHORUS-TULLE")

    # ── Raw-material receipt ────────────────────────────────────────

    def test_the_receipt_form_offers_only_her_books_and_suppliers(self):
        for path in ("/operating/raw_material_good_receipt/create",
                     "/operating/raw_material_good_receipt/create/partial"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertContains(page, "Almaty Branch")
                self.assertNotContains(page, "Laleli Shopfront")
                self.assertContains(page, "Steppe Weavers")
                self.assertNotContains(page, "Bosphorus Mills")

    def test_a_receipt_into_another_book_is_refused(self):
        response = self.client.post("/operating/raw_material_good_receipt/create/json", {
            "book": self.laleli.pk, "supplier": self.own_supplier.pk,
            "receipt_number": "R-1",
        })
        self.assertFalse(response.json()["success"])
        self.assertIn("book", response.json()["field_errors"])
        self.assertFalse(RawMaterialGoodReceipt.objects.exists())

    def test_a_receipt_into_her_own_book_saves(self):
        response = self.client.post("/operating/raw_material_good_receipt/create/json", {
            "book": self.almaty.pk, "supplier": self.own_supplier.pk,
            "receipt_number": "R-2",
        })
        self.assertTrue(response.json()["success"], response.json())

    # ── Order routes ────────────────────────────────────────────────

    def test_another_books_order_is_not_found(self):
        other = self.other_order.pk
        for method, path in (
                ("get", f"/operating/api/get_order_status/{other}/"),
                ("get", f"/operating/generate_pdf_qr_for_order_item_units/{self.other_line.pk}/"),
                ("get", f"/operating/api/get_order_detail/1/{other}/"),
                ("post", f"/operating/orders/{other}/update-status/"),
                ("patch", f"/operating/orders/{other}/update-ettn/")):
            with self.subTest(path=path):
                self.assertEqual(getattr(self.client, method)(path).status_code, 404)

    def test_her_own_books_order_still_answers(self):
        # One without lines: the status API reads each line's product
        # category, which these test products do not have.
        bare = self.order_in(self.almaty, "ALM-2")
        self.assertEqual(
            self.client.get(f"/operating/api/get_order_status/{bare.pk}/").status_code, 200)
        self.assertEqual(self.client.get(
            f"/operating/generate_pdf_qr_for_order_item_units/{self.own_line.pk}/").status_code, 200)

    def test_nobody_signed_out_reaches_an_order(self):
        anonymous = Client()
        own = self.own_order.pk
        for method, path in (
                ("get", f"/operating/api/get_order_status/{own}/"),
                ("get", f"/operating/generate_pdf_qr_for_order_item_units/{self.own_line.pk}/"),
                ("post", f"/operating/orders/{own}/update-status/"),
                ("patch", f"/operating/orders/{own}/update-ettn/")):
            with self.subTest(path=path):
                response = getattr(anonymous, method)(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/authentication/signin", response["Location"])
        self.own_order.refresh_from_db()
        self.assertEqual(self.own_order.order_status, "pending")

    def test_a_web_order_is_the_install_admins(self):
        path = f"/operating/orders/web/{self.web_order.pk}/status/"
        self.assertEqual(self.client.get(path).status_code, 404)
        boss = User.objects.create_superuser("boss_op_walls", password="pw")
        admin = Client()
        admin.force_login(boss)
        self.assertEqual(admin.get(path).status_code, 200)
