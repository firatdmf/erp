"""Current-account (cari) routes, mounted at /accounting/.

Formerly the standalone ``current_account`` app served from /cari/. The
ledger belongs to accounting, so it lives here and the URLs read in
English: /accounting/accounts/, /accounting/invoices/, and so on.

Namespace is ``accounts`` rather than ``accounting`` so these names stay
separate from the older accounting routes (index, books, sales); reverse
them as ``accounts:list``, ``accounts:invoice_detail``, etc.

Routes come in two shapes.

COLLECTIONS name their book: /accounting/books/5/accounts/. A list, a
report or a create form has to be told which book's money it is about,
and putting that in the path rather than the session makes the page
bookmarkable and lets two tabs sit on two books at once. Each is wrapped
in ``book_scoped``, which resolves the id onto ``request.book`` and 404s
a book the viewer is not assigned.

OBJECTS do not: /accounting/accounts/912/. The row already knows its
book through its own FK, so repeating it in the path would only create
the possibility of the two disagreeing — /books/5/accounts/912/ where
912 belongs to book 2 — a mismatch every view would then have to check
for. These paths are unchanged from before the split.

Legacy unscoped collection URLs (/accounting/accounts/, and the rest as
they were) are kept as redirects to the viewer's working book, so old
bookmarks and links still land somewhere sensible.

Route ordering note: the literal segments that sit alongside an
``<int:pk>`` capture (invoices/settings/, statement/all/) are safe in any
order because ``int`` never matches a word, but they are listed first
anyway so the intent is obvious.
"""
from django.urls import path
from django.views.generic import TemplateView

from . import (
    invoice_excel,
    views_check,
    views_invoice,
    views_payment,
    views_purchase,
    views_report,
)
from . import views_accounts as views
from .book_scope import book_scoped
from .views_accounts import LegacyCollectionRedirect as _Legacy

app_name = "accounts"


def scoped(route, view, name):
    """A collection page, addressed by book."""
    return path(f"books/<int:book_id>/{route}", book_scoped(view), name=name)


def legacy(route, name):
    """The pre-split URL, redirecting to the same page in the viewer's
    working book so old links keep working."""
    return path(route, _Legacy.as_view(target=f"accounts:{name}"),
                name=f"legacy_{name}")

