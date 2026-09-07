"""The orders list's search box matches what it says it matches.

The box reads "Search order no, customer, product…" but the row carried
a data-search attribute holding only the order id, the order number and
a contact/company/web_client name — so typing a product name emptied the
list, and a walk-in sale, which has none of those three, could not be
found by its customer at all. The filter runs in the browser over what
the page shipped, so anything absent from that attribute is unfindable.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import Product, ProductVariant
from operating.models import Order, OrderItem
from operating.views import _order_search_index


class OrderListSearchIndexTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.current_account = CurrentAccount.objects.create(
            book=self.book, code="CARI-078", name="PERAKENDE",
            type="customer", default_currency=self.usd)
        self.product = Product.objects.create(
            title="Bamboo Plise", sku="TTEMPILISE", featured=False)
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="K24649.G34",
)

        self.order = Order.objects.create(
            order_number="DK-501", current_account=self.current_account, is_retail_order=True)
        OrderItem.objects.create(
            order=self.order, product=self.product,
            product_variant=self.variant,
            quantity=Decimal("12"), price=Decimal("4.50"))

        User = get_user_model()
        self.member = User.objects.create_user("rep", password="pw")
        self.member.member.books.add(self.book)
        self.member.member.default_book = self.book
        self.member.member.save()

    def _index(self):
        return _order_search_index(Order.objects.get(pk=self.order.pk))

    def test_the_order_number_is_searchable(self):
        self.assertIn("DK-501", self._index())

    def test_the_product_title_is_searchable(self):
        self.assertIn("Bamboo Plise", self._index())

    def test_the_product_sku_is_searchable(self):
        self.assertIn("TTEMPILISE", self._index())

    def test_the_variant_sku_is_searchable(self):
        self.assertIn("K24649.G34", self._index())

    def test_a_walk_in_is_searchable_by_the_current_account_it_posts_to(self):
        """A retail order has no contact, company or web client. Its
        customer identity IS the shared Perakende account, so the name
        and the code both have to be in the haystack."""
        index = self._index()
        self.assertIn("PERAKENDE", index)
        self.assertIn("CARI-078", index)

    def test_a_named_customer_is_searchable(self):
        from crm.models import Contact
        contact = Contact.objects.create(name="Hakan Taşçı")
        self.order.contact = contact
        self.order.save()
        self.assertIn("Hakan Taşçı", self._index())

    def test_every_tab_indexes_the_same_row(self):
        """The panes are the same orders under different headings. A row
        that the query finds under "All Orders" has to be findable under
        "Retail" too, so each pane's anchor carries the index — not just
        the first one."""
        self.client.force_login(self.member)
        html = self.client.get(reverse(
            "operating:order_list_scoped",
            kwargs={"book_id": self.book.pk})).content.decode()
        # One row in the All pane, one in Retail — both carrying products.
        self.assertEqual(html.count("TTEMPILISE"), 2)
