from django.contrib import admin
from django.urls import path, include
from . import views
from . import api_views

app_name ="authentication"
urlpatterns = [
    path('home/', views.home, name="home"),
    path('signup/',views.signup,name = 'signup'),
    path('signin/',views.signin,name = 'signin'),
    path('signout/',views.signout,name = 'signout'),
    path('settings/update_profile/', views.update_profile, name='update_profile'),
    path('settings/change_password/', views.change_password_settings, name='change_password_settings'),
    
    # WebClient API endpoints
    path('api/create_web_client/', api_views.create_web_client, name='create_web_client'),
    path('api/login_web_client/', api_views.login_web_client, name='login_web_client'),
    path('api/check_web_client_email/', api_views.check_web_client_email, name='check_web_client_email'),
    path('api/create_google_client/', api_views.create_google_client, name='create_google_client'),
    path('api/get_web_client_profile/<int:user_id>/', api_views.get_web_client_profile, name='get_web_client_profile'),
    path('api/update_web_client_profile/<int:user_id>/', api_views.update_web_client_profile, name='update_web_client_profile'),
    path('api/change_password/<int:user_id>/', api_views.change_password, name='change_password'),
    path('api/reset_password/', api_views.reset_password, name='reset_password'),
    path('api/verify_email/', api_views.verify_email, name='verify_email'),
    path('api/get_exchange_rates/', api_views.get_exchange_rates, name='get_exchange_rates'),
    path('api/add_client_address/<int:user_id>/', api_views.add_client_address, name='add_client_address'),
    path('api/get_client_addresses/<int:user_id>/', api_views.get_client_addresses, name='get_client_addresses'),
    path('api/set_default_address/<int:user_id>/<int:address_id>/', api_views.set_default_address, name='set_default_address'),
    path('api/delete_client_address/<int:user_id>/<int:address_id>/', api_views.delete_client_address, name='delete_client_address'),
    
    # Favorite API endpoints
    path('api/get_user_favorites/<int:user_id>/', api_views.get_user_favorites, name='get_user_favorites'),
    path('api/toggle_favorite/<int:user_id>/', api_views.toggle_favorite, name='toggle_favorite'),
    path('api/check_favorite/<int:user_id>/<str:product_sku>/', api_views.check_favorite, name='check_favorite'),
    
    # Cart API endpoints
    path('api/get_cart/<int:user_id>/', api_views.get_cart, name='get_cart'),
    path('api/add_to_cart/<int:user_id>/', api_views.add_to_cart, name='add_to_cart'),
    path('api/update_cart_item/<int:user_id>/<int:item_id>/', api_views.update_cart_item, name='update_cart_item'),
    path('api/remove_from_cart/<int:user_id>/<int:item_id>/', api_views.remove_from_cart, name='remove_from_cart'),
    path('api/clear_cart/<int:user_id>/', api_views.clear_cart, name='clear_cart'),
    
    # Order API endpoints
    path('api/get_user_orders/<int:user_id>/', api_views.get_user_orders, name='get_user_orders'),
    path('api/get_order_detail/<int:user_id>/<int:order_id>/', api_views.get_order_detail, name='get_order_detail'),
    
    # Product Review API endpoints
    path('api/can_review_product/<int:user_id>/<str:product_sku>/', api_views.can_review_product, name='can_review_product'),
    path('api/add_product_review/<int:user_id>/', api_views.add_product_review, name='add_product_review'),
    path('api/get_product_reviews/<str:product_sku>/', api_views.get_product_reviews, name='get_product_reviews'),
    path('api/get_user_reviews/<int:user_id>/', api_views.get_user_reviews, name='get_user_reviews'),
    path('api/delete_review/<int:user_id>/<int:review_id>/', api_views.delete_review, name='delete_review'),
]
