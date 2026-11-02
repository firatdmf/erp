class EtsySyncMiddleware:
    """Starts the Etsy sync now and then, after a signed-in person's request.

    The install has no clock of its own; its use is the clock, as for the
    product-image housekeeping. The check is one cache lookup, and the sync
    itself runs off the request (etsy_sync.sync_now_and_then).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            from .etsy_sync import sync_now_and_then
            try:
                sync_now_and_then()
            except Exception as exc:      # a sync problem must never cost a page
                print(f"[etsy] sync not started: {exc}")
        return response
