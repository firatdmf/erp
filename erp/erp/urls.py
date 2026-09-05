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
from django.urls import path, include, re_path
from django.views.generic import RedirectView
# The mail views live in marketing now; imported directly so the Gmail OAuth
# callback keeps its registered /email/oauth2callback/ path.
from marketing import views_email as email_views
from django.http import HttpResponse
from . import views
from django.contrib.auth import views as auth_views


# from django.contrib.staticfiles.views import serve

urlpatterns = [
    path("", views.index.as_view(), name="index"),
    path("dashboard/", views.Dashboard.as_view(), name="dashboard"),
    path("settings/",views.user_settings.as_view(),name="user_settings"),
    # Built-in i18n endpoint: POST { language: 'tr' } sets cookie + redirects
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path('authentication/',include('authentication.urls')),
    # Both are mounted at accounting/. The ledger goes first so its
    # books/<id>/accounts/ collections are matched here rather than being
    # shadowed by accounting.urls' own books/<pk>/ routes.
    path('accounting/', include('accounting.urls_accounts')),
    path('accounting/',include('accounting.urls')),
    path("todo/", include("todo.urls")),
    path("crm/", include("crm.urls")),
    path("marketing/",include("marketing.urls")),
    path("operating/",include("operating.urls")),
    # The mail system moved into `marketing` and now lives at
    # /marketing/email/... . Two things keep the old /email/ prefix working:
    #
    #  * the OAuth callback path is registered with Google Cloud Console and
    #    baked into GMAIL_REDIRECT_URI, so it must resolve unchanged or every
    #    Gmail reconnect fails with redirect_uri_mismatch. It is routed
    #    straight at the view, no namespace involved.
    #  * everything else 302s across, so bookmarked inboxes still land.
    path("email/oauth2callback/", email_views.oauth2callback, name="gmail_oauth2callback"),
    re_path(r"^email/(?P<rest>.*)$", RedirectView.as_view(url="/marketing/email/%(rest)s", permanent=False)),
    path("notifications/", include("notifications.urls")),
    path("team/", include("team.urls")),
    path("notes/", include("notes.urls")),
    path("procurement/", include("procurement.urls")),
    path('accounts/', include('django.contrib.auth.urls')),
    path("testpage/",views.test_page.as_view(),name="test_page"),
    path("testpage2/",views.test_page2.as_view(),name="test_page2"),
    path("search/", views.GlobalSearch.as_view(), name="global_search"),
    # path('static/<path:path>',serve),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Toolbar is opt-in (DEBUG_TOOLBAR env flag) — see settings.py.
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
