from django.urls import path
from . import views


app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("orders/create",views.OrderCreate.as_view(),name="create_order"),
    path("orders/<int:pk>/edit",views.OrderEdit.as_view(),name="update_order"),
    path("orders/<int:pk>/", views.OrderDetail.as_view(),name="order_detail"),
    path("orders/", views.OrderList.as_view(), name="order_list"),
    path("orders/delete/<int:pk>/",views.delete_order,name="delete_order"),
    # path("create_product/",views.CreateProduct.as_view(),name="create_product"),
    # path("product_list/",views.Product.as_view(),name="product_list"),

    # below are for api paths
    path("api/order/machine-update/", views.machine_update_status, name="machine_update"),
    path("machine/update-item/<int:item_id>/", views.MachineStatusUpdate.as_view(), name="machine-status-update"),
]
htmx_urlpatterns = [
    path("product_autocomplete/", views.product_autocomplete, name="product_autocomplete"),
]

urlpatterns += htmx_urlpatterns