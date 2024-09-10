from django.urls import path
from . import views
from .views import CategorySearchView, SalesView,BookDetail,CreateAsset

app_name = 'accounting'
urlpatterns = [
    path("", views.index.as_view(),name="index"),
    # path('report_expense/', ExpenseView.as_view(), name='report_expense'),
    path('category_search/', CategorySearchView.as_view(), name='category_search'),
    path('sales/',SalesView.as_view(),name="sales_view"),
    # path('books/',BookView.as_view(),name="book_view"),
    path('books/<int:pk>/',BookDetail.as_view(),name="book_detail"),
    path('books/<int:pk>/create_asset/',CreateAsset.as_view(),name="create_asset")
]

htmx_urlpatterns = [
path('add_expense/',views.index.as_view(),name="add_expense"),
# I don't know if I use the below at all
# path('get_expenses/',views.index.as_view(),name="get_expenses"),

# Adding income
path("add_income/",views.index.as_view(),name="add_income"),

# Add asset
path("add_asset/",views.index.as_view(),name="add_asset"),
# path("set_book/",views.BookView.as_view(),name="set_book")

]

urlpatterns += htmx_urlpatterns