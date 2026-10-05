from django.urls import path
# from . import views
from .views import *
from .book_scope import book_page
# from django.contrib.auth.decorators import login_required

app_name = 'accounting'

# Book-scoped actions reached from the sidebar. The menu is built from
# erp/nav.py, which cannot pass a book id, so each of these resolves the
# member's working book and forwards. Named `go_*` so a reader can tell at
# a glance that the route is a redirect and not a page of its own.
_working_book_routes = [
    ("go_add_capital",      "accounting:add_equity_capital"),
    ("go_add_revenue",      "accounting:add_equity_revenue"),
    ("go_add_expense",      "accounting:add_equity_expense"),
    ("go_pay_dividend",     "accounting:add_equity_divident"),
    ("go_add_asset",        "accounting:add_fixed_asset"),
    ("go_add_cash_account", "accounting:add_cash_account"),
    ("go_transactions",     "accounting:cash_transaction_entry_list"),
    ("go_expenses",         "accounting:equity_expense_list"),
    ("go_transfer",         "accounting:make_in_transfer"),
    ("go_currency_exchange", "accounting:make_currency_exchange"),
    ("go_cap_table",        "accounting:book_shares"),
    ("go_add_stakeholder",  "accounting:add_stakeholderbook"),
]

urlpatterns = [
    path("", index.as_view(),name="index"),
    *[
        path(f"go/{name.removeprefix('go_')}/",
             WorkingBookRedirect.as_view(target=target),
             name=name)
        for name, target in _working_book_routes
    ],
    # path('report_expense/', ExpenseView.as_view(), name='report_expense'),
    path('category_search/', CategorySearchView.as_view(), name='category_search'),
    path('sales/',SalesView.as_view(),name="sales_view"),
    path('sales-dashboard/', SalesDashboardView.as_view(), name='sales_dashboard'),
    # path('books/',BookView.as_view(),name="book_view"),
    path('books/create/',CreateBook.as_view(),name="create_book"),
    # path('books/<int:pk>/',login_required(BookDetail.as_view()),name="book_detail"),
    path('books/<int:pk>/',book_page(BookDetail.as_view()),name="book_detail"),
    path('books/<int:pk>/rename/', book_page(RenameBook.as_view()), name="rename_book"),
    path('books/<int:pk>/brand_name/', book_page(SetBookBrandName.as_view()), name="set_book_brand_name"),
    path('books/<int:pk>/work_here/', SetMyWorkingBook.as_view(), name="set_my_working_book"),
    path('books/<int:pk>/shares/', book_page(BookShares.as_view()), name="book_shares"),
    path('books/<int:pk>/cash_accounts/new/', book_page(AddCashAccount.as_view()), name="add_cash_account"),
    path('books/<int:pk>/cash_accounts/<int:account_pk>/edit/', book_page(EditCashAccount.as_view()), name="edit_cash_account"),
    path('books/<int:pk>/add_stakeholderbook/', book_page(AddStakeholderBook.as_view()),name="add_stakeholderbook"),
    path('books/<int:pk>/add_equity_capital/', book_page(AddEquityCapital.as_view()),name="add_equity_capital"),
    path('books/<int:pk>/add_equity_revenue/',book_page(AddEquityRevenue.as_view()),name="add_equity_revenue"),
    path('books/<int:pk>/add_equity_expense/', book_page(AddEquityExpense.as_view()),name="add_equity_expense"),
    path('books/<int:pk>/revenues/<int:source_pk>/', book_page(EquityRevenueDetail.as_view()),name="equity_revenue_detail"),
    path('books/<int:pk>/revenues/<int:source_pk>/edit/', book_page(EditEquityRevenue.as_view()),name="edit_equity_revenue"),
    path('books/<int:pk>/revenues/<int:source_pk>/delete/', book_page(DeleteEquityRevenue.as_view()),name="delete_equity_revenue"),
    path('books/<int:pk>/capital/<int:source_pk>/', book_page(EquityCapitalDetail.as_view()),name="equity_capital_detail"),
    path('books/<int:pk>/capital/<int:source_pk>/edit/', book_page(EditEquityCapital.as_view()),name="edit_equity_capital"),
    path('books/<int:pk>/capital/<int:source_pk>/delete/', book_page(DeleteEquityCapital.as_view()),name="delete_equity_capital"),
    path('books/<int:pk>/exchanges/<int:source_pk>/', book_page(EquityExchangeDetail.as_view()),name="equity_exchange_detail"),
    path('books/<int:pk>/exchanges/<int:source_pk>/edit/', book_page(EditEquityExchange.as_view()),name="edit_equity_exchange"),
    path('books/<int:pk>/exchanges/<int:source_pk>/delete/', book_page(DeleteEquityExchange.as_view()),name="delete_equity_exchange"),
    path('books/<int:pk>/dividends/<int:source_pk>/', book_page(EquityDividendDetail.as_view()),name="equity_dividend_detail"),
    path('books/<int:pk>/dividends/<int:source_pk>/edit/', book_page(EditEquityDividend.as_view()),name="edit_equity_dividend"),
    path('books/<int:pk>/dividends/<int:source_pk>/delete/', book_page(DeleteEquityDividend.as_view()),name="delete_equity_dividend"),
    path('books/<int:pk>/transfers/<int:source_pk>/', book_page(EquityTransferDetail.as_view()),name="equity_transfer_detail"),
    path('books/<int:pk>/transfers/<int:source_pk>/edit/', book_page(EditEquityTransfer.as_view()),name="edit_equity_transfer"),
    path('books/<int:pk>/transfers/<int:source_pk>/delete/', book_page(DeleteEquityTransfer.as_view()),name="delete_equity_transfer"),
    path('books/<int:pk>/add_equity_divident/', book_page(AddEquityDivident.as_view()),name="add_equity_divident"),
    path('books/<int:pk>/equity_expense_list/', book_page(EquityExpenseList.as_view()),name="equity_expense_list"),
    # The entry itself at expenses/<pk>/, the form to change it one level
    # deeper — the shape every other document here already has
    # (invoices/<pk>/ and invoices/<pk>/edit/). A saved expense lands on
    # the first of these; the second is only reached by asking to edit.
    path('books/<int:pk>/expenses/<int:expense_pk>/', book_page(EquityExpenseDetail.as_view()),name="equity_expense_detail"),
    path('books/<int:pk>/expenses/<int:expense_pk>/edit/', book_page(EditEquityExpense.as_view()),name="edit_equity_expense"),
    path('books/<int:pk>/expenses/<int:expense_pk>/delete/', book_page(DeleteEquityExpense.as_view()),name="delete_equity_expense"),
    # path('books/<int:pk>/create_invoice/', InvoiceCreateView.as_view(),name="create_invoice"),
    path('books/<int:pk>/make_in_transfer/', book_page(MakeInTransfer.as_view()),name="make_in_transfer"),
    path('books/<int:pk>/make_currency_exchange/', book_page(MakeCurrencyExchange.as_view()),name="make_currency_exchange"),
    path('books/<int:pk>/cash_transaction_entry_list/', book_page(CashTransactionEntryList.as_view()),name="cash_transaction_entry_list"),
    path('books/<int:pk>/create_asset_inventory_raw_material_good/', book_page(CreateAssetInventoryRawMaterialGood.as_view()),name="create_asset_inventory_raw_material_good"),
    path('books/<int:pk>/raw_goods_receipt/',book_page(CreateAssetInventoryRawMaterialGood.as_view()),name="raw_goods_receipt"),
    path('books/<int:pk>/add_fixed_asset/',book_page(AddFixedAsset.as_view()),name="add_fixed_asset"),
    path('books/<int:pk>/edit_fixed_asset/<int:asset_pk>/',book_page(EditFixedAsset.as_view()),name="edit_fixed_asset"),
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