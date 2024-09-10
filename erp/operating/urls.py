from django.urls import path
from . import views

app_name = "operating"
urlpatterns = [
    path("", views.index.as_view(), name="index"),
]
htmx_urlpatterns = []

urlpatterns += htmx_urlpatterns