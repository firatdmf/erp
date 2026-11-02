from django.urls import path

from . import views

app_name = "integrations"

urlpatterns = [
    path("etsy/", views.etsy_index, name="etsy_index"),
    # Registered on the Etsy app exactly as written: keep the trailing slash.
    path("etsy/callback/", views.etsy_callback, name="etsy_callback"),
    path("etsy/books/<int:book_pk>/", views.etsy_book, name="etsy_book"),
    path("etsy/books/<int:book_pk>/settings/", views.etsy_settings, name="etsy_settings"),
    path("etsy/books/<int:book_pk>/connect/", views.etsy_connect, name="etsy_connect"),
    path("etsy/books/<int:book_pk>/disconnect/", views.etsy_disconnect, name="etsy_disconnect"),
]
