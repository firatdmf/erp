"""Several of one customer's orders on one printable sheet.

A customer who buys from two divisions holds an account in each book —
that is how the ledger is built, and it is right: their money posts in
two places. But they are one person, and asking them to read three
separate sheets for three orders is the ledger's shape leaking onto the
customer's desk.

So: tick the orders on the contact page, print them together. The sheet
records NOTHING — no invoice, no ledger row — which is exactly what lets
it cross books: the receivable stays on each order, in the book it
belongs to, and this is only the page the customer reads.

Run:
    python manage.py test operating.test_order_print_combined
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from crm.models import Contact
from marketing.models import Product

from .models import Order, OrderItem

User = get_user_model()


class OlegOrders:
    """Three orders for one customer across two books — the split that
    sent this customer three documents. Shared by the printed sheet and
    the Excel of it, which are one document in two formats."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        self.oleg = Contact.objects.create(name="OLEG MOTUZENKO")
        self.someone_else = Contact.objects.create(name="BURSA TEKSTIL")

        self.crepe = Product.objects.create(title="Crepe", sku="KZL000315", price=10)

        # Two Laleli orders and one from the factory — the split that
        # sent this customer three documents.
        self.laleli_a = self._order(self.laleli, self.oleg, "DK-284",
                                    Decimal("156.00"), Decimal("2.50"))
        self.laleli_b = self._order(self.laleli, self.oleg, "DK-275",
                                    Decimal("40.00"), Decimal("4.41"))
        self.ergene_a = self._order(self.ergene, self.oleg, "DK-291",
                                    Decimal("19.50"), Decimal("4.50"))

        self.boss = User.objects.create_superuser("boss", "b@t.com", "pw")
        self.client.force_login(self.boss)
        self.url = reverse(self.url_name)

    def _order(self, book, contact, number, qty, price):
        cari, _ = CariAccount.objects.get_or_create(
            book=book, contact=contact,
            defaults=dict(code=f"C-{book.pk}-{contact.pk}", name=contact.name,
                          type="customer", default_currency=self.usd))
        order = Order.objects.create(order_number=number, cari=cari,
                                     contact=contact)
        OrderItem.objects.create(order=order, product=self.crepe,
                                 quantity=qty, price=price)
        return order

    def _get(self, *orders):
        ids = ",".join(str(o.pk) for o in orders)
        return self.client.get(self.url, {"ids": ids})


class CombinedOrderSheet(OlegOrders, TestCase):
    url_name = "operating:order_print_combined"

    # ── what it prints ────────────────────────────────────────────────
    def test_it_totals_every_order_on_the_sheet(self):
        """156.00×2.50 + 40.00×4.41 + 19.50×4.50 = 390.00 + 176.40 + 87.75."""
        resp = self._get(self.laleli_a, self.laleli_b, self.ergene_a)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["order_total"], Decimal("654.15"))
        self.assertEqual(resp.context["order_total_quantity"], Decimal("215.50"))
        self.assertContains(resp, "$654.15")

    def test_each_order_is_named_above_its_own_lines(self):
        """Three orders on one page, and the customer can still tell
        which line came from which."""
        resp = self._get(self.laleli_a, self.laleli_b, self.ergene_a)
        for number in ("DK-284", "DK-275", "DK-291"):
            self.assertContains(resp, number)
        self.assertEqual([g["order"].pk for g in resp.context["order_groups"]],
                         [self.laleli_a.pk, self.laleli_b.pk, self.ergene_a.pk])

    def test_it_spans_books(self):
        """The whole point. An Invoice cannot do this — its book is the
        book its money posts to — but this sheet posts nothing."""
        resp = self._get(self.laleli_a, self.ergene_a)
        self.assertEqual(resp.status_code, 200)
        books = {g["order"].cari.book.name for g in resp.context["order_groups"]}
        self.assertEqual(books, {"Laleli Fabric", "Ergene Fabric"})

    def test_it_writes_nothing(self):
        """No invoice is raised and no ledger row written. The
        receivable already sits on each order; a document that posted
        again would claim the same money twice."""
        from accounting.models_accounts import CariMovement, Invoice
        before = (Invoice.objects.count(), CariMovement.objects.count())
        self._get(self.laleli_a, self.laleli_b, self.ergene_a)
        self.assertEqual(
            (Invoice.objects.count(), CariMovement.objects.count()), before)

    # ── what it refuses ───────────────────────────────────────────────
    def test_two_customers_cannot_share_a_sheet(self):
        """The orders are named by id in a URL anyone can retype. One
        sheet is addressed to one customer."""
        theirs = self._order(self.laleli, self.someone_else, "DK-999",
                             Decimal("10"), Decimal("1"))
        resp = self._get(self.laleli_a, theirs)
        self.assertEqual(resp.status_code, 400)

    def test_an_order_with_no_customer_is_not_printable(self):
        """(None, None, None) matches (None, None, None), so without
        this an unattached order would combine with any other."""
        nobody = Order.objects.create(order_number="DK-NOCARI")
        resp = self._get(nobody)
        self.assertEqual(resp.status_code, 400)

    def test_no_orders_picked(self):
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.assertEqual(self.client.get(self.url, {"ids": "x"}).status_code, 400)

    def test_a_missing_order_is_not_silently_dropped(self):
        """Printing two of the three asked for would be a wrong total on
        a document the customer is handed."""
        resp = self.client.get(self.url, {"ids": f"{self.laleli_a.pk},9999999"})
        self.assertEqual(resp.status_code, 404)

    def test_a_signed_out_visitor_gets_nothing(self):
        """The sheet carries a customer's prices. Every order with a
        cari is already refused — member_can_use_book says no to a
        viewer with no member — and this covers the one without."""
        self.client.logout()
        resp = self._get(self.laleli_a)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/authentication/signin", resp["Location"])

    def test_a_book_the_viewer_is_not_assigned_is_refused(self):
        """The rule book_guarded applies to an order page, asked here
        per order — a sheet may legitimately span books, but only the
        viewer's own."""
        laleli_only = User.objects.create_user("laleli_only", password="pw")
        laleli_only.member.books.add(self.laleli)
        laleli_only.member.default_book = self.laleli
        laleli_only.member.save()
        self.client.force_login(laleli_only)

        self.assertEqual(self._get(self.laleli_a, self.laleli_b).status_code, 200)
        self.assertEqual(self._get(self.laleli_a, self.ergene_a).status_code, 404)


