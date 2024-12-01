from django.urls import path
from . import views

app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("create_product/",views.CreateProduct.as_view(),name="create_product"),
    path("product_list/",views.Product.as_view(),name="product_list"),
]
htmx_urlpatterns = []

urlpatterns += htmx_urlpatterns