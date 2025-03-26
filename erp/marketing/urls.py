from django.urls import path
from . import views
app_name = "marketing"


urlpatterns = [
    path("",views.Index.as_view(),name="index"),
    path("product_list/",views.ProductList.as_view(),name="product_list"),
    path("product_detail/<int:pk>/",views.ProductDetail.as_view(),name="product_detail"),
    path("product_create/",views.ProductCreate.as_view(),name="product_create"),
    path("product_update/<int:pk>/",views.ProductUpdate.as_view(),name="product_update"),
    path("product_file_create/",views.ProductFileCreate.as_view(),name="product_file_create"),
    path("api/get_products",views.get_products,name="get_products")
]