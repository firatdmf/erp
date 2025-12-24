from django.urls import path
# from . import views
from .views import *
# from django.contrib.auth.decorators import login_required

app_name = 'accounting'
urlpatterns = [
    path("", index.as_view(),name="index"),
    # path('report_expense/', ExpenseView.as_view(), name='report_expense'),
    path('category_search/', CategorySearchView.as_view(), name='category_search'),
    path('sales/',SalesView.as_view(),name="sales_view"),
    path('sales-dashboard/', SalesDashboardView.as_view(), name='sales_dashboard'),
    # path('books/',BookView.as_view(),name="book_view"),
    path('books/create/',CreateBook.as_view(),name="create_book"),
    # path('books/<int:pk>/',login_required(BookDetail.as_view()),name="book_detail"),
    path('books/<int:pk>/',BookDetail.as_view(),name="book_detail"),
    path('books/<int:pk>/add_stakeholderbook/', AddStakeholderBook.as_view(),name="add_stakeholderbook"),
    path('books/<int:pk>/add_equity_capital/', AddEquityCapital.as_view(),name="add_equity_capital"),
    path('books/<int:pk>/add_equity_revenue/',AddEquityRevenue.as_view(),name="add_equity_revenue"),
    path('books/<int:pk>/add_equity_expense/', AddEquityExpense.as_view(),name="add_equity_expense"),
    path('books/<int:pk>/add_equity_divident/', AddEquityDivident.as_view(),name="add_equity_divident"),
    path('books/<int:pk>/equity_expense_list/', EquityExpenseList.as_view(),name="equity_expense_list"),
    # path('books/<int:pk>/create_invoice/', InvoiceCreateView.as_view(),name="create_invoice"),
    path('books/<int:pk>/make_in_transfer/', MakeInTransfer.as_view(),name="make_in_transfer"),
    path('books/<int:pk>/make_currency_exchange/', MakeCurrencyExchange.as_view(),name="make_currency_exchange"),
    path('books/<int:pk>/add_accounts_receivable/', AddAccountsReceivable.as_view(),name="add_accounts_receivable"),
    path('books/<int:pk>/add_accounts_payable/', AddAccountsPayable.as_view(),name="add_accounts_payable"),
    path('books/<int:pk>/cash_transaction_entry_list/', CashTransactionEntryList.as_view(),name="cash_transaction_entry_list"),
    path('books/<int:pk>/create_asset_inventory_raw_material_good/', CreateAssetInventoryRawMaterialGood.as_view(),name="create_asset_inventory_raw_material_good"),
    path('books/<int:pk>/raw_goods_receipt/',CreateAssetInventoryRawMaterialGood.as_view(),name="raw_goods_receipt"),
    path('books/<int:pk>/finished_goods_receipt/',FinishedGoodsReceipt.as_view(),name="finished_goods_receipt"),
    path('books/<int:pk>/pay_liability_accounts_payable/',PayLiabilityAccountsPayable.as_view(),name="pay_liability_accounts_payable"),
    path('books/<int:pk>/get_asset_accounts_receivable/',GetAssetAccountsReceivable.as_view(),name="get_asset_accounts_receivable"),
    # path('books/<int:pk>/kpi_dashboard/',kpi_dashboard,name="kpi_dashboard"),
    # path("books/<int:pk>/material_lookup/", asset_inventory_raw_material_lookup, name="material_lookup"),

]

htmx_urlpatterns = [
path('add_expense/',index.as_view(),name="add_expense"),
# I don't know if I use the below at all
# path('get_expenses/',views.index.as_view(),name="get_expenses"),

# Adding income
path("add_income/",index.as_view(),name="add_income"),

# Add asset
path("add_asset/",index.as_view(),name="add_asset"),
# path("set_book/",views.BookView.as_view(),name="set_book")

]

urlpatterns += htmx_urlpatterns