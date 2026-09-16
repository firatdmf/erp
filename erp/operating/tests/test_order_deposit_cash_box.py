"""A deposit taken with an order says which kasa it went into.

The same rule as Take Payment: a cash collection names its cash box, or it
is not confirmed. Without one the deposit is kept as a draft to finish,
never booked into no kasa at all.

Run with:
    python manage.py test operating.tests.test_order_deposit_cash_box
"""
from decimal import Decimal
from unittest import mock

from django.urls import reverse

from accounting.models import CashAccount, CurrencyCategory, Payment
# The module, not the class: a TestCase imported by name is collected and
# run again under this file.
from operating.tests import test_cross_book_order_split as split

ERGENE_SKU, LALELI_SKU = split.ERGENE_SKU, split.LALELI_SKU


class OrderDepositCashBox(split.CrossBookOrderSplit):
    # Inherits the setup and helpers; the split tests themselves are
    # switched off at the bottom of this file.

    def setUp(self):
        super().setUp()
        usd = CurrencyCategory.objects.get(code="USD")
        self.laleli_box = CashAccount.objects.create(
            book=self.laleli, name="Laleli Kasa", currency=usd)
        self.ergene_box = CashAccount.objects.create(
            book=self.ergene, name="Ergene Kasa", currency=usd)

    def test_a_deposit_with_its_box_is_confirmed_into_that_box(self):
        self._post([self._line(LALELI_SKU, self.laleli, "L-0001")],
                   deposit_received="1", deposit_amount="30",
                   deposit_cash_account=self.laleli_box.pk)
        pay = Payment.objects.get()
        self.assertEqual(pay.status, "confirmed")
        self.assertEqual(pay.cash_account, self.laleli_box)

    def test_a_deposit_without_a_box_is_kept_as_a_draft(self):
        r = self.client.post(reverse("operating:create_order"), {
            "customer_type": "contact", "customer_pk": self.customer.pk,
            "book": self.laleli.pk,
            "product_json_input": __import__("json").dumps(
                [self._line(LALELI_SKU, self.laleli, "L-0001")]),
            "deposit_received": "1", "deposit_amount": "30",
        }, follow=True)
        pay = Payment.objects.get()
        self.assertEqual(pay.status, "draft")
        self.assertIsNone(pay.posted_movement)
        self.assertContains(r, "saved as a draft")

    def test_a_box_from_another_book_is_not_accepted(self):
        self._post([self._line(LALELI_SKU, self.laleli, "L-0001")],
                   deposit_received="1", deposit_amount="30",
                   deposit_cash_account=self.ergene_box.pk)
        pay = Payment.objects.get()
        self.assertEqual(pay.status, "draft")
        self.assertIsNone(pay.cash_account)

    def test_each_half_of_a_split_goes_into_its_own_books_box(self):
        self._post(
            [self._line(LALELI_SKU, self.laleli, "L-0001"),
             self._line(ERGENE_SKU, self.ergene, "E-0001")],
            deposit_received="1",
            **{f"deposit_amount_{self.laleli.pk}": "40",
               f"deposit_amount_{self.ergene.pk}": "25",
               f"deposit_cash_account_{self.laleli.pk}": self.laleli_box.pk,
               f"deposit_cash_account_{self.ergene.pk}": self.ergene_box.pk},
        )
        boxes = {p.book_id: (p.status, p.cash_account_id) for p in Payment.objects.all()}
        self.assertEqual(boxes[self.laleli.pk], ("confirmed", self.laleli_box.pk))
        self.assertEqual(boxes[self.ergene.pk], ("confirmed", self.ergene_box.pk))

    def test_the_form_lists_each_books_boxes(self):
        with mock.patch("marketing.utils.bunny_storage.upload_to_bunny"):
            r = self.client.get(reverse("operating:create_order"))
        self.assertContains(r, 'id="co-deposit-boxes"')
        boxes = r.context["deposit_cash_boxes"]
        self.assertEqual([b["id"] for b in boxes[str(self.laleli.pk)]], [self.laleli_box.pk])
        self.assertEqual([b["id"] for b in boxes[str(self.ergene.pk)]], [self.ergene_box.pk])
        self.assertContains(r, 'name="deposit_cash_account"')


# The parent's tests would otherwise run a second time under this name.
for _name in [n for n in vars(split.CrossBookOrderSplit) if n.startswith("test_")]:
    setattr(OrderDepositCashBox, _name, None)
