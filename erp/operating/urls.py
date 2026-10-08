from django.urls import path, include
from . import views
from . import views_warehouse
from . import views_samples
from . import order_excel
from . import picking_list
from . import warehouse_label
from . import warehouse_excel
from accounting import views_invoice
from accounting.book_scope import book_guarded, book_guarded_for_sales_rep, book_scoped
from crm.directories import customer_guarded
from .models import Order, Pack, Warehouse
from .split_orders import split_order_guarded
from django.views.generic import TemplateView, RedirectView


app_name = "operating"


in_reach = views_warehouse.warehouse_in_reach


def of_a_customer_in_reach(view):
    """An order's printouts and its customer card name the customer, so
    they open only for someone who may see that customer (crm.Directory).
    Beside the book guards rather than instead of them: this one lets a
    shop print the factory's half of an order they share a customer for.

    Every action on an order named by id carries it too — packing,
    completing, deleting. None of those prints a name, but an order
    whose customer its reader may not see is another business's order,
    and not theirs to pack or delete by typing its number.
    """
    return customer_guarded(view, Order, "contact", "company",
                            book="current_account__book")

urlpatterns = [
    # Purchasing, moved in from the old `procurement` app. Mounted here so its
    # names resolve as `operating:purchase_request_list`, and so the sales-rep
    # path gate keeps seeing it as a prefix it does not allow.
    path("procurement/", include("operating.urls_procurement")),

    path("", views.index.as_view(), name="index"),
    # Warehouse. Every page under one warehouse is `in_reach`: open to
    # whoever works with that warehouse's stock, 404 for anyone else
    # (views_warehouse.warehouse_in_reach). The three pages about the
    # warehouse itself keep the stricter warehouse_guarded.
    path("warehouses/", views_warehouse.WarehouseList.as_view(), name="warehouse_list"),
    # Global activity feed ("Son Hareketler") — all warehouses. Must sit
    # above warehouses/<int:pk>/ patterns (won't collide: int ≠ "movements").
    path("warehouses/movements/", views_warehouse.WarehouseMovementsAll.as_view(), name="warehouse_movements_all"),
    path("warehouses/create/", views_warehouse.WarehouseCreate.as_view(), name="create_warehouse"),
    path("warehouses/create/partial/", views_warehouse.WarehouseCreatePartial.as_view(), name="create_warehouse_partial"),
    path("warehouses/account-create/", views_warehouse.warehouse_account_create, name="warehouse_account_create"),
    path("warehouses/barcode-available/", views_warehouse.warehouse_barcode_available, name="warehouse_barcode_available"),
    path("warehouses/<int:pk>/", views_warehouse.warehouse_guarded(views_warehouse.WarehouseDetail.as_view()), name="warehouse_detail"),
    path("warehouses/<int:pk>/excel/", in_reach(warehouse_excel.warehouse_excel), name="warehouse_excel"),
    path("warehouses/<int:pk>/group-variants/", in_reach(views_warehouse.warehouse_group_variants), name="warehouse_group_variants"),
    path("warehouses/<int:pk>/catalog-search/", in_reach(views_warehouse.catalog_base_search), name="catalog_base_search"),
    path("warehouses/<int:pk>/catalog-variants/<int:product_id>/", in_reach(views_warehouse.catalog_product_variants), name="catalog_product_variants"),
    path("warehouses/<int:pk>/customer-currency/", in_reach(views_warehouse.warehouse_customer_currency), name="warehouse_customer_currency"),
    path("customer-currency/", views_warehouse.customer_currency, name="customer_currency"),
    path("warehouses/<int:pk>/catalog-variant-match/<int:product_id>/", in_reach(views_warehouse.catalog_variant_match), name="catalog_variant_match"),
    path("warehouses/<int:pk>/supplier-codes/", in_reach(views_warehouse.supplier_codes), name="supplier_codes"),
    path("warehouses/<int:pk>/barcode-lookup/", in_reach(views_warehouse.warehouse_barcode_lookup), name="warehouse_barcode_lookup"),
    path("warehouses/<int:pk>/product-search/", in_reach(views_warehouse.warehouse_product_search), name="warehouse_product_search"),
    path("warehouses/<int:pk>/rolls/<int:roll_pk>/move-here/", in_reach(views_warehouse.warehouse_roll_move_here), name="warehouse_roll_move_here"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/", in_reach(views_warehouse.warehouse_product_rolls), name="warehouse_product_rolls"),
    path("warehouses/<int:warehouse_pk>/rolls/<int:roll_pk>/photo/", in_reach(views_warehouse.warehouse_roll_photo), name="warehouse_roll_photo"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/label/", in_reach(warehouse_label.warehouse_product_label), name="warehouse_product_label"),
    # Not in_reach: what a roll's QR opens, for anyone holding the label.
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/code/", warehouse_label.warehouse_product_code, name="warehouse_product_code"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/info/", warehouse_label.warehouse_product_info, name="warehouse_product_info"),
    # Convenience: a mistyped/stale "label/info" path still lands on the info screen.
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/label/info/", RedirectView.as_view(pattern_name="operating:warehouse_product_info", permanent=False)),
    path("warehouses/<int:pk>/edit/", views_warehouse.warehouse_guarded(views_warehouse.WarehouseEdit.as_view()), name="warehouse_edit"),
    path("warehouses/<int:pk>/import/", in_reach(views_warehouse.WarehouseProductImport.as_view()), name="warehouse_product_import"),
    path("warehouses/<int:pk>/delete/", views_warehouse.warehouse_guarded(views_warehouse.WarehouseDelete.as_view()), name="warehouse_delete"),
    path("warehouses/<int:pk>/scan/", in_reach(views_warehouse.WarehouseRollScan.as_view()), name="warehouse_roll_scan"),
    path("warehouses/<int:pk>/manual-add/", in_reach(views_warehouse.WarehouseManualAdd.as_view()), name="warehouse_manual_add"),
    path("warehouses/<int:pk>/purchase/<int:invoice_id>/edit/", in_reach(views_warehouse.WarehousePurchaseEdit.as_view()), name="warehouse_purchase_edit"),
    path("warehouses/<int:pk>/next-sku/", in_reach(views_warehouse.warehouse_next_sku), name="warehouse_next_sku"),
    path("warehouses/<int:pk>/next-barcode/", in_reach(views_warehouse.warehouse_next_barcode), name="warehouse_next_barcode"),
    path("warehouses/<int:pk>/merge-duplicates/", in_reach(views_warehouse.WarehouseMergeDuplicates.as_view()), name="warehouse_merge_duplicates"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/", in_reach(views_warehouse.WarehouseProductDetail.as_view()), name="warehouse_product_detail"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/edit/", in_reach(views_warehouse.WarehouseProductEdit.as_view()), name="warehouse_product_edit"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/delete/", in_reach(views_warehouse.WarehouseProductDelete.as_view()), name="warehouse_product_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/stock-out/", in_reach(views_warehouse.WarehouseStockOut.as_view()), name="warehouse_stock_out"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/<int:roll_pk>/delete/", in_reach(views_warehouse.WarehouseRollDelete.as_view()), name="warehouse_roll_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/bulk-delete/", in_reach(views_warehouse.WarehouseRollBulkDelete.as_view()), name="warehouse_roll_bulk_delete"),
    path("warehouses/<int:warehouse_pk>/products/<int:product_pk>/rolls/<int:roll_pk>/edit/", in_reach(views_warehouse.WarehouseRollEdit.as_view()), name="warehouse_roll_edit"),
    path("warehouses/<int:warehouse_pk>/movements/", in_reach(views_warehouse.WarehouseMovements.as_view()), name="warehouse_movements"),
    # Sample packages, made from a client's CRM page.
    path("samples/rolls/", views_samples.sample_roll_search, name="sample_roll_search"),
    path("samples/packages/create/", views_samples.sample_package_create, name="sample_package_create"),
    path("samples/packages/<int:pk>/shipping/", views_samples.sample_package_shipping, name="sample_package_shipping"),
    path("orders/create/", views.create_web_order, name="create_web_order"),
    # Creating an order is a PAGE, like editing one. Book-scoped, because
    # every line that names no book of its own is filed under the book the
    # form was opened in — and a URL naming no book falls back to the
    # member's default, which is not necessarily the list they came from.
    path("books/<int:book_id>/orders/create/",
         book_scoped(views.OrderCreate.as_view()), name="create_order_page"),
    # The form POSTs here, and carries its book in a hidden field, so this
    # one needs no book of its own. Still serves the sidebar partial to an
    # HX-Request, for anything still opening the drawer.
    path("orders/create", views.OrderCreate.as_view(), name="create_order"),
    path("orders/edit/<int:pk>/", book_guarded(views.OrderEdit.as_view(), Order, "current_account.book"), name="edit_order"),
    path("orders/web/<int:pk>/status/", views.WebOrderStatusEdit.as_view(), name="web_order_status"),
    # book_guarded, plus the split-order exception: a half in another book
    # leads to the half the viewer may open, which shows the whole order.
    path("orders/<int:pk>/", split_order_guarded(views.OrderDetail.as_view()), name="order_detail"),
    path("orders/<int:pk>/customer/", of_a_customer_in_reach(views.order_customer_card_view), name="order_customer_card"),
    path("orders/<int:pk>/print/", of_a_customer_in_reach(views.OrderPrint.as_view()), name="order_print"),
    # The order's invoice — a printout of the order, nothing stored.
    path("orders/<int:pk>/invoice/", book_guarded(views_invoice.OrderInvoice.as_view(), Order, "current_account.book"), name="order_invoice"),
    path("orders/<int:pk>/invoice/excel/", book_guarded(views_invoice.order_invoice_excel, Order, "current_account.book"), name="order_invoice_excel"),
    # Not book_guarded, and not scoped to one order: the sheet is a
    # customer's orders, which may sit in two books. The view checks the
    # viewer against each order's book itself.
    path("orders/print/combined/", views.OrderPrintCombined.as_view(), name="order_print_combined"),
    path("orders/print/combined/excel/", order_excel.combined_order_excel, name="order_excel_combined"),
    path("orders/<int:pk>/changes/", of_a_customer_in_reach(views.order_changes), name="order_changes"),
    # The rolls to pull for an order, for the warehouse floor: no prices,
    # no customer name. Guarded the way the pack screen is — it is the
    # same people's sheet.
    path("orders/<int:pk>/picking_list/", of_a_customer_in_reach(book_guarded_for_sales_rep(picking_list.order_picking_list, Order, "current_account.book")), name="order_picking_list"),
    # Packing-scan flow (reserve warehouse rolls before shipping).
    #
    # The sales-rep role reaches these (erp.roles), and these routes name
    # an order by id and nothing else — so for her, and only for her,
    # the order's book is checked against her assignments the way
    # order_detail's is. See book_guarded_for_sales_rep for why it is not
    # simply book_guarded for everybody.
    path("orders/<int:pk>/pack/", of_a_customer_in_reach(book_guarded_for_sales_rep(views.order_pack_scan, Order, "current_account.book")), name="order_pack_scan"),
    path("orders/<int:pk>/pack/add/", of_a_customer_in_reach(book_guarded_for_sales_rep(views.order_pack_reserve_add, Order, "current_account.book")), name="order_pack_reserve_add"),
    path("orders/<int:pk>/pack/update/", of_a_customer_in_reach(views.order_pack_reserve_update), name="order_pack_reserve_update"),
    path("orders/<int:pk>/pack/remove/", of_a_customer_in_reach(views.order_pack_reserve_remove), name="order_pack_reserve_remove"),
    path("orders/<int:pk>/pack/assign_pack/", of_a_customer_in_reach(book_guarded_for_sales_rep(views.order_pack_reserve_assign_pack, Order, "current_account.book")), name="order_pack_reserve_assign_pack"),
    path("orders/<int:pk>/pack/assign_item/", of_a_customer_in_reach(book_guarded_for_sales_rep(views.order_pack_assign_item, Order, "current_account.book")), name="order_pack_assign_item"),
    path("orders/<int:pk>/pack/complete/", of_a_customer_in_reach(views.order_pack_complete), name="order_pack_complete"),
    path("orders/create/barcode_check/", views.order_create_barcode_check, name="order_create_barcode_check"),
    path("orders/create/barcode_resolve/", views.order_create_barcode_resolve, name="order_create_barcode_resolve"),
    path("orders/create/roll_list/", views.order_create_roll_list, name="order_create_roll_list"),
    path("orders/<int:pk>/excel/", of_a_customer_in_reach(order_excel.order_excel), name="order_excel"),
    # An order's money lands in one book (through its current account), so the list
    # names the book the same way the ledger's collections do. The old
    # unscoped address stays as a redirect to the viewer's working book:
    # it is linked from the nav, the mobile drawer, the top bar and a
    # current account's detail page, and those links carry no book of their own.
    path("books/<int:book_id>/orders/", book_scoped(views.OrderList.as_view()),
         name="order_list_scoped"),
    path("orders/", views.OrderListRedirect.as_view(), name="order_list"),
    path("orders/analytics/", views.OrderAnalytics.as_view(), name="order_analytics"),
    path("orders/delete/<int:pk>/", of_a_customer_in_reach(views.delete_order), name="delete_order"),
    path("orders/bulk-delete/", views.bulk_delete_orders, name="bulk_delete_orders"),
    path(
        "orders/<int:pk>/production/",
        of_a_customer_in_reach(views.OrderProduction.as_view()),
        name="order_production",
    ),
    path(
        "orders/<int:pk>/packing_list/",
        # Guarded with the pack flow above, and for the same reason: the
        # packing screen POSTs its sack add/delete here.
        of_a_customer_in_reach(book_guarded_for_sales_rep(
            views.OrderPackingList.as_view(), Order, "current_account.book")),
        name="order_packing_list",
    ),
    # path("create_product/",views.CreateProduct.as_view(),name="create_product"),
    # path("product_list/",views.Product.as_view(),name="product_list"),
    path(
        "orders/<int:pk>/packing_list/export_excel/",
        of_a_customer_in_reach(views.export_packing_list_excel),
        name="export_packing_list_excel",
    ),
    path(
        "orders/<int:pk>/packing_list/pdf/",
        of_a_customer_in_reach(views.order_packing_list_pdf),
        name="order_packing_list_pdf",
    ),
    path(
        "packs/<int:pack_pk>/pdf/",
        customer_guarded(views.pack_pdf, Pack, "order__contact", "order__company",
                         kwarg="pack_pk", book="order__current_account__book"),
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
