"""
Performance monitoring middleware
"""
import time
from django.utils.deprecation import MiddlewareMixin


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
