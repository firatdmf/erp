"""An order split across books has one status.

Two orders in the books, one on screen — and one status section: whichever
half a change is asked on, every half takes it, in one transaction, with the
same cargo info and the same receipts. Completing, re-opening or cancelling
posts to every half's book, so it takes someone who holds all of them.

Run with:
    python manage.py test operating.tests.test_split_order_status
"""
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderCargoReceipt, OrderItem

CDN = "https://cdn.test/receipt"


class _ASplitOrder:
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
    def setUp(self, _upload):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        customer = Contact.objects.create(name="Anna Lugansk")
        group = uuid.uuid4()
        self.laleli_half = self._half(self.laleli, "ORD-2026-000023", customer, group, usd, "Krep")
        self.ergene_half = self._half(self.ergene, "ORD-2026-000024", customer, group, usd, "Tul")
        self.user = User.objects.create_user("firat", password="pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _half(self, book, number, customer, group, currency, title):
        account = CurrentAccount.objects.create(
            book=book, code=f"C-{book.pk}", name=f"Anna ({book.name})", type="customer",
            contact=customer, default_currency=currency)
        order = Order.objects.create(order_number=number, current_account=account,
                                     contact=customer, currency=currency, split_group=group)
        OrderItem.objects.create(order=order, quantity=Decimal("10"), price=Decimal("2"),
                                 product=Product.objects.create(title=title, sku=title, price=1))
        return order

    def _url(self, order):
        return reverse("operating:order_detail", kwargs={"pk": order.pk})

    def _move(self, order, status, *files, **extra):
        return self.client.post(self._url(order), {
            "action": "update_status", "order_status": status,
            "carrier": "yurtici", "tracking_number": "TRK-1",
            "cargo_receipts": list(files), **extra})

    def _states(self):
        return [(o.order_status, o.carrier, o.tracking_number)
                for o in Order.objects.filter(pk__in=[self.laleli_half.pk, self.ergene_half.pk]).order_by("pk")]

    def _save_cargo(self, order):
        return self.client.post(self._url(order), {
            "action": "update_status", "order_status": order.order_status,
            "carrier": "yurtici", "tracking_number": "TRK-9"}, HTTP_ACCEPT="application/json")


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class SplitOrderStatus(_ASplitOrder, TestCase):

    def test_completing_one_half_completes_both_with_the_same_cargo(self, upload):
        self._move(self.ergene_half, "shipped")
        self.assertEqual(self._states(), [("shipped", "yurtici", "TRK-1")] * 2)

    def test_reopening_and_cancelling_move_both_too(self, upload):
        self._move(self.laleli_half, "shipped")
        self._move(self.ergene_half, "packaging")
        self.assertEqual([s[0] for s in self._states()], ["packaging", "packaging"])
        self._move(self.laleli_half, "cancelled", cancel_reason="customer gave up")
        self.assertEqual([s[0] for s in self._states()], ["cancelled", "cancelled"])

    def test_completing_takes_every_half_s_book(self, upload):
        self.user.member.books.remove(self.ergene)
        resp = self._move(self.laleli_half, "shipped")
        self.assertEqual(self._states(), [("pending", None, None)] * 2)
        self.assertIn("every book", " ".join(str(m.message) for m in resp.wsgi_request._messages))
        # ...and the page says so before anyone tries.
        page = self.client.get(self._url(self.laleli_half))
        self.assertContains(page, 'id="od-needs-all-books"')
        self.assertRegex(page.content.decode(), r'id="od-complete-btn"[^>]*disabled')

    def test_but_packing_does_not(self, upload):
        self.user.member.books.remove(self.ergene)
        self._move(self.laleli_half, "packaging")
        self.assertEqual([s[0] for s in self._states()], ["packaging", "packaging"])

    def test_saving_cargo_info_brings_a_half_that_stands_elsewhere_along(self, upload):
        Order.objects.filter(pk=self.laleli_half.pk).update(order_status="shipped")
        self.laleli_half.refresh_from_db()
        self.assertTrue(self._save_cargo(self.laleli_half).json()["ok"])
        self.assertEqual(self._states(), [("shipped", "yurtici", "TRK-9")] * 2)

    def test_which_completes_it_so_takes_every_book_as_completing_does(self, upload):
        Order.objects.filter(pk=self.laleli_half.pk).update(order_status="shipped")
        self.laleli_half.refresh_from_db()
        self.user.member.books.remove(self.ergene)
        resp = self._save_cargo(self.laleli_half)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(self._states(), [("shipped", None, None), ("pending", None, None)])

    def test_saving_on_a_cancelled_half_does_not_cancel_the_rest(self, upload):
        Order.objects.filter(pk=self.laleli_half.pk).update(order_status="cancelled")
        self.laleli_half.refresh_from_db()
        self._save_cargo(self.laleli_half)
        self.assertEqual([s[0] for s in self._states()], ["cancelled", "pending"])

    def test_a_cancelled_half_stays_cancelled_and_holds_nothing_back(self, upload):
        Order.objects.filter(pk=self.ergene_half.pk).update(order_status="cancelled")
        self._move(self.laleli_half, "shipped")
        self.assertEqual([s[0] for s in self._states()], ["shipped", "cancelled"])

    def test_a_refused_half_takes_the_other_back_with_it(self, upload):
        from operating import views_warehouse
        real = views_warehouse._apply_status_to_one

        def second_half_fails(order, *args, **kwargs):
            if order.pk == self.ergene_half.pk:
                return False, "error:boom"
            return real(order, *args, **kwargs)

        with patch.object(views_warehouse, "_apply_status_to_one", side_effect=second_half_fails):
            self._move(self.laleli_half, "shipped")
        self.assertEqual(self._states(), [("pending", None, None)] * 2)

    def test_a_receipt_attached_on_one_half_shows_on_both_and_comes_off_from_either(self, upload):
        pdf = SimpleUploadedFile("kargo-fisi.pdf", b"%PDF-1.4", content_type="application/pdf")
        self._move(self.laleli_half, "shipped", pdf)
        receipt = OrderCargoReceipt.objects.get()
        self.assertEqual(receipt.order_id, self.laleli_half.pk)
        self.assertContains(self.client.get(self._url(self.ergene_half)), "kargo-fisi.pdf")
        with patch("marketing.utils.bunny_storage.delete_from_bunny"):
            self.client.post(self._url(self.ergene_half),
                             {"action": "delete_cargo_receipt", "receipt_id": receipt.pk})
        self.assertFalse(OrderCargoReceipt.objects.exists())

    def test_cargo_saved_on_one_half_before_reads_the_same_on_the_other(self, upload):
        Order.objects.filter(pk=self.laleli_half.pk).update(
            order_status="shipped", carrier="yurtici", tracking_number="OLD-1")
        Order.objects.filter(pk=self.ergene_half.pk).update(order_status="shipped")
        self.assertContains(self.client.get(self._url(self.ergene_half)), "OLD-1")


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class SplitOrderTellsTheCustomerOnce(_ASplitOrder, TestCase):
    """One notice for the whole order — both halves' lines under both
    numbers — not one per half."""

    def setUp(self):
        super().setUp()
        Order.objects.update(notify_customer=True, is_guest_order=True,
                             guest_email="anna@lugansk.test")

    @patch("operating.order_notifications._render_order_pdf", return_value=("order.pdf", b"%PDF order"))
    @patch("operating.order_notifications._send_via_gmail_oauth", return_value=True)
    def test_completing_sends_one_email_for_both_halves(self, send, _pdf, upload):
        with self.captureOnCommitCallbacks(execute=True):
            self._move(self.ergene_half, "shipped")
        self.assertEqual(self._states(), [("shipped", "yurtici", "TRK-1")] * 2)
        self.assertEqual(send.call_count, 1)
        _to, subject, html = send.call_args.args[:3]
        self.assertIn("ORD-2026-000023 & ORD-2026-000024", subject)
        self.assertIn("Krep", html)
        self.assertIn("Tul", html)
        self.assertIn("40.00", html)  # 20.00 + 20.00

    @patch("operating.order_notifications._render_order_pdf", return_value=("order.pdf", b"%PDF order"))
    @patch("operating.order_notifications._send_via_gmail_oauth", return_value=True)
    def test_a_refused_change_tells_nobody(self, send, _pdf, upload):
        self.user.member.books.remove(self.ergene)
        with self.captureOnCommitCallbacks(execute=True):
            self._move(self.laleli_half, "shipped")
        send.assert_not_called()
