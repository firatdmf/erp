from django.urls import path
from . import views
app_name = 'crm'
urlpatterns = [
    path("",views.create_client,name="create_client"),
]