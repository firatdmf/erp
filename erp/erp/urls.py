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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.http import HttpResponse
from . import views
from django.contrib.auth import views as auth_views


# from django.contrib.staticfiles.views import serve

urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("dashboard/", views.Dashboard.as_view(), name="dashboard"),
    path("settings/",views.user_settings.as_view(),name="user_settings"),
    path("admin/", admin.site.urls),
    path('authentication/',include('authentication.urls')),
    path('accounting/',include('accounting.urls')),
    path("todo/", include("todo.urls")),
    path("crm/", include("crm.urls")),
    path("marketing/",include("marketing.urls")),
    path("operating/",include("operating.urls")),
    path("reports/",views.reports.as_view(),name="reports"),
    path("reports/task_report",views.task_report.as_view(),name="task_report"),
    path('accounts/', include('django.contrib.auth.urls')),
    path("testpage/",views.test_page.as_view(),name="test_page"),
    path("testpage2/",views.test_page2.as_view(),name="test_page2")
    # path('static/<path:path>',serve),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
