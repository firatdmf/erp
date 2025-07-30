from django.urls import path
from . import views
from django.views.generic import TemplateView


app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("orders/create", views.OrderCreate.as_view(), name="create_order"),
    path("orders/edit/<int:pk>/", views.OrderEdit.as_view(), name="edit_order"),
    path("orders/<int:pk>/", views.OrderDetail.as_view(), name="order_detail"),
    path("orders/", views.OrderList.as_view(), name="order_list"),
    path("orders/delete/<int:pk>/", views.delete_order, name="delete_order"),
    path(
        "orders/<int:pk>/production/",
        views.OrderProduction.as_view(),
        name="order_production",
    ),
    # path("create_product/",views.CreateProduct.as_view(),name="create_product"),
    # path("product_list/",views.Product.as_view(),name="product_list"),
    # below are for api paths
    path(
        "api/order/machine-update/", views.machine_update_status, name="machine_update"
    ),
    path(
        "machine/update-item/<int:item_id>/",
        views.MachineStatusUpdate.as_view(),
        name="machine-status-update",
    ),
    # path(
    #     "scan/",
    #     TemplateView.as_view(template_name="operating/scan.html"),
    #     name="qr_scan",
    # ),
    path("scan_order_item_unit/",views.OrderItemUnitScan.as_view(),name="scan_order_item_unit"),
    path("scan_order_item_unit_pack/",views.OrderItemUnitScanPack.as_view(),name="scan_order_item_unit_pack"),
    path("process-qr/", views.process_qr_payload, name="process_qr_payload"),
    path(
        "generate_pdf_qr_for_order_item_units/<int:pk>/",
        views.generate_pdf_qr_for_order_item_units,
        name="generate_pdf_qr_for_order_item_units",
    ),
]
htmx_urlpatterns = [
    path(
        "product_autocomplete/", views.product_autocomplete, name="product_autocomplete"
    ),
    path("start_production/", views.start_production, name="start_production"),
]

api_urlpatterns = [
    path("api/get_order_status/<int:order_id>/",views.get_order_status,name="get_order_status"),
]

urlpatterns += htmx_urlpatterns
urlpatterns += api_urlpatterns
