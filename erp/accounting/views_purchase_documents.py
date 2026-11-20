"""A purchase's documents: the supplier's invoice, a delivery note,
photos of the goods.

They are crm.Attachment rows hung off the purchase (Attachment.invoice),
stored and served the way a contact's files are (crm.views.save_uploads,
attachment_response), but reached only through the purchase: every
route here is book_guarded on the Invoice in the URLconf, so a document
opens for exactly the people the purchase opens for, and from the
purchasing paths a role without the ledger still reaches
(erp.roles.ACCOUNTS_OPEN_PREFIXES).
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from crm.models import Attachment
from crm.views import attachment_response, save_uploads

from .models import Invoice

# Their folder in the storage zone: accounting's, as a cargo receipt sits
# under Operating/orders/. One folder per purchase under it.
FOLDER = "Accounting/purchases"


def _purchase(pk):
    return get_object_or_404(Invoice, pk=pk, type="purchase")


def _document(pk, doc_pk):
    return get_object_or_404(Attachment.everywhere, pk=doc_pk, invoice_id=pk)


def documents_of(invoice):
    return (Attachment.everywhere.filter(invoice=invoice)
            .select_related("uploaded_by").order_by("-uploaded_at", "-id"))


def _list(request, invoice, errors=()):
    html = render_to_string("accounts/partials/_purchase_documents_list.html",
                            {"documents": documents_of(invoice), "invoice": invoice},
                            request=request)
    return JsonResponse({"success": not errors, "html": html, "errors": list(errors)})


@login_required
def purchase_documents(request, pk):
    """GET: the list. POST: files added (`files`), then the list."""
    invoice = _purchase(pk)
    if request.method == "POST":
        return _list(request, invoice, save_uploads(request, "invoice", invoice, folder=FOLDER))
    return _list(request, invoice)


@login_required
def purchase_document_file(request, pk, doc_pk):
    return attachment_response(_document(pk, doc_pk))


@login_required
def purchase_document_delete(request, pk, doc_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    _document(pk, doc_pk).delete()
    return _list(request, _purchase(pk))
