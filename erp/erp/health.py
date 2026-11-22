"""The page Railway's health check asks before a new release takes traffic.

Railway keeps the running release serving until this answers 200, so a
deploy no longer shows a 502 while the new container runs its start
command (collectstatic, migrate) and gunicorn comes up. The check comes
from healthcheck.railway.app, which ALLOWED_HOSTS lets in.
"""
from django.db import connection
from django.http import HttpResponse
from django.views.decorators.cache import never_cache

from .middleware import public


@public
@never_cache
def healthz(request):
    """200 when the app is up and reaches its database, else 503."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return HttpResponse("database unreachable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
