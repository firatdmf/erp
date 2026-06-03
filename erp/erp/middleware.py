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
