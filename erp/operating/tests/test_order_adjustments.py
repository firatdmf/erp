# to run this test, use the command:
# python manage.py test operating.tests.test_order_adjustments

"""Lines on an order that are not products.

Delivery, packing, a partnership discount: a label and an amount, agreed
as part of the deal. They were nowhere in the ERP, so an order that had
been quoted at €14,850 on a proforma — €15,090 of goods less a €240
partnership discount — could only be stored as €15,090, and the customer's
account was owed €240 more than anybody had agreed to.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.invoice_doc import build_order_doc
from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import post_order_movement
from crm.models import Company, Contact
from marketing.models import Product
from operating.models import Order, OrderAdjustment, OrderItem


class OrderAdjustmentTest(TestCase):
    def setUp(self):
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.company = Company.objects.create(name="Euroland")
        self.account = CurrentAccount.objects.create(
            book=self.book, code="C-EUR", name="Euroland", type="customer",
            company=self.company, default_currency=self.eur,
        )
        self.product = Product.objects.create(title="Fitted Sheet", sku="FS", featured=False)
        self.member = getattr(
            get_user_model().objects.create_superuser("firat_adj", "a@b.c", "pw"), "member", None)
        self.order = Order.objects.create(company=self.company, current_account=self.account,
                                          currency=self.eur)
        OrderItem.objects.create(order=self.order, product=self.product,
                                 quantity=Decimal("100"), price=Decimal("2.00"))

    def _add(self, label, amount, position=0):
        return OrderAdjustment.objects.create(order=self.order, label=label,
                                              amount=Decimal(amount), position=position)

    # ── What the order comes to ─────────────────────────────────────
    def test_an_order_with_none_is_its_lines(self):
        self.assertEqual(self.order.lines_total(), Decimal("200.00"))
        self.assertEqual(self.order.total_value(), Decimal("200.00"))
        self.assertEqual(self.order.adjustments_total(), Decimal("0.00"))

    def test_a_charge_adds_and_a_discount_takes_off(self):
        self._add("Delivery", "45.00", 0)
        self._add("Partnership discount", "-20.00", 1)
        self.assertEqual(self.order.lines_total(), Decimal("200.00"))
        self.assertEqual(self.order.adjustments_total(), Decimal("25.00"))
        self.assertEqual(self.order.total_value(), Decimal("225.00"))

    def test_the_subtotal_stays_the_goods(self):
        """The lines keep the prices that were quoted — the discount is
        its own row, not spread over them."""
        self._add("Partnership discount", "-40.00")
        self.assertEqual(self.order.lines_total(), Decimal("200.00"))
        self.assertEqual(self.order.items.get().price, Decimal("2.00"))
        self.assertEqual(self.order.total_value(), Decimal("160.00"))

    def test_a_discount_bigger_than_the_order_bills_nothing(self):
        """Not a negative receivable — that would credit the customer for
        shopping here."""
        self._add("Goodwill", "-500.00")
        self.assertEqual(self.order.total_value(), Decimal("0.00"))
        self.assertEqual(self.order.billable_value(), Decimal("0.00"))

    def test_they_print_in_the_order_they_were_agreed(self):
        self._add("Packing", "10.00", 1)
        self._add("Delivery", "45.00", 0)
        self.assertEqual([a.label for a in self.order.adjustments.all()],
                         ["Delivery", "Packing"])

    # ── What the customer's account is owed ─────────────────────────
    def test_the_ledger_follows_the_adjusted_total(self):
        self._add("Delivery", "45.00")
        self._add("Partnership discount", "-20.00")
        post_order_movement(self.order, member=self.member)
        mv = CurrentAccountMovement.objects.get(movement_type="order_sale")
        self.assertEqual(mv.amount, Decimal("225.00"))
        self.assertEqual(self.order.billable_value(), Decimal("225.00"))

    def test_editing_one_moves_the_ledger_with_it(self):
        adj = self._add("Delivery", "45.00")
        post_order_movement(self.order, member=self.member)
        adj.amount = Decimal("60.00")
        adj.save()
        post_order_movement(self.order, member=self.member)
        self.assertEqual(CurrentAccountMovement.objects.filter(
            movement_type="order_sale").count(), 1)
        self.assertEqual(CurrentAccountMovement.objects.get(
            movement_type="order_sale").amount, Decimal("260.00"))

    def test_the_profit_gives_away_a_discount(self):
        self._add("Partnership discount", "-20.00")
        # No cost is recorded on the product, so the goods' own profit is
        # their full price; the discount comes straight off it.
        self.assertEqual(self.order.gross_profit(), Decimal("180.00"))

    # ── What the customer is sent ───────────────────────────────────
    def test_the_invoice_shows_each_line_and_the_net_total(self):
        self._add("Delivery", "45.00", 0)
        self._add("Partnership discount", "-20.00", 1)
        doc = build_order_doc(self.order)
        self.assertEqual(doc.subtotal, Decimal("200.00"))
        self.assertEqual([(a.label, a.amount) for a in doc.adjustments],
                         [("Delivery", Decimal("45.00")),
                          ("Partnership discount", Decimal("-20.00"))])
        self.assertEqual(doc.total, Decimal("225.00"))

    def test_a_discount_prints_with_its_sign_outside_the_symbol(self):
        """“−€20.00”, not “€-20.00” — see Adjustment.magnitude."""
        [adj] = build_order_doc(self._discounted()).adjustments
        self.assertTrue(adj.is_credit)
        self.assertEqual(adj.magnitude, Decimal("20.00"))

    def _discounted(self):
        self._add("Partnership discount", "-20.00")
        return self.order

    def test_an_invoice_with_none_says_nothing_about_them(self):
        doc = build_order_doc(self.order)
        self.assertEqual(doc.adjustments, [])
        self.assertEqual(doc.total, doc.subtotal)

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_the_order_page_lists_them(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self._add("Delivery", "45.00")
        user = get_user_model().objects.create_superuser("firat_adj2", "c@d.e", "pw")
        self.client.force_login(user)
        r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Delivery")
        self.assertContains(r, "245.00")      # grand total
        self.assertContains(r, "200.00")      # subtotal, the goods alone

    # ── Every other document the customer is handed ─────────────────
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def test_the_printed_order_shows_them(self, mock_upload):
        """The sheet and the invoice are raised from the same order, so
        they must not quote two different figures."""
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self._add("Delivery", "45.00")
        user = get_user_model().objects.create_superuser("firat_adj3", "e@f.g", "pw")
        self.client.force_login(user)
        r = self.client.get(reverse("operating:order_print", args=[self.order.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Delivery")
        self.assertContains(r, "245.00")
        self.assertEqual(r.context["order_total"], Decimal("245.00"))

    def test_the_confirmation_mail_totals_them_too(self):
        from operating.order_notifications import _order_lines_and_total
        self._add("Delivery", "45.00")
        self._add("Partnership discount", "-20.00")
        items, adjustments, subtotal, total = _order_lines_and_total(self.order)
        self.assertEqual(len(items), 1)
        self.assertEqual([a.label for a in adjustments],
                         ["Delivery", "Partnership discount"])
        self.assertEqual(subtotal, Decimal("200.00"))
        self.assertEqual(total, Decimal("225.00"))

    # ── What the snapshot keeps ─────────────────────────────────────
    def test_the_first_copy_freezes_them_too(self):
        self._add("Delivery", "45.00")
        snap = self.order.build_snapshot()
        self.assertEqual(snap["adjustments"], [{"label": "Delivery", "amount": 45.0}])
        self.assertEqual(snap["total_value"], 245.0)


class AdjustmentsThroughTheFormTest(TestCase):
    """The create/edit form carries them as adjustments_json — the one
    path a real order takes."""

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Oleg Motuzenko")
        Product.objects.create(title="Krep", sku="KRP", featured=False)
        user = get_user_model().objects.create_superuser("seller_adj", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _post(self, adjustments, url=None, extra=None, item_id=None):
        line = {
            "item_no": 1, "product": {"sku": "KRP", "variant": False},
            "description": "", "quantity": 100, "outsourced": 0,
            "price": 2, "is_custom_curtain": False, "rolls": [],
        }
        # An edit names the line it is editing; without the id the form
        # would be asking for a second one.
        if item_id:
            line["item_id"] = item_id
        data = {
            "customer_type": "contact", "customer_pk": self.customer.pk,
            "book": self.book.pk,
            "product_json_input": json.dumps([line]),
        }
        if adjustments is not None:
            data["adjustments_json"] = json.dumps(adjustments)
        data.update(extra or {})
        return self.client.post(url or reverse("operating:create_order"), data)

    def test_the_form_saves_them_with_the_order(self):
        self._post([{"label": "Delivery", "amount": "45.00"},
                    {"label": "Partnership discount", "amount": "-20.00"}])
        order = Order.objects.get()
        self.assertEqual([(a.label, a.amount) for a in order.adjustments.all()],
                         [("Delivery", Decimal("45.00")),
                          ("Partnership discount", Decimal("-20.00"))])
        self.assertEqual(order.total_value(), Decimal("225.00"))

    def test_the_ledger_is_posted_net_at_create(self):
        self._post([{"label": "Partnership discount", "amount": "-20.00"}])
        order = Order.objects.get()
        mv = CurrentAccountMovement.objects.get(movement_type="order_sale")
        self.assertEqual(mv.amount, Decimal("180.00"))
        # And the frozen first copy agrees with it.
        self.assertEqual(order.original_snapshot["total_value"], 180.0)

    def test_a_row_with_no_label_or_no_amount_is_dropped(self):
        """The form leaves an empty pair behind whenever somebody clicks
        Add and thinks better of it."""
        self._post([{"label": "", "amount": "10"},
                    {"label": "Packing", "amount": ""},
                    {"label": "Delivery", "amount": "0"},
                    {"label": "Freight", "amount": "12.50"}])
        self.assertEqual([(a.label, a.amount) for a in Order.objects.get().adjustments.all()],
                         [("Freight", Decimal("12.50"))])

    def test_editing_replaces_them(self):
        self._post([{"label": "Delivery", "amount": "45.00"}])
        order = Order.objects.get()
        self._post([{"label": "Delivery", "amount": "60.00"}],
                   url=reverse("operating:edit_order", args=[order.pk]),
                   item_id=order.items.get().pk)
        self.assertEqual([(a.label, a.amount) for a in order.adjustments.all()],
                         [("Delivery", Decimal("60.00"))])
        self.assertEqual(CurrentAccountMovement.objects.get(
            movement_type="order_sale").amount, Decimal("260.00"))

    def test_clearing_them_on_edit_clears_the_ledger_too(self):
        self._post([{"label": "Delivery", "amount": "45.00"}])
        order = Order.objects.get()
        self._post([], url=reverse("operating:edit_order", args=[order.pk]),
                   item_id=order.items.get().pk)
        self.assertFalse(order.adjustments.exists())
        self.assertEqual(CurrentAccountMovement.objects.get(
            movement_type="order_sale").amount, Decimal("200.00"))

    def test_a_form_that_carries_no_field_leaves_them_alone(self):
        """An older page, or another endpoint posting the same view:
        silence is not an instruction to delete what is there."""
        self._post([{"label": "Delivery", "amount": "45.00"}])
        order = Order.objects.get()
        self._post(None, url=reverse("operating:edit_order", args=[order.pk]),
                   item_id=order.items.get().pk)
        self.assertEqual([a.label for a in order.adjustments.all()], ["Delivery"])

    def test_the_form_reopens_with_the_rows_it_saved(self):
        self._post([{"label": "Delivery", "amount": "45.00"}])
        order = Order.objects.get()
        r = self.client.get(reverse("operating:edit_order", args=[order.pk]),
                            headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('label: "Delivery"', body)
        self.assertIn('amount: "45.00"', body)      # unlocalised, so JS can read it
