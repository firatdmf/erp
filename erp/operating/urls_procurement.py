from django.urls import path
from . import views_procurement as views

# No namespace declared here: these patterns are included into operating/urls.py,
# so the names live in the `operating:` namespace with the rest of the app. They
# carry a purchase_ prefix because `order_list` and `order_detail` already mean
# a sales order there.
urlpatterns = [
    # Purchase Requests
    path("requests/", views.PurchaseRequestListView.as_view(), name="purchase_request_list"),
    path("requests/create/", views.PurchaseRequestCreateView.as_view(), name="purchase_request_create"),
    path("requests/create/partial/", views.create_request_partial, name="purchase_request_create_partial"),
    path("requests/<int:pk>/", views.PurchaseRequestDetailView.as_view(), name="purchase_request_detail"),
    
    # Purchase Orders
    path("orders/", views.PurchaseOrderListView.as_view(), name="purchase_order_list"),
    path("orders/create/", views.PurchaseOrderCreateView.as_view(), name="purchase_order_create"),
    path("orders/create/partial/", views.create_order_partial, name="purchase_order_create_partial"),
    path("orders/<int:pk>/", views.PurchaseOrderDetailView.as_view(), name="purchase_order_detail"),
]
