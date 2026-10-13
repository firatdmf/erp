"""The newsletter's subscribers, on a page.

People sign up on the website — the pop-up, the footer form, the blog's
subscribe box — and until now the list could only be read in the admin.
"""
from django.db.models import Q
from django.views import generic

from .models import NewsletterSubscription


class SubscriberList(generic.ListView):
    model = NewsletterSubscription
    template_name = "marketing/subscriber_list.html"
    context_object_name = "subscribers"
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related("discount_code")
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(email__icontains=search) | Q(phone__icontains=search))
        status = self.request.GET.get("status", "")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "unsubscribed":
            queryset = queryset.filter(is_active=False)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        everyone = NewsletterSubscription.objects.all()
        active = everyone.filter(is_active=True)
        context.update(
            search=self.request.GET.get("search", "").strip(),
            status=self.request.GET.get("status", ""),
            total=everyone.count(),
            active_total=active.count(),
            with_email=active.filter(email__isnull=False).count(),
            with_phone=active.filter(phone__isnull=False).count(),
        )
        return context
