"""An order's files: the customer's own PO, a proforma, sketches and
photos they sent (the shared attachments, erp.attachments). Cargo receipts
stay their own thing (OrderCargoReceipt): they are part of shipping.

The routes are guarded in the URLconf the way the order's picking list
is, so the files open for the people who may open the order.
"""
from django.shortcuts import get_object_or_404

from erp.attachments import record_file_views

from .models import Order

order_files, order_file, order_file_delete = record_file_views(
    "Operating/orders", lambda pk: get_object_or_404(Order, pk=pk), "operating:order_files")
