"""
Performance monitoring middleware
"""
import time
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation
from django.conf import settings


class ForceEnglishDefaultMiddleware(MiddlewareMixin):
    """Activate English for every request UNLESS the user explicitly
    picked another language via the language switcher (django_language
    cookie set, or LANGUAGE_SESSION_KEY in session).

    Django's LocaleMiddleware auto-detects the language from the
    Accept-Language header, which made every Turkish browser see the
    Turkish UI even on first visit. We want English to be the
    universal default — the switcher still works for users who want
    Turkish.
    """

    def process_request(self, request):
        # If the user has explicitly chosen a language, respect that.
        explicit = (
            request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
            if hasattr(settings, "LANGUAGE_COOKIE_NAME") else None
        )
        if not explicit:
            session = getattr(request, "session", None)
            if session is not None:
                explicit = session.get(translation.LANGUAGE_SESSION_KEY, None) \
                    if hasattr(translation, "LANGUAGE_SESSION_KEY") else None
        if explicit:
            return None
        # No explicit preference → force English.
        translation.activate("en")
        request.LANGUAGE_CODE = "en"
        return None


# class PerformanceLoggingMiddleware(MiddlewareMixin):
#     """
#     Middleware to log template rendering time and total request time
#     """
    
#     def process_request(self, request):
#         """Mark the start time of the request"""
#         request._request_start_time = time.time()
    
#     def process_template_response(self, request, response):
#         """Log template rendering time"""
#         # Don't manually render - Django will do it automatically
#         # Just mark that we're in template phase
#         if hasattr(request, '_request_start_time'):
#             request._template_phase_start = time.time()
#         return response
    
#     def process_response(self, request, response):
#         """Log total request time"""
#         if hasattr(request, '_request_start_time'):
#             total_time = time.time() - request._request_start_time
            
#             # Only log slow requests (more than 500ms)
#             if total_time > 0.5:
#                 print(f"\n⚠️  SLOW REQUEST DETECTED!")
#                 print(f"   🌐 Path: {request.path}")
#                 print(f"   ⏱️  Total Time: {total_time:.4f}s")
        
#         return response


class ReadOnlyRoleMiddleware(MiddlewareMixin):
    """Holds a sales rep to reading stock and sales.

    Runs before URL resolution, so a view added tomorrow is closed to
    her unless someone widens `erp.roles.READ_PREFIXES` on purpose. See
    erp/roles.py for the two gates and why they are shaped that way.

    Everyone who is not a sales rep passes straight through — this is
    not a general permission system, it is one role.
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    def process_request(self, request):
        from erp.roles import is_sales_rep, may_read, may_write

        if not is_sales_rep(getattr(request, "user", None)):
            return None

        if request.method not in self.SAFE_METHODS:
            # One exception to "no writes": raising a new order. It is
            # born pending and reserves nothing; completing it is a
            # separate transition she cannot make (see
            # operating.views_warehouse.apply_order_status_change).
            if not may_write(request.path):
                return self._deny(
                    request,
                    "Your account can create orders, but not change other records.",
                )
            return None

        if not may_read(request.path):
            return self._deny(
                request,
                "Your account can view stock and sales only.",
            )
        return None

    @staticmethod
    def _deny(request, message):
        from django.http import HttpResponseForbidden, JsonResponse

        # Half this app talks to itself over fetch(); a JSON caller that
        # gets an HTML error page reports it as a parse failure, which
        # tells the reader nothing about why the click did nothing.
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )
        if wants_json:
            return JsonResponse({"success": False, "error": message}, status=403)
        return HttpResponseForbidden(
            f"<h1>Read-only account</h1><p>{message}</p>"
            "<p><a href='/'>Back</a></p>"
        )


def public(view):
    """Marks a view as open to anonymous visitors — see LoginWallMiddleware.

    Same attribute Django 5.1's ``login_not_required`` sets, so the two can
    be swapped once the project is on it.
    """
    view.login_required = False
    return view


class LoginWallMiddleware(MiddlewareMixin):
    """Every page is behind the sign-in unless it says otherwise.

    The guard used to be per view, and a view that forgot it served its
    page to whoever asked — or crashed, since the templates assume a
    signed-in member. Runs after URL resolution (process_view) so it
    can read the view itself, and sends the visitor to the sign-in with
    ``next`` set, the way ``login_required`` does.

    What stays open, because it has to be:

    * the sign-in and its neighbours (sign-up, sign-out, password reset,
      the Google sign-in dance), and the admin, which has its own door;
    * the storefront's API — every path with an ``api/`` segment, and
      every ``csrf_exempt`` view, which is what an endpoint meant for a
      browser on another site looks like here. Those keep whatever guard
      they have today; this wall is for the ERP's own pages;
    * a view marked ``@public`` (erp.middleware.public).
    """

    PUBLIC_PREFIXES = (
        "/authentication/signin",
        "/authentication/signup/",
        "/authentication/signout/",
        "/authentication/home/",
        "/authentication/index",
        "/authentication/google-oauth/",
        "/accounts/",        # django.contrib.auth.urls: password reset et al.
        "/admin/",
        "/i18n/",
        "/static/",
        "/media/",
        "/__debug__/",
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        if self._is_public(request.path, view_func):
            return None
        return self._to_sign_in(request)

    @classmethod
    def _is_public(cls, path, view_func):
        if path.startswith(cls.PUBLIC_PREFIXES):
            return True
        if "/api/" in path:
            return True
        if getattr(view_func, "csrf_exempt", False):
            return True
        return getattr(view_func, "login_required", True) is False

    @staticmethod
    def _to_sign_in(request):
        from django.contrib.auth.views import redirect_to_login
        from django.http import HttpResponse

        redirect = redirect_to_login(request.get_full_path())
        # An htmx fragment request cannot follow a redirect into the
        # sign-in page — it would swap the sign-in form into a corner of
        # a page that no longer belongs to anyone. HX-Redirect moves the
        # whole window instead.
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=200)
            response["HX-Redirect"] = redirect["Location"]
            return response
        return redirect
