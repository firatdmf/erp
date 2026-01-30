from django.urls import path
from . import views
from django.views.generic import TemplateView


app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("orders/create/", views.create_web_order, name="create_web_order"),
    path("orders/create", views.OrderCreate.as_view(), name="create_order"),
    path("orders/edit/<int:pk>/", views.OrderEdit.as_view(), name="edit_order"),
    path("orders/web/<int:pk>/status/", views.WebOrderStatusEdit.as_view(), name="web_order_status"),
    path("orders/<int:pk>/", views.OrderDetail.as_view(), name="order_detail"),
    path("orders/", views.OrderList.as_view(), name="order_list"),
    path("orders/analytics/", views.OrderAnalytics.as_view(), name="order_analytics"),
    path("orders/delete/<int:pk>/", views.delete_order, name="delete_order"),
    path(
        "orders/<int:pk>/production/",
        views.OrderProduction.as_view(),
        name="order_production",
    ),
    path(
        "orders/<int:pk>/packing_list/",
        views.OrderPackingList.as_view(),
        name="order_packing_list",
    ),
    # path("create_product/",views.CreateProduct.as_view(),name="create_product"),
    # path("product_list/",views.Product.as_view(),name="product_list"),
    path(
        "orders/<int:pk>/packing_list/export_excel/",
        views.export_packing_list_excel,
        name="export_packing_list_excel",
    ),
    path(
        "raw_material_good/list",
        views.RawMaterialGoodList.as_view(),
        name="raw_material_good_list",
    ),
    path(
        "raw_material_good/create",
        views.RawMaterialGoodCreate.as_view(),
        name="create_raw_material_good",
    ),
    path(
        "raw_material_good_receipt/create",
        views.RawMaterialGoodReceiptCreate.as_view(),
        name="create_raw_material_good_receipt",
    ),
    path(
        "raw_material_good_item/create",
        views.RawMaterialGoodItemCreate.as_view(),
        name="create_raw_material_good_item",
    ),
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
    path(
        "scan_order_item_unit/",
        views.OrderItemUnitScan.as_view(),
        name="scan_order_item_unit",
    ),
    path(
        "scan_order_item_unit_pack/",
        views.OrderItemUnitScanPack.as_view(),
        name="scan_order_item_unit_pack",
    ),
    path(
        "prcocess_qr_payload_pack/",
        views.process_qr_payload_pack,
        name="process_qr_payload_pack",
    ),
    path("process-qr/", views.process_qr_payload, name="process_qr_payload"),
    path(
        "generate_pdf_qr_for_order_item_units/<int:pk>/",
        views.generate_pdf_qr_for_order_item_units,
        name="generate_pdf_qr_for_order_item_units",
    ),
    path(
        "raw_material_good/create/json",
        views.create_raw_material_good_json,
        name="create_raw_material_good_json",
    ),
    path(
        "raw_material_good_receipt/create/json",
        views.create_raw_material_good_receipt_json,
        name="create_raw_material_good_receipt_json",
    ),
    path(
        "raw_material_good_item/create/json",
        views.create_raw_material_good_item_json,
        name="create_raw_material_good_item_json",
    ),
    path(
        "raw_material_good_receipt/create/partial",
        views.create_raw_material_receipt_partial,
        name="create_raw_material_receipt_partial",
    ),
    path(
        "raw_material_good_item/create/partial",
        views.create_raw_material_item_partial,
        name="create_raw_material_item_partial",
    ),
    path(
        "raw_material_good/<int:pk>/get/json",
        views.get_raw_material_good_json,
        name="get_raw_material_good_json",
    ),
    path(
        "raw_material_good/<int:pk>/update/json",
        views.update_raw_material_good_json,
        name="update_raw_material_good_json",
    ),
    path(
        "raw_material_good/<int:pk>/delete/json",
        views.delete_raw_material_good_json,
        name="delete_raw_material_good_json",
    ),
]
htmx_urlpatterns = [
    path(
        "product_autocomplete/", views.product_autocomplete, name="product_autocomplete"
    ),
    path("start_production/", views.start_production, name="start_production"),
    # BOM Autocomplete
    path("raw_material_search/", views.raw_material_search, name="raw_material_search"),
]

api_urlpatterns = [
    path(
        "api/get_order_status/<int:order_id>/",
        views.get_order_status,
        name="get_order_status",
    ),
    path(
        "orders/<int:order_id>/update-ettn/",
        views.update_order_ettn,
        name="update-order-ettn",
    ),
    path(
        "api/get_order_detail/<int:user_id>/<int:order_id>/",
        views.get_order_detail_api,
        name="get_order_detail_api",
    ),
    # Order Tracking API endpoints
    path(
        "orders/track/",
        views.track_order,
        name="track_order",
    ),
    path(
        "orders/<int:order_id>/update-status/",
        views.update_order_status,
        name="update_order_status",
    ),
]

urlpatterns += htmx_urlpatterns
urlpatterns += api_urlpatterns
