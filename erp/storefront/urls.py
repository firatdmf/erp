from django.urls import path
from . import views, api

app_name = "storefront"

urlpatterns = [
    # ERP içi yönetim sayfaları
    path("", views.dashboard, name="dashboard"),
    path("home/", views.edit_home, name="edit_home"),
    path("home/jump/<str:kind>/", views.jump_home_section, name="jump_home_section"),
    path("home/section/<int:pk>/", views.edit_home_section, name="edit_home_section"),
    path("home/section/<int:pk>/delete/", views.delete_home_section, name="delete_home_section"),
    path("home/section/new/", views.create_home_section, name="create_home_section"),
    path("menu/", views.edit_menu, name="edit_menu"),
    path("menu/item/<int:pk>/", views.edit_menu_item, name="edit_menu_item"),
    path("menu/item/<int:pk>/delete/", views.delete_menu_item, name="delete_menu_item"),
    path("menu/item/new/", views.create_menu_item, name="create_menu_item"),

    # Belino Next.js'in çekeceği API'ler
    path("api/<slug:key>/nav/", api.api_nav, name="api_nav"),
    path("api/<slug:key>/home/", api.api_home, name="api_home"),

    # ERP içi admin API (drag-drop, hızlı toggle, inline edit)
    path("api/reorder/<str:model>/", api.api_reorder, name="api_reorder"),
    path("api/toggle/<str:model>/<int:pk>/", api.api_toggle_active, name="api_toggle"),
    path("api/text/<str:model>/<int:pk>/", api.api_save_text, name="api_save_text"),
    path("api/image/<str:model>/<int:pk>/", api.api_save_image, name="api_save_image"),
]
