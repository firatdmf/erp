from django.urls import path
from . import views
from . import views_warehouse
from . import order_excel
from . import warehouse_label
from . import warehouse_excel
from django.views.generic import TemplateView, RedirectView


app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
    # Warehouse
    path("warehouses/", views_warehouse.WarehouseList.as_view(), name="warehouse_list"),
    # Global activity feed ("Son Hareketler") — all warehouses. Must sit
    # above warehouses/<int:pk>/ patterns (won't collide: int ≠ "movements").
    path("warehouses/movements/", views_warehouse.WarehouseMovementsAll.as_view(), name="warehouse_movements_all"),
    path("warehouses/create/", views_warehouse.WarehouseCreate.as_view(), name="create_warehouse"),
    path("warehouses/create/partial/", views_warehouse.WarehouseCreatePartial.as_view(), name="create_warehouse_partial"),
    path("warehouses/<int:pk>/", views_warehouse.WarehouseDetail.as_view(), name="warehouse_detail"),
    path("warehouses/<int:pk>/excel/", warehouse_excel.warehouse_excel, name="warehouse_excel"),
    path("warehouses/<int:pk>/group-variants/", views_warehouse.warehouse_group_variants, name="warehouse_group_variants"),
    path("warehouses/<int:pk>/catalog-search/", views_warehouse.catalog_base_search, name="catalog_base_search"),
    path("warehouses/<int:pk>/catalog-variants/<int:product_id>/", views_warehouse.catalog_product_variants, name="catalog_product_variants"),
    path("warehouses/<int:pk>/catalog-variant-match/<int:product_id>/", views_warehouse.catalog_variant_match, name="catalog_variant_match"),
    path("warehouses/<int:pk>/barcode-lookup/", views_warehouse.warehouse_barcode_lookup, name="warehouse_barcode_lookup"),
    path("warehouses/<int:pk>/rolls/<int:roll_pk>/move-here/", views_warehouse.warehouse_roll_move_here, name="warehouse_roll_move_here"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/label/", warehouse_label.warehouse_product_label, name="warehouse_product_label"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/code/", warehouse_label.warehouse_product_code, name="warehouse_product_code"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/info/", warehouse_label.warehouse_product_info, name="warehouse_product_info"),
    # Convenience: a mistyped/stale "label/info" path still lands on the info screen.
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/label/info/", RedirectView.as_view(pattern_name="operating:warehouse_product_info", permanent=False)),
    path("warehouses/<int:pk>/edit/", views_warehouse.WarehouseEdit.as_view(), name="warehouse_edit"),
    path("warehouses/<int:pk>/import/", views_warehouse.WarehouseProductImport.as_view(), name="warehouse_product_import"),
    path("warehouses/<int:pk>/delete/", views_warehouse.WarehouseDelete.as_view(), name="warehouse_delete"),
    path("warehouses/<int:pk>/scan/", views_warehouse.WarehouseRollScan.as_view(), name="warehouse_roll_scan"),
    path("warehouses/<int:pk>/manual-add/", views_warehouse.WarehouseManualAdd.as_view(), name="warehouse_manual_add"),
    path("warehouses/<int:pk>/purchase/<int:invoice_id>/edit/", views_warehouse.WarehousePurchaseEdit.as_view(), name="warehouse_purchase_edit"),
    path("warehouses/<int:pk>/next-sku/", views_warehouse.warehouse_next_sku, name="warehouse_next_sku"),
    path("warehouses/<int:pk>/merge-duplicates/", views_warehouse.WarehouseMergeDuplicates.as_view(), name="warehouse_merge_duplicates"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/", views_warehouse.WarehouseProductDetail.as_view(), name="warehouse_product_detail"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/edit/", views_warehouse.WarehouseProductEdit.as_view(), name="warehouse_product_edit"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/delete/", views_warehouse.WarehouseProductDelete.as_view(), name="warehouse_product_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/stock-out/", views_warehouse.WarehouseStockOut.as_view(), name="warehouse_stock_out"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/<int:roll_pk>/delete/", views_warehouse.WarehouseRollDelete.as_view(), name="warehouse_roll_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/bulk-delete/", views_warehouse.WarehouseRollBulkDelete.as_view(), name="warehouse_roll_bulk_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/<int:roll_pk>/edit/", views_warehouse.WarehouseRollEdit.as_view(), name="warehouse_roll_edit"),
    path("warehouses/<int:warehouse_pk>/movements/", views_warehouse.WarehouseMovements.as_view(), name="warehouse_movements"),
    path("orders/create/", views.create_web_order, name="create_web_order"),
    path("orders/create", views.OrderCreate.as_view(), name="create_order"),
    path("orders/edit/<int:pk>/", views.OrderEdit.as_view(), name="edit_order"),
    path("orders/web/<int:pk>/status/", views.WebOrderStatusEdit.as_view(), name="web_order_status"),
    path("orders/<int:pk>/", views.OrderDetail.as_view(), name="order_detail"),
    path("orders/<int:pk>/customer/", views.order_customer_card_view, name="order_customer_card"),
    path("orders/<int:pk>/print/", views.OrderPrint.as_view(), name="order_print"),
    path("orders/<int:pk>/print-header/", views.update_order_print_header, name="order_print_header"),
    path("orders/<int:pk>/changes/", views.order_changes, name="order_changes"),
    # Packing-scan flow (reserve warehouse rolls before shipping)
    path("orders/<int:pk>/pack/", views.order_pack_scan, name="order_pack_scan"),
    path("orders/<int:pk>/pack/add/", views.order_pack_reserve_add, name="order_pack_reserve_add"),
    path("orders/<int:pk>/pack/update/", views.order_pack_reserve_update, name="order_pack_reserve_update"),
    path("orders/<int:pk>/pack/remove/", views.order_pack_reserve_remove, name="order_pack_reserve_remove"),
    path("orders/<int:pk>/pack/assign_pack/", views.order_pack_reserve_assign_pack, name="order_pack_reserve_assign_pack"),
    path("orders/<int:pk>/pack/assign_item/", views.order_pack_assign_item, name="order_pack_assign_item"),
    path("orders/<int:pk>/pack/complete/", views.order_pack_complete, name="order_pack_complete"),
    path("orders/create/barcode_check/", views.order_create_barcode_check, name="order_create_barcode_check"),
    path("orders/create/roll_list/", views.order_create_roll_list, name="order_create_roll_list"),
    path("orders/<int:pk>/excel/", order_excel.order_excel, name="order_excel"),
    path("orders/", views.OrderList.as_view(), name="order_list"),
    path("orders/analytics/", views.OrderAnalytics.as_view(), name="order_analytics"),
    path("orders/delete/<int:pk>/", views.delete_order, name="delete_order"),
    path("orders/bulk-delete/", views.bulk_delete_orders, name="bulk_delete_orders"),
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
        "orders/<int:pk>/packing_list/pdf/",
        views.order_packing_list_pdf,
        name="order_packing_list_pdf",
    ),
    path(
        "packs/<int:pack_pk>/pdf/",
        views.pack_pdf,
        name="pack_pdf",
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
    path(
        "webclient_autocomplete/", views.webclient_autocomplete, name="webclient_autocomplete"
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
