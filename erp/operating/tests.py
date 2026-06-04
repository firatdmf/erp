from django.test import TestCase, Client
from django.urls import reverse
from .models import Order, Pack, PackedOrderItem, OrderItem, Product
from unittest.mock import patch

class PackTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))

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