urlpatterns = [
    # ------------------------------------------------------------------
    # Collections — one book's worth, named in the path.
    # ------------------------------------------------------------------
    scoped("accounts/",                  views.CariList.as_view(),           "list"),
    scoped("accounts/new/",              views.CariCreate.as_view(),         "create"),
    scoped("accounts/statement/",        views.CariStatementAll.as_view(),   "statement_all"),
    scoped("accounts/retail/",           views.RetailCariRedirect.as_view(), "retail"),

    scoped("invoices/",                  views_invoice.InvoiceList.as_view(),           "invoice_list"),
    scoped("invoices/new/",              views_invoice.InvoiceCreate.as_view(),         "invoice_create"),
    scoped("invoices/settings/",         views_invoice.InvoiceSettingsUpdate.as_view(), "invoice_settings"),

    scoped("purchases/",                 views_purchase.PurchaseOrderList.as_view(), "purchase_order_list"),
    scoped("purchases/new/",             views_purchase.GoodsReceipt.as_view(),      "goods_receipt"),
    scoped("purchases/order/",           views_purchase.PurchaseOrderSave.as_view(), "purchase_order_save"),

    scoped("payments/",                  views_payment.PaymentList.as_view(),   "payment_list"),
    scoped("payments/new/",              views_payment.PaymentCreate.as_view(), "payment_create"),

    scoped("reports/",                   views_report.ReportIndex.as_view(),       "report_index"),
    scoped("reports/aging/",             views_report.AgingReport.as_view(),       "report_aging"),
    scoped("reports/trial-balance/",     views_report.TrialBalance.as_view(),      "report_trial_balance"),
    scoped("reports/credit-limit/",      views_report.CreditLimitReport.as_view(), "report_credit_limit"),
    scoped("reports/due-calendar/",      views_report.DueCalendar.as_view(),       "report_due_calendar"),

    scoped("checks/",                    views_check.CheckList.as_view(),   "check_list"),
    scoped("checks/new/",                views_check.CheckCreate.as_view(), "check_create"),

    # ------------------------------------------------------------------
    # Objects — the row names its own book, so the path does not.
    # ------------------------------------------------------------------
    path("accounts/<int:pk>/",                 views.CariDetail.as_view(),         name="detail"),
    path("accounts/<int:pk>/statement/",       views.CariStatement.as_view(),      name="statement"),
    path("accounts/<int:pk>/edit/",            views.CariEdit.as_view(),           name="edit"),
    path("accounts/<int:pk>/delete/",          views.CariDelete.as_view(),         name="delete"),
    path("accounts/<int:pk>/movements/new/",   views.CariMovementCreate.as_view(), name="movement_create"),
    path("accounts/<int:pk>/movements/<int:mv_pk>/",        views.CariMovementDetail.as_view(), name="movement_detail"),
    path("accounts/<int:pk>/movements/<int:mv_pk>/edit/",   views.CariMovementEdit.as_view(),   name="movement_edit"),
    path("accounts/<int:pk>/movements/<int:mv_pk>/delete/", views.CariMovementDelete.as_view(), name="movement_delete"),

    # A transfer belongs to two accounts, so it is not nested under either.
    path("accounts/transfers/<int:pk>/",      views.CariTransferDetail.as_view(), name="transfer_detail"),
    path("accounts/transfers/<int:pk>/edit/", views.CariTransferEdit.as_view(),   name="transfer_edit"),
    path("accounts/transfers/<int:pk>/undo/", views.CariTransferUndo.as_view(),   name="transfer_undo"),

    path("accounts/invoices/<int:pk>/",         views_invoice.InvoiceDetail.as_view(),  name="invoice_detail"),
    path("accounts/invoices/<int:pk>/excel/",   invoice_excel.invoice_excel,            name="invoice_excel"),
    path("accounts/invoices/<int:pk>/edit/",    views_invoice.InvoiceEdit.as_view(),    name="invoice_edit"),
    path("accounts/invoices/<int:pk>/issue/",   views_invoice.InvoiceIssue.as_view(),   name="invoice_issue"),
    path("accounts/invoices/<int:pk>/cancel/",  views_invoice.InvoiceCancel.as_view(),  name="invoice_cancel"),
    path("accounts/invoices/<int:pk>/restore/", views_invoice.InvoiceRestore.as_view(), name="invoice_restore"),
    path("accounts/invoices/<int:pk>/delete/",  views_invoice.InvoiceDelete.as_view(),  name="invoice_delete"),

    path("accounts/purchases/<int:pk>/order/",   views_purchase.PurchaseOrderSave.as_view(),    name="purchase_order_update"),
    path("accounts/purchases/<int:pk>/confirm/", views_purchase.PurchaseOrderConfirm.as_view(), name="purchase_order_confirm"),
    path("accounts/purchases/<int:pk>/print/",   views_purchase.PurchaseOrderPrint.as_view(),   name="purchase_order_print"),
    path("accounts/purchases/<int:pk>/",         views_purchase.PurchaseOrderDetail.as_view(),  name="purchase_order_detail"),
    path("accounts/purchases/<int:pk>/edit/",    views_purchase.GoodsReceipt.as_view(),         name="goods_receipt_edit"),
    path("accounts/purchases/<int:pk>/cancel/",  views_purchase.PurchaseCancel.as_view(),       name="purchase_cancel"),

    path("accounts/payments/<int:pk>/",         views_payment.PaymentDetail.as_view(),  name="payment_detail"),
    path("accounts/payments/<int:pk>/edit/",    views_payment.PaymentEdit.as_view(),    name="payment_edit"),
    path("accounts/payments/<int:pk>/confirm/", views_payment.PaymentConfirm.as_view(), name="payment_confirm"),
    path("accounts/payments/<int:pk>/cancel/",  views_payment.PaymentCancel.as_view(),  name="payment_cancel"),
    path("accounts/payments/<int:pk>/delete/",  views_payment.PaymentDelete.as_view(),  name="payment_delete"),

    path("accounts/checks/<int:pk>/",         views_check.CheckDetail.as_view(),  name="check_detail"),
    path("accounts/checks/<int:pk>/endorse/", views_check.CheckEndorse.as_view(), name="check_endorse"),
    path("accounts/checks/<int:pk>/deposit/", views_check.CheckDeposit.as_view(), name="check_deposit"),
    path("accounts/checks/<int:pk>/clear/",   views_check.CheckClear.as_view(),   name="check_clear"),
    path("accounts/checks/<int:pk>/bounce/",  views_check.CheckBounce.as_view(),  name="check_bounce"),
    path("accounts/checks/<int:pk>/cancel/",  views_check.CheckCancel.as_view(),  name="check_cancel"),

    # ------------------------------------------------------------------
    # Book-independent.
    # ------------------------------------------------------------------
    # An FX rate is a fact about two currencies on a date; no book owns it.
    path("accounts/payments/fx-rate/", views_payment.fx_rate_lookup, name="fx_rate_lookup"),
    path("accounts/help/", TemplateView.as_view(
        template_name="accounts/help.html"), name="help"),

    # ------------------------------------------------------------------
    # Pre-split URLs, redirected to the same page in the working book.
    # ------------------------------------------------------------------
    legacy("accounts/",           "list"),
    legacy("accounts/new/",       "create"),
    legacy("accounts/statement/all/", "statement_all"),
    legacy("accounts/retail/",    "retail"),
    legacy("accounts/invoices/",  "invoice_list"),
    legacy("accounts/invoices/new/",      "invoice_create"),
    legacy("accounts/invoices/settings/", "invoice_settings"),
    legacy("accounts/purchases/", "purchase_order_list"),
    legacy("accounts/purchases/new/", "goods_receipt"),
    legacy("accounts/payments/",  "payment_list"),
    legacy("accounts/payments/new/", "payment_create"),
    legacy("accounts/reports/",   "report_index"),
    legacy("accounts/reports/aging/", "report_aging"),
    legacy("accounts/reports/trial-balance/", "report_trial_balance"),
    legacy("accounts/reports/credit-limit/",  "report_credit_limit"),
    legacy("accounts/reports/due-calendar/",  "report_due_calendar"),
    legacy("accounts/checks/",    "check_list"),
    legacy("accounts/checks/new/", "check_create"),
]
