from django.test import TestCase, Client
from django.urls import reverse
from operating.models import Order, Pack, PackedOrderItem, OrderItem, Product
from unittest.mock import patch

class PackTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Pages are behind the sign-in (erp.middleware.LoginWallMiddleware).
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user("packer", password="pw"))
        # Create a test product
        self.product = Product.objects.create(
            title="Test Product",
            sku="TP-100",
            price=10.00
        )
        # Create a test order
        self.order = Order.objects.create(
            order_number="DK0000008",
            status="pending"
        )
        # Create a test order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=10.00
        )

    @patch('marketing.utils.bunny_storage.upload_to_bunny')
    def test_pack_creation_and_code_generation(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        
        # Create a Pack
        pack = Pack.objects.create(
            order=self.order,
            pack_number=1
        )
        
        # Verify code is automatically generated
        self.assertEqual(pack.code, "PK-DK0000008-1")
        # Verify upload was called
        self.assertTrue(mock_upload.called)

    @patch('marketing.utils.bunny_storage.upload_to_bunny')
    def test_pdf_list_view(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        pack = Pack.objects.create(
            order=self.order,
            pack_number=1
        )
        
        # Pack the item
        PackedOrderItem.objects.create(
            pack=pack,
            order_item=self.order_item
        )
        
        url = reverse('operating:order_packing_list_pdf', kwargs={'pk': self.order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        # inline, not attachment — order_packing_list_pdf serves this one
        # for reading in a browser tab, and has since the Excel export took
        # over downloading-and-editing. The assertion was left behind.
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))

    @patch('marketing.utils.bunny_storage.upload_to_bunny')
    def test_pack_label_pdf_view(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        pack = Pack.objects.create(
            order=self.order,
            pack_number=1
        )
        
        PackedOrderItem.objects.create(
            pack=pack,
            order_item=self.order_item
        )
        
        url = reverse('operating:pack_pdf', kwargs={'pack_pk': pack.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))


    @patch('marketing.utils.bunny_storage.upload_to_bunny')
    def test_delete_renumbers_remaining_packs(self, mock_upload):
        """Deleting a package closes the gap — the rest run 1..N again, and
        the next one added follows on from N, not from the highest number
        the order ever had."""
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        url = reverse("operating:order_packing_list", args=[self.order.pk])
        p1, p2, p3 = (Pack.objects.create(order=self.order, pack_number=n) for n in (1, 2, 3))

        r = self.client.post(url, {"action": "delete_pack", "pack_id": p2.pk})
        self.assertTrue(r.json()["ok"])
        self.assertEqual(r.json()["numbers"], {str(p1.pk): 1, str(p3.pk): 2})
        p3.refresh_from_db()
        self.assertEqual((p3.pack_number, p3.code, p3.qr_code_url), (2, "PK-DK0000008-2", None))

        # Delete down to the last package: it becomes #1, and a new one is #2.
        self.client.post(url, {"action": "delete_pack", "pack_id": p1.pk})
        p3.refresh_from_db()
        self.assertEqual(p3.pack_number, 1)
        r = self.client.post(url, {"action": "add_pack"})
        self.assertEqual(r.json()["pack"]["number"], 2)

    @patch('marketing.utils.bunny_storage.upload_to_bunny')
    def test_reorder_packs_renumbers_in_dropped_order(self, mock_upload):
        """Dragging packages into a new order numbers them by where they
        now stand, carrying their contents — a straight swap included,
        which would trip unique (order, pack_number) if written through."""
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        url = reverse("operating:order_packing_list", args=[self.order.pk])
        p1, p2, p3 = (Pack.objects.create(order=self.order, pack_number=n) for n in (1, 2, 3))
        packed = PackedOrderItem.objects.create(pack=p3, order_item=self.order_item)

        r = self.client.post(url, {"action": "reorder_packs", "pack_ids": f"{p3.pk},{p1.pk},{p2.pk}"})
        self.assertEqual(r.json(), {"ok": True, "numbers": {str(p3.pk): 1, str(p1.pk): 2, str(p2.pk): 3}})
        p3.refresh_from_db()
        self.assertEqual((p3.pack_number, p3.code, p3.qr_code_url), (1, "PK-DK0000008-1", None))
        packed.refresh_from_db()
        self.assertEqual(packed.pack_id, p3.pk)

        # A list that misses a package (a stale screen) changes nothing.
        r = self.client.post(url, {"action": "reorder_packs", "pack_ids": f"{p1.pk},{p2.pk}"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(
            list(self.order.packs.order_by("pack_number").values_list("pk", flat=True)),
            [p3.pk, p1.pk, p2.pk])
