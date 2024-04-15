"""
URL configuration for erp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from . import views
from django.contrib.auth import views as auth_views


# from django.contrib.staticfiles.views import serve

urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("admin/", admin.site.urls),
    path('authentication/',include('authentication.urls')),
    path("todo/", include("todo.urls")),
    path("crm/", include("crm.urls")),
    path("reports/",views.reports.as_view(),name="reports"),
    path("reports/task_report",views.task_report.as_view(),name="task_report"),
    path('accounts/', include('django.contrib.auth.urls')),
    # path('static/<path:path>',serve),
]
