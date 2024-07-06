from django.urls import path
from . import views
from .views import ExpenseView, CategorySearchView

app_name = 'accounting'
urlpatterns = [
    path("", views.index.as_view(),name="index"),
    path('report_expense/', ExpenseView.as_view(), name='report_expense'),
    path('category_search/', CategorySearchView.as_view(), name='category_search'),
]