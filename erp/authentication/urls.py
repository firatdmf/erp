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
    
    # WebClient API endpoints
    path('api/create_web_client/', api_views.create_web_client, name='create_web_client'),
    path('api/login_web_client/', api_views.login_web_client, name='login_web_client'),
    path('api/check_web_client_email/', api_views.check_web_client_email, name='check_web_client_email'),
    path('api/create_google_client/', api_views.create_google_client, name='create_google_client'),
    path('api/get_web_client_profile/<int:user_id>/', api_views.get_web_client_profile, name='get_web_client_profile'),
    path('api/update_web_client_profile/<int:user_id>/', api_views.update_web_client_profile, name='update_web_client_profile'),
    path('api/change_password/<int:user_id>/', api_views.change_password, name='change_password'),
    path('api/add_client_address/<int:user_id>/', api_views.add_client_address, name='add_client_address'),
    path('api/set_default_address/<int:user_id>/<int:address_id>/', api_views.set_default_address, name='set_default_address'),
    path('api/delete_client_address/<int:user_id>/<int:address_id>/', api_views.delete_client_address, name='delete_client_address'),
    
    # Favorite API endpoints
    path('api/get_user_favorites/<int:user_id>/', api_views.get_user_favorites, name='get_user_favorites'),
    path('api/toggle_favorite/<int:user_id>/', api_views.toggle_favorite, name='toggle_favorite'),
    path('api/check_favorite/<int:user_id>/<str:product_sku>/', api_views.check_favorite, name='check_favorite'),
]
