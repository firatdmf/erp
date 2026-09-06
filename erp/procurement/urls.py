from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    # Purchase Requests
    path("requests/", views.PurchaseRequestListView.as_view(), name="request_list"),
    path("requests/create/", views.PurchaseRequestCreateView.as_view(), name="request_create"),
    path("requests/create/partial/", views.create_request_partial, name="request_create_partial"),
    path("requests/<int:pk>/", views.PurchaseRequestDetailView.as_view(), name="request_detail"),
    
    # Purchase Orders
    path("orders/", views.PurchaseOrderListView.as_view(), name="order_list"),
    path("orders/create/", views.PurchaseOrderCreateView.as_view(), name="order_create"),
    path("orders/create/partial/", views.create_order_partial, name="order_create_partial"),
    path("orders/<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="order_detail"),
]
