# to run this test, use the command:
# python manage.py test accounting.test_purchase_edit_billed_quantity

"""A purchase line bills what the supplier invoiced, not what its rolls
measure today.

Invoice 117: 152 m and 155 m arrived and were billed; 2 m was cut off one
roll on each line for samples, entered on the warehouse page as a shorter
roll. The next save of the purchase rebuilt both lines from the rolls, and
the supplier's balance lost $21.20 nobody had agreed to. A line now moves
only by the roll changes made on the purchase form itself."""
from decimal import Decimal

from django.urls import reverse

from accounting.tests import test_received_purchase_edit as base
from operating.models import WarehouseProductItem


class PurchaseEditBilledQuantityTest(base.TestCase):
    setUp = base.ReceivedPurchaseEditTest.setUp
    _invoice = base.ReceivedPurchaseEditTest._invoice
    _roll = base.ReceivedPurchaseEditTest._roll
    _edit_url = base.ReceivedPurchaseEditTest._edit_url
    _form = base.ReceivedPurchaseEditTest._form
    _variant = base.ReceivedPurchaseEditTest._variant
    _save = base.ReceivedPurchaseEditTest._save

    def _cut_on_warehouse_page(self, barcode, metres):
        roll = self._roll(barcode)
        r = self.client.post(
            reverse("operating:warehouse_roll_edit",
                    args=[self.wh.pk, roll.product_id, roll.pk]),
            data={"barcode": roll.barcode, "quantity": str(metres)})
        self.assertTrue(r.json()["success"], r.json())

    def _line(self):
        return self._invoice().items.get()

    def test_a_roll_shortened_on_the_warehouse_page_leaves_the_line_alone(self):
        self._cut_on_warehouse_page("KRV-A", 28)

        r = self._save(self._form())
        self.assertEqual(r.status_code, 200, r.content)

        self.assertEqual(self._roll("KRV-A").quantity, Decimal("28.00"))
        self.assertEqual(self._line().quantity, Decimal("50.000"))
        inv = self._invoice()
        self.assertEqual(inv.total, Decimal("175.00"))
        self.assertEqual(inv.posted_movement.amount, Decimal("-175.00"))

    def test_a_re_measure_on_the_form_moves_the_line_by_that_much(self):
        self._cut_on_warehouse_page("KRV-A", 28)

        form = self._form()
        self._variant(form)["tops"][1]["qty"] = "19"          # KRV-B, 20 → 19
        self.assertEqual(self._save(form).status_code, 200)

        self.assertEqual(self._line().quantity, Decimal("49.000"))

    def test_adding_and_removing_rolls_still_count(self):
        self._cut_on_warehouse_page("KRV-A", 28)

        form = self._form()
        self._variant(form)["tops"].append({"qty": 12, "barcode": ""})
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._line().quantity, Decimal("62.000"))

        form = self._form()
        tops = self._variant(form)["tops"]
        tops[:] = [t for t in tops if t["barcode"] != "KRV-B"]
        self.assertEqual(self._save(form).status_code, 200)
        self.assertEqual(self._line().quantity, Decimal("42.000"))
        self.assertFalse(WarehouseProductItem.objects.filter(barcode="KRV-B").exists())