class CombinedOrderExcel(OlegOrders, TestCase):
    """The same sheet as a spreadsheet."""

    url_name = "operating:order_excel_combined"

    def _book(self, *orders):
        import openpyxl
        from io import BytesIO
        resp = self._get(*orders)
        self.assertEqual(resp.status_code, 200)
        return openpyxl.load_workbook(BytesIO(resp.content)).active

    def test_it_comes_to_what_the_printed_sheet_comes_to(self):
        ws = self._book(self.laleli_a, self.laleli_b, self.ergene_a)
        self.assertEqual(ws.cell(ws.max_row, 11).value, 654.15)

    def test_money_is_a_number_a_spreadsheet_can_add(self):
        """The point of exporting is to do arithmetic on it, so the
        figures are numbers with a display format — not text that only
        looks like money."""
        ws = self._book(self.laleli_a)
        # int or float — openpyxl reads a whole number back as an int.
        # What matters is that it is not a string that looks like money.
        self.assertIsInstance(ws.cell(ws.max_row, 11).value, (int, float))
        self.assertIn("#,##0.00", ws.cell(ws.max_row, 11).number_format)

    def test_every_line_names_the_order_it_came_from(self):
        """A column, where the printed sheet uses a heading row: a
        spreadsheet sorts and pivots on a column and cannot on a
        heading."""
        ws = self._book(self.laleli_a, self.ergene_a)
        col = [ws.cell(r, 1).value for r in range(1, ws.max_row + 1)]
        self.assertIn("DK-284", col)
        self.assertIn("DK-291", col)

    def test_it_is_delivered_as_a_spreadsheet(self):
        resp = self._get(self.laleli_a)
        self.assertIn("spreadsheetml.sheet", resp["Content-Type"])
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertIn("OLEG MOTUZENKO", resp["Content-Disposition"])

    def test_it_refuses_what_the_printed_sheet_refuses(self):
        """Both go through select_combined_orders — a rule enforced in
        only one of two formats is not a rule."""
        theirs = self._order(self.laleli, self.someone_else, "DK-999",
                             Decimal("10"), Decimal("1"))
        self.assertEqual(self._get(self.laleli_a, theirs).status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.assertEqual(
            self.client.get(self.url,
                            {"ids": f"{self.laleli_a.pk},9999999"}).status_code, 404)

    def test_a_signed_out_visitor_gets_nothing(self):
        self.client.logout()
        self.assertEqual(self._get(self.laleli_a).status_code, 302)

    def test_it_carries_the_variant_name_and_both_codes(self):
        ws = self._book(self.laleli_a)
        heads = [ws.cell(r, c).value
                 for r in range(1, ws.max_row + 1) for c in (3, 4, 5, 6, 7)]
        for h in ("Product", "SKU", "Variant", "Variant SKU", "Type"):
            self.assertIn(h, heads)


class SingleOrderPrintUnchanged(TestCase):
    """The one-order sheet builds its rows through the same helper now.
    It must still print exactly what it printed before — one order needs
    no per-order heading above its lines."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        cari = CariAccount.objects.create(
            book=book, code="C-1", name="Oleg", type="customer",
            default_currency=usd)
        self.order = Order.objects.create(order_number="DK-284", cari=cari,
                                          contact=Contact.objects.create(name="OLEG"))
        OrderItem.objects.create(
            order=self.order,
            product=Product.objects.create(title="Crepe", sku="KZL000315", price=10),
            quantity=Decimal("156.00"), price=Decimal("2.50"))
        self.client.force_login(User.objects.create_superuser("boss", "b@t.com", "pw"))

    def test_it_still_prints_its_total(self):
        resp = self.client.get(
            reverse("operating:order_print", kwargs={"pk": self.order.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["order_total"], Decimal("390.00"))
        self.assertContains(resp, "$390.00")

    def test_it_carries_no_group_heading(self):
        resp = self.client.get(
            reverse("operating:order_print", kwargs={"pk": self.order.pk}))
        self.assertEqual(len(resp.context["order_groups"]), 1)
        self.assertNotContains(resp, 'class="grp"')
