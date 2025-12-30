from django.urls import path
from . import views
from . import api_stock_update
app_name = "marketing"


urlpatterns = [
    path("",views.Index.as_view(),name="index"),
    path("product_list/",views.ProductList.as_view(),name="product_list"),
    path("product_detail/<int:pk>/",views.ProductDetail.as_view(),name="product_detail"),
    path("product_create/",views.ProductCreate.as_view(),name="product_create"),
    path("product_edit/<int:pk>/",views.ProductEdit.as_view(),name="product_edit"),
    path("product/<int:pk>/delete/",views.ProductDelete.as_view(),name="product_delete"),
    # path("product_file_create/",views.ProductFileCreate.as_view(),name="product_file_create"),
    # below are for api routes
    path("api/get_product_categories",views.get_product_categories,name="get_product_categories"),
    path("api/get_products",views.get_products,name="get_products"),
    path("api/get_product",views.get_product,name="get_product"),
    path("api/update_product_stock/",api_stock_update.update_product_stock,name="update_product_stock"),
    path("api/product_file_delete/",views.ProductFileDelete.as_view(),name="product_file_delete"),
    path("api/update_variant_image_order/",views.update_variant_image_order,name="update_variant_image_order"),
    path("api/async_delete_cloudinary_files/",views.async_delete_cloudinary_files,name="async_delete_cloudinary_files"),
    path("api/temp_upload_file/",views.temp_upload_file,name="temp_upload_file"),
    path("api/cleanup_temp_files/",views.cleanup_temp_files,name="cleanup_temp_files"),
    path("api/instant_upload_file/",views.instant_upload_file,name="instant_upload_file"),
    path("api/instant_delete_file/",views.instant_delete_file,name="instant_delete_file"),
    path("api/instant_delete_variant/",views.instant_delete_variant,name="instant_delete_variant"),
    path("api/get_product_files/",views.get_product_files,name="get_product_files"),
    path("api/get_variant_files/",views.get_variant_files,name="get_variant_files"),
    path("api/link_files_to_variant/",views.link_files_to_variant,name="link_files_to_variant"),
    path("api/save_product_attributes/",views.save_product_attributes,name="save_product_attributes"),
    path("api/get_product_attributes/",views.get_product_attributes,name="get_product_attributes"),
    # Discount code API endpoints
    path("api/validate_discount_code/",views.validate_discount_code,name="validate_discount_code"),
    path("api/increment_discount_usage/",views.increment_discount_usage,name="increment_discount_usage"),
]

