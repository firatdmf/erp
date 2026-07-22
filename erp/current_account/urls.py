from django.urls import path

from django.views.generic import TemplateView

from . import views, views_invoice, views_payment, views_report, views_check, views_purchase, invoice_excel

app_name = "current_account"

urlpatterns = [
    # --- Cari (Phase 1) ---
    path("",                       views.CariList.as_view(),           name="cari_list"),
    path("yeni/",                  views.CariCreate.as_view(),         name="cari_create"),
    path("<int:pk>/",              views.CariDetail.as_view(),         name="cari_detail"),
    path("<int:pk>/ekstre/",       views.CariStatement.as_view(),      name="cari_statement"),
    path("ekstre/tumu/",           views.CariStatementAll.as_view(),   name="cari_statement_all"),
    path("<int:pk>/duzenle/",      views.CariEdit.as_view(),           name="cari_edit"),
    path("<int:pk>/sil/",          views.CariDelete.as_view(),         name="cari_delete"),
    path("<int:pk>/hareket/yeni/", views.CariMovementCreate.as_view(), name="movement_create"),

    # --- Invoice (Phase 2) ---
    path("fatura/",                  views_invoice.InvoiceList.as_view(),   name="invoice_list"),
    path("fatura/yeni/",             views_invoice.InvoiceCreate.as_view(), name="invoice_create"),
    path("fatura/<int:pk>/",         views_invoice.InvoiceDetail.as_view(), name="invoice_detail"),
    path("fatura/<int:pk>/excel/",   invoice_excel.invoice_excel,           name="invoice_excel"),
    path("fatura/<int:pk>/duzenle/", views_invoice.InvoiceEdit.as_view(),   name="invoice_edit"),
    path("fatura/<int:pk>/kes/",     views_invoice.InvoiceIssue.as_view(),  name="invoice_issue"),
    path("fatura/<int:pk>/iptal/",   views_invoice.InvoiceCancel.as_view(),  name="invoice_cancel"),
    path("fatura/<int:pk>/geri-al/", views_invoice.InvoiceRestore.as_view(), name="invoice_restore"),
    path("fatura/<int:pk>/sil/",     views_invoice.InvoiceDelete.as_view(),  name="invoice_delete"),

    # --- Purchase orders (warehouse intake, not a generic invoice view) ---
    path("satin-alma/",              views_purchase.PurchaseOrderList.as_view(),   name="purchase_order_list"),
    path("satin-alma/<int:pk>/",     views_purchase.PurchaseOrderDetail.as_view(), name="purchase_order_detail"),
    path("satin-alma/<int:pk>/iptal/", views_purchase.PurchaseCancel.as_view(),    name="purchase_cancel"),

    # --- Payment (Phase 3) ---
    path("tahsilat/",                  views_payment.PaymentList.as_view(),    name="payment_list"),
    path("tahsilat/yeni/",             views_payment.PaymentCreate.as_view(),  name="payment_create"),
    path("tahsilat/<int:pk>/",         views_payment.PaymentDetail.as_view(),  name="payment_detail"),
    path("tahsilat/<int:pk>/onayla/",  views_payment.PaymentConfirm.as_view(), name="payment_confirm"),
    path("tahsilat/<int:pk>/iptal/",   views_payment.PaymentCancel.as_view(),  name="payment_cancel"),
    path("tahsilat/<int:pk>/sil/",     views_payment.PaymentDelete.as_view(),  name="payment_delete"),

    # --- Reports (Phase 4) ---
    path("rapor/",                views_report.ReportIndex.as_view(),       name="report_index"),
    path("rapor/yaslandirma/",    views_report.AgingReport.as_view(),       name="report_aging"),
    path("rapor/mizan/",          views_report.TrialBalance.as_view(),      name="report_trial_balance"),
    path("rapor/risk-limiti/",    views_report.CreditLimitReport.as_view(), name="report_credit_limit"),
    path("rapor/vade-takvimi/",   views_report.DueCalendar.as_view(),       name="report_due_calendar"),

    # --- Help / Documentation ---
    path("help/", TemplateView.as_view(template_name="current_account/help.html"), name="help"),

    # --- Çek / Senet (Phase 5) ---
    path("cek-senet/",                       views_check.CheckList.as_view(),    name="check_list"),
    path("cek-senet/yeni/",                  views_check.CheckCreate.as_view(),  name="check_create"),
    path("cek-senet/<int:pk>/",              views_check.CheckDetail.as_view(),  name="check_detail"),
    path("cek-senet/<int:pk>/ciro/",         views_check.CheckEndorse.as_view(), name="check_endorse"),
    path("cek-senet/<int:pk>/bankaya-ver/",  views_check.CheckDeposit.as_view(), name="check_deposit"),
    path("cek-senet/<int:pk>/tahsil/",       views_check.CheckClear.as_view(),   name="check_clear"),
    path("cek-senet/<int:pk>/karsiliksiz/",  views_check.CheckBounce.as_view(),  name="check_bounce"),
    path("cek-senet/<int:pk>/iptal/",        views_check.CheckCancel.as_view(),  name="check_cancel"),
]
