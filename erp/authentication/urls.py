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
]
