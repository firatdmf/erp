"""The carrier's receipt is attached to the order as it ships.

A photo or PDF picked in the cargo box rides in with Complete order (or
Save) and is kept on the order; anything that isn't an image or a PDF is
turned away without costing the completion. A refused completion stores
nothing, and a receipt can be taken off again — but not by a sales rep,
who can't move the order on either.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from authentication.models import Permission
from marketing.models import Product
from operating.models import Order, OrderCargoReceipt, OrderItem

CDN = "https://cdn.test/receipt"


def _pdf(name="kargo-fisi.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 receipt", content_type="application/pdf")


def _jpg(name="IMG_0412.jpg"):
    return SimpleUploadedFile(name, b"\xff\xd8\xff receipt", content_type="image/jpeg")


class _AnOrderToComplete:
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-318", name="Euroland", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(
            order_number="DK0000318", current_account=account, order_status="pending")
        product = Product.objects.create(title="Crepe", sku="KZL000318",
                                         price=10, cost=Decimal("1"))
        OrderItem.objects.create(order=self.order, product=product,
                                 quantity=Decimal("10"), price=Decimal("2.50"))
        self.user = User.objects.create_user("cargo_rcpt", password="pw")
        self.user.member.books.add(book)
        self.user.member.default_book = book
        self.user.member.save()
        self.client.force_login(self.user)
        self.url = reverse("operating:order_detail", kwargs={"pk": self.order.pk})

    def _complete(self, *files, status="shipped"):
        return self.client.post(self.url, {
            "action": "update_status", "order_status": status,
            "carrier": "yurtici", "tracking_number": "123",
            "cargo_receipts": list(files),
        })


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class CargoReceiptOnCompletion(_AnOrderToComplete, TestCase):

    def test_completing_keeps_the_receipts(self, upload):
        self._complete(_pdf(), _jpg())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
        receipts = list(self.order.cargo_receipts.all())
        self.assertEqual([r.file_name for r in receipts], ["kargo-fisi.pdf", "IMG_0412.jpg"])
        self.assertEqual([r.content_type for r in receipts], ["application/pdf", "image/jpeg"])
        self.assertTrue(receipts[0].is_pdf)
        self.assertEqual(receipts[0].created_by, self.user)
        self.assertTrue(upload.call_args_list[0].args[1].startswith(
            f"operating/orders/{self.order.pk}/cargo/"))
        self.assertContains(self.client.get(self.url), "kargo-fisi.pdf")

    def test_a_file_that_is_not_an_image_or_pdf_is_turned_away(self, upload):
        doc = SimpleUploadedFile("notes.docx", b"PK", content_type="application/msword")
        resp = self._complete(doc, _pdf())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
        self.assertEqual(self.order.cargo_receipts.count(), 1)
        self.assertEqual(upload.call_count, 1)
        self.assertIn("notes.docx", " ".join(m.message for m in resp.wsgi_request._messages))

    def test_a_cdn_failure_still_completes_the_order(self, upload):
        upload.side_effect = Exception("Bunny down")
        self._complete(_pdf())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
        self.assertFalse(self.order.cargo_receipts.exists())

    def test_a_refused_completion_stores_nothing(self, upload):
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)
        self._complete(_pdf())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "pending")
        self.assertFalse(self.order.cargo_receipts.exists())
        upload.assert_not_called()

    def test_save_alone_attaches_a_receipt(self, upload):
        self._complete(_jpg(), status="pending")
        self.assertEqual(self.order.cargo_receipts.count(), 1)

    @patch("marketing.utils.bunny_storage.delete_from_bunny")
    def test_a_receipt_can_be_removed(self, delete, upload):
        self._complete(_pdf())
        receipt = self.order.cargo_receipts.get()
        self.client.post(self.url, {"action": "delete_cargo_receipt", "receipt_id": receipt.pk})
        self.assertFalse(OrderCargoReceipt.objects.filter(pk=receipt.pk).exists())
        delete.assert_called_once_with(CDN)

    def test_a_sales_rep_cannot_remove_one(self, upload):
        self._complete(_pdf())
        receipt = self.order.cargo_receipts.get()
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)
        self.client.post(self.url, {"action": "delete_cargo_receipt", "receipt_id": receipt.pk})
        self.assertTrue(OrderCargoReceipt.objects.filter(pk=receipt.pk).exists())

    def test_a_phone_can_open_the_camera(self, upload):
        # The file picker also takes PDFs, which on Android means no camera;
        # the second input asks for the rear camera outright.
        html = self.client.get(self.url).content.decode()
        self.assertIn('id="od-rcpt-cam" accept="image/*" capture="environment"', html)

    def test_camera_shots_and_picked_files_post_together(self, upload):
        # Each camera shot is its own input under the same name.
        self._complete(_jpg("image.jpg"), _jpg("image.jpg"), _pdf())
        self.assertEqual(self.order.cargo_receipts.count(), 3)
        self.assertEqual(len({c.args[1] for c in upload.call_args_list}), 3)

    def test_a_real_photo_is_stored_as_a_jpeg(self, upload):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (4000, 3000), "white").save(buf, format="PNG")
        self._complete(SimpleUploadedFile("slip.png", buf.getvalue(), content_type="image/png"))
        receipt = self.order.cargo_receipts.get()
        self.assertEqual((receipt.file_name, receipt.content_type), ("slip.jpg", "image/jpeg"))
        sent, path = upload.call_args.args[:2]
        self.assertTrue(path.endswith(".jpg"))
        sent.seek(0)
        self.assertEqual(Image.open(sent).size, (2400, 1800))

    @patch("marketing.utils.bunny_storage.delete_from_bunny")
    @patch("operating.views_warehouse.apply_order_status_change", return_value=(False, "error:boom"))
    def test_any_refused_completion_takes_the_receipts_back(self, _funnel, delete, upload):
        # Receipts are stored ahead of the status change (so its email can
        # carry them); a refusal for any reason removes them again.
        self._complete(_pdf())
        self.assertFalse(self.order.cargo_receipts.exists())
        delete.assert_called_once_with(CDN)


class _FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class TheShippedEmailCarriesTheReceipt(_AnOrderToComplete, TestCase):
    """Completing an order emails the customer from inside the status
    change; the receipt picked with Complete order goes out with it."""

    def setUp(self):
        super().setUp()
        Order.objects.filter(pk=self.order.pk).update(
            notify_customer=True, is_guest_order=True, guest_email="tanya@euroland.test")

    @patch("operating.order_notifications._render_order_pdf", return_value=("order.pdf", b"%PDF order"))
    @patch("operating.order_notifications._send_via_gmail_oauth", return_value=True)
    @patch("requests.get", return_value=_FakeResponse(b"%PDF-1.4 receipt"))
    def test_completing_attaches_the_receipt(self, _get, send, _pdf_render, upload):
        self._complete(_pdf())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
        shipped = [c for c in send.call_args_list if "receipt" in (c.kwargs.get("text_body") or "")]
        self.assertEqual(len(shipped), 1)
        call = shipped[0]
        self.assertEqual(call.kwargs["extra_attachments"],
                         [("kargo-fisi.pdf", b"%PDF-1.4 receipt", "application/pdf")])
        self.assertIn("The carrier's receipt is attached to this email.", call.args[2])

    @patch("operating.order_notifications._render_order_pdf", return_value=("order.pdf", b"%PDF order"))
    @patch("operating.order_notifications._send_via_gmail_oauth", return_value=True)
    @patch("requests.get", side_effect=Exception("CDN down"))
    def test_a_receipt_the_cdn_cannot_serve_does_not_stop_the_email(self, _get, send, _pdf_render, upload):
        self._complete(_pdf())
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.kwargs["extra_attachments"], [])
        self.assertNotIn("attached to this email", send.call_args.args[2])
