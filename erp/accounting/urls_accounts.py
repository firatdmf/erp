"""Current-account (cari) routes, mounted at /accounting/accounts/.

Formerly the standalone ``current_account`` app served from /cari/. The
ledger belongs to accounting, so it lives here and the URLs read in
English: /accounting/accounts/, /accounting/accounts/invoices/, and so on.

Namespace is ``accounts`` rather than ``accounting`` so these names stay
separate from the older accounting routes (index, books, sales); reverse
them as ``accounts:list``, ``accounts:invoice_detail``, etc.

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

app_name = "accounts"

urlpatterns = [
    # --- Accounts (cari) ---
    path("",                          views.CariList.as_view(),           name="list"),
    path("new/",                      views.CariCreate.as_view(),         name="create"),
    path("statement/all/",            views.CariStatementAll.as_view(),   name="statement_all"),
    path("<int:pk>/",                 views.CariDetail.as_view(),         name="detail"),
    path("<int:pk>/statement/",       views.CariStatement.as_view(),      name="statement"),
    path("<int:pk>/edit/",            views.CariEdit.as_view(),           name="edit"),
    path("<int:pk>/delete/",          views.CariDelete.as_view(),         name="delete"),
    path("<int:pk>/movements/new/",   views.CariMovementCreate.as_view(), name="movement_create"),

    # --- Invoices ---
    path("invoices/",                    views_invoice.InvoiceList.as_view(),           name="invoice_list"),
    path("invoices/new/",                views_invoice.InvoiceCreate.as_view(),         name="invoice_create"),
    path("invoices/settings/",           views_invoice.InvoiceSettingsUpdate.as_view(), name="invoice_settings"),
    path("invoices/<int:pk>/",           views_invoice.InvoiceDetail.as_view(),         name="invoice_detail"),
    path("invoices/<int:pk>/excel/",     invoice_excel.invoice_excel,                   name="invoice_excel"),
    path("invoices/<int:pk>/edit/",      views_invoice.InvoiceEdit.as_view(),           name="invoice_edit"),
    path("invoices/<int:pk>/issue/",     views_invoice.InvoiceIssue.as_view(),          name="invoice_issue"),
    path("invoices/<int:pk>/cancel/",    views_invoice.InvoiceCancel.as_view(),         name="invoice_cancel"),
    path("invoices/<int:pk>/restore/",   views_invoice.InvoiceRestore.as_view(),        name="invoice_restore"),
    path("invoices/<int:pk>/delete/",    views_invoice.InvoiceDelete.as_view(),         name="invoice_delete"),

    # --- Purchase orders (warehouse intake, not a generic invoice view) ---
    path("purchases/",                   views_purchase.PurchaseOrderList.as_view(),   name="purchase_order_list"),
    path("purchases/<int:pk>/",          views_purchase.PurchaseOrderDetail.as_view(), name="purchase_order_detail"),
    path("purchases/<int:pk>/cancel/",   views_purchase.PurchaseCancel.as_view(),      name="purchase_cancel"),

    # --- Payments (tahsilat) ---
    path("payments/",                    views_payment.PaymentList.as_view(),    name="payment_list"),
    path("payments/new/",                views_payment.PaymentCreate.as_view(),  name="payment_create"),
    path("payments/<int:pk>/",           views_payment.PaymentDetail.as_view(),  name="payment_detail"),
    path("payments/<int:pk>/edit/",      views_payment.PaymentEdit.as_view(),    name="payment_edit"),
    path("payments/<int:pk>/confirm/",   views_payment.PaymentConfirm.as_view(), name="payment_confirm"),
    path("payments/<int:pk>/cancel/",    views_payment.PaymentCancel.as_view(),  name="payment_cancel"),
    path("payments/<int:pk>/delete/",    views_payment.PaymentDelete.as_view(),  name="payment_delete"),

    # --- Reports ---
    path("reports/",                 views_report.ReportIndex.as_view(),       name="report_index"),
    path("reports/aging/",           views_report.AgingReport.as_view(),       name="report_aging"),
    path("reports/trial-balance/",   views_report.TrialBalance.as_view(),      name="report_trial_balance"),
    path("reports/credit-limit/",    views_report.CreditLimitReport.as_view(), name="report_credit_limit"),
    path("reports/due-calendar/",    views_report.DueCalendar.as_view(),       name="report_due_calendar"),

    # --- Checks / promissory notes (çek & senet) ---
    path("checks/",                   views_check.CheckList.as_view(),    name="check_list"),
    path("checks/new/",               views_check.CheckCreate.as_view(),  name="check_create"),
    path("checks/<int:pk>/",          views_check.CheckDetail.as_view(),  name="check_detail"),
    path("checks/<int:pk>/endorse/",  views_check.CheckEndorse.as_view(), name="check_endorse"),
    path("checks/<int:pk>/deposit/",  views_check.CheckDeposit.as_view(), name="check_deposit"),
    path("checks/<int:pk>/clear/",    views_check.CheckClear.as_view(),   name="check_clear"),
    path("checks/<int:pk>/bounce/",   views_check.CheckBounce.as_view(),  name="check_bounce"),
    path("checks/<int:pk>/cancel/",   views_check.CheckCancel.as_view(),  name="check_cancel"),

    # --- Help / documentation ---
    path("help/", TemplateView.as_view(
        template_name="accounts/help.html"), name="help"),
]
