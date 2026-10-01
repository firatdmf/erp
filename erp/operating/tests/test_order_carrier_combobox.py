"""The carrier field on the order page is a combobox over the fixed list.

The <select> stays underneath as what the form posts, so a pick is saved
exactly as before; the page opens on a chip when the order already has a
carrier, and on the search box when it doesn't.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from operating.models import Carrier, Order


class CarrierCombobox(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-419", name="Euroland", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(
            order_number="DK0000419", current_account=account, order_status="pending")
        user = User.objects.create_user("carrier_cbx", password="pw")
        user.member.books.add(book)
        user.member.default_book = book
        user.member.save()
        self.client.force_login(user)
        self.url = reverse("operating:order_detail", kwargs={"pk": self.order.pk})

    def _html(self):
        return self.client.get(self.url).content.decode()

    def test_no_carrier_opens_on_the_search_box(self):
        html = self._html()
        self.assertIn('<select name="carrier" id="od-carrier-select" hidden>', html)
        self.assertIn('<div class="od-cbx-box" >', html)
        self.assertIn('<div class="od-cbx-chip" hidden>', html)

    def test_a_chosen_carrier_opens_on_its_chip(self):
        Order.objects.filter(pk=self.order.pk).update(carrier="yurtici")
        html = self._html()
        self.assertIn('<div class="od-cbx-box" hidden>', html)
        self.assertIn("<span>Yurtiçi Kargo</span>", html)
        self.assertIn('<option value="yurtici" selected>', html)

    def test_the_pick_still_posts_as_carrier(self):
        self.client.post(self.url, {"action": "update_status", "order_status": "pending",
                                    "carrier": "aras", "tracking_number": ""})
        self.order.refresh_from_db()
        self.assertEqual(self.order.carrier, "aras")


class TypedCarriersJoinTheList(CarrierCombobox):
    """A carrier missing from the list is typed in by name and added on
    save; "Other" is no longer offered but still reads on old orders."""

    def _save(self, carrier):
        self.client.post(self.url, {"action": "update_status", "order_status": "pending",
                                    "carrier": carrier, "tracking_number": ""})
        self.order.refresh_from_db()
        return self.order.carrier

    def test_the_seeded_list_leaves_other_out(self):
        self.assertEqual([c for c, _ in Carrier.choices()],
                         ["yurtici", "mng", "aras", "ptt", "ups"])
        self.assertNotIn('value="other"', self._html())

    def test_a_typed_name_is_added_and_offered_next_time(self):
        code = self._save("Sürat Kargo")
        self.assertEqual(code, "surat-kargo")
        self.assertEqual(self.order.get_carrier_display(), "Sürat Kargo")
        self.assertIn(("surat-kargo", "Sürat Kargo"), Carrier.choices())
        self.assertEqual(Carrier.objects.get(code=code).created_by.username, "carrier_cbx")
        self.assertIn("<span>Sürat Kargo</span>", self._html())

    def test_the_same_name_typed_differently_is_the_same_carrier(self):
        self._save("Sürat Kargo")
        self.assertEqual(self._save("  SURAT   kargo "), "surat-kargo")
        self.assertEqual(self._save("yurtiçi kargo"), "yurtici")
        self.assertEqual(Carrier.objects.count(), 7)

    def test_an_old_order_under_other_keeps_it(self):
        Order.objects.filter(pk=self.order.pk).update(carrier="other")
        html = self._html()
        self.assertIn("<span>Diğer</span>", html)
        self.assertIn('<option value="other" selected>', html)
        self.assertEqual(self._save("other"), "other")


class CompletedOrderCargoReadsAsSent(CarrierCombobox):
    """Once the order is completed its cargo info shows read-only, with an
    "Edit cargo info" button that brings the fields back."""

    def test_an_open_order_shows_the_fields(self):
        html = self._html()
        self.assertIn('<div id="od-ship-edit" >', html)
        self.assertNotIn('id="od-ship-view"', html)
        self.assertNotIn('id="od-ship-unlock"', html)

    def test_a_completed_order_shows_its_cargo_read_only(self):
        Order.objects.filter(pk=self.order.pk).update(
            order_status="shipped", carrier="yurtici", tracking_number="16865")
        html = self._html()
        self.assertIn('id="od-ship-view"', html)
        self.assertIn('<i class="fa fa-truck"></i>Yurtiçi Kargo</span>', html)
        self.assertIn('<i class="fa fa-barcode"></i>16865</span>', html)
        self.assertIn('<div id="od-ship-edit" hidden>', html)
        self.assertIn('id="od-ship-unlock"', html)
        self.assertIn('id="od-ship-cancel"', html)

    def test_a_completed_order_without_cargo_says_so(self):
        Order.objects.filter(pk=self.order.pk).update(order_status="shipped")
        self.assertIn('class="od-ship-sum-none"', self._html())

    def test_a_completed_order_can_still_save_cargo_info(self):
        Order.objects.filter(pk=self.order.pk).update(order_status="shipped")
        self.client.post(self.url, {"action": "update_status", "order_status": "shipped",
                                    "carrier": "aras", "tracking_number": "999"})
        self.order.refresh_from_db()
        self.assertEqual((self.order.order_status, self.order.carrier, self.order.tracking_number),
                         ("shipped", "aras", "999"))
