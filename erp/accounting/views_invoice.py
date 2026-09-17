"""
Invoice views.

An invoice is a printout of a sales order or a purchase, built live from
that record (accounting/invoice_doc.py). Nothing here issues, edits or
cancels anything — change the order or the purchase and the invoice
follows. The page is print only and speaks the app's current language;
the Excel download is the one other form it takes.

    /operating/orders/<id>/invoice/               → OrderInvoice
    /operating/orders/<id>/invoice/excel/         → order_invoice_excel
    /accounting/accounts/purchases/<id>/invoice/  → PurchaseInvoice
    /accounting/accounts/purchases/<id>/invoice/excel/ → purchase_invoice_excel
    /accounting/accounts/invoices/<id>/           → InvoiceRedirect (old links)
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .invoice_doc import build_order_doc, build_purchase_doc
from .invoice_excel import workbook_response
from .models import Invoice


def _render_doc(request, doc):
    return render(request, "accounts/invoice_document.html", {"doc": doc})


def _order(pk):
    from operating.models import Order
    return get_object_or_404(
        Order.objects.select_related("current_account__book",
                                     "current_account__default_currency"),
        pk=pk,
    )


def _purchase(pk):
    return get_object_or_404(
        Invoice.objects.select_related("current_account", "currency", "book"),
        pk=pk, type="purchase",
    )


@method_decorator(login_required, name="dispatch")
class OrderInvoice(View):
    def get(self, request, pk):
        return _render_doc(request, build_order_doc(_order(pk)))


@login_required
def order_invoice_excel(request, pk):
    return workbook_response(build_order_doc(_order(pk)))


@method_decorator(login_required, name="dispatch")
class PurchaseInvoice(View):
    def get(self, request, pk):
        return _render_doc(request, build_purchase_doc(_purchase(pk)))


@login_required
def purchase_invoice_excel(request, pk):
    return workbook_response(build_purchase_doc(_purchase(pk)))


@method_decorator(login_required, name="dispatch")
class InvoiceRedirect(View):
    """The old invoice page. Bookmarks, emails and ledger rows still point
    here, so it sends each to what the invoice mirrored: a purchase to its
    purchase page, an order's invoice to the order's invoice, anything
    else to its account."""

    def get(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        if inv.type == "purchase":
            return redirect("accounts:purchase_order_detail", pk=inv.pk)
        if inv.order_id:
            return redirect("operating:order_invoice", pk=inv.order_id)
        return redirect("accounts:detail", pk=inv.current_account_id)

