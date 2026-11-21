"""Sell-down goals: the list, one goal's designs, and the goal form.

Anyone may read a goal in a book they work in, and reads it over those
books only (operating.sell_down.progress). A sales rep reads it without
money: shares, quantities and designs, never a value built from cost.
Creating and changing a goal is an admin's.
"""
from decimal import Decimal

from django import forms
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View

from accounting.models import Book
from accounting.services_accounts import member_books
from erp.roles import is_sales_rep
from marketing.models import Product, ProductCategory

from . import sell_down
from .models import SellDownGoal
from .views_warehouse import _is_admin


def _member(request):
    return getattr(request.user, "member", None)


def _currency_symbol(progress):
    """The symbol the goal's values are in: its books' base currency
    (the form keeps one goal to one currency)."""
    cur = progress.books[0].base_currency if progress.books else None
    return (getattr(cur, "symbol", "") or getattr(cur, "code", "")) if cur else ""


class SellDownList(View):
    template_name = "operating/sell_down_list.html"

    def get(self, request):
        member = _member(request)
        book_ids = sell_down.readable_book_ids(member)
        goals = (SellDownGoal.objects
                 .filter(book_parts__book_id__in=book_ids).distinct()
                 .order_by("-is_active", "deadline", "id"))
        rows = [p for p in (sell_down.progress(g, book_ids) for g in goals) if p]
        return render(request, self.template_name, {
            "rows": [(p, _currency_symbol(p)) for p in rows],
            "show_money": not is_sales_rep(request.user),
            "may_edit": _is_admin(request.user),
        })


class SellDownDetail(View):
    template_name = "operating/sell_down_detail.html"

    def get(self, request, pk):
        goal = get_object_or_404(SellDownGoal, pk=pk)
        book_ids = sell_down.readable_book_ids(_member(request))
        p = sell_down.progress(goal, book_ids)
        if p is None:
            raise Http404
        # Each design's row opens to its variants.
        by_design = sell_down.variants_by_design(goal, [b.pk for b in p.books])
        for d in p.designs:
            d.variants = by_design.get(d.product_id, [])
        focus_ids = {d.product_id for d in p.focus}
        return render(request, self.template_name, {
            "p": p,
            "goal": goal,
            "currency": _currency_symbol(p),
            "focus_ids": focus_ids,
            "show_money": not is_sales_rep(request.user),
            "may_edit": _is_admin(request.user),
        })


class SellDownGoalForm(forms.ModelForm):
    books = forms.ModelMultipleChoiceField(
        queryset=Book.objects.none(), widget=forms.CheckboxSelectMultiple,
        label=gettext_lazy("Books"),
        help_text=gettext_lazy("Its stock in these books is added together. "
                      "Each person sees the books they work in."))
    sell_percent = forms.DecimalField(
        min_value=Decimal("0"), max_value=Decimal("100"), decimal_places=2,
        label=gettext_lazy("Sell (%)"),
        help_text=gettext_lazy("How much of today's value to sell by the deadline."))
    tag = forms.CharField(
        required=False, label=gettext_lazy("Product tag"),
        widget=forms.TextInput(attrs={"list": "sellDownTags"}),
        help_text=gettext_lazy("Only products carrying this tag. Leave blank for any."))

    class Meta:
        model = SellDownGoal
        fields = ["title", "category", "tag", "deadline", "focus_percent", "is_active"]
        labels = {
            "title": gettext_lazy("Name"),
            "category": gettext_lazy("Product group"),
            "deadline": gettext_lazy("Deadline"),
            "focus_percent": gettext_lazy("Focus on designs holding (%)"),
            "is_active": gettext_lazy("Show on the dashboard"),
        }
        help_texts = {
            "category": gettext_lazy("Only products in this group. Leave blank for every group."),
            "focus_percent": gettext_lazy("The fewest designs, biggest first, that hold this share "
                                 "of what is left are the ones to push."),
        }
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["books"].queryset = member_books(member)
        self.fields["category"].queryset = ProductCategory.objects.order_by("name")
        self.fields["category"].required = False
        self.fields["focus_percent"].max_value = Decimal("100")
        if self.instance.pk:
            self.fields["books"].initial = [p.book_id for p in self.instance.book_parts.all()]
            self.fields["sell_percent"].initial = 100 - self.instance.target_left_percent
        else:
            self.fields["sell_percent"].initial = Decimal("80")

    def clean_tag(self):
        return (self.cleaned_data.get("tag") or "").strip()

    def clean_focus_percent(self):
        value = self.cleaned_data["focus_percent"]
        if value > 100:
            raise forms.ValidationError(_("At most 100%."))
        return value

    def clean(self):
        data = super().clean()
        books = data.get("books") or []
        currencies = {b.base_currency_id for b in books}
        if len(currencies) > 1:
            self.add_error("books", _("These books use different currencies, "
                                      "so their stock can't be added up."))
        deadline = data.get("deadline")
        start = self.instance.start_date if self.instance.pk else timezone.localdate()
        if deadline and deadline <= start:
            self.add_error("deadline", _("The deadline has to be after the start (%(day)s).")
                           % {"day": start.isoformat()})
        return data


class SellDownEdit(View):
    template_name = "operating/sell_down_form.html"

    def _goal(self, pk):
        return get_object_or_404(SellDownGoal, pk=pk) if pk else SellDownGoal()

    def _render(self, request, form, goal):
        tags = sorted({t for ts in Product.objects.exclude(tags__isnull=True)
                      .values_list("tags", flat=True) for t in (ts or []) if t})
        return render(request, self.template_name, {"form": form, "goal": goal, "tags": tags})

    def get(self, request, pk=None):
        if not _is_admin(request.user):
            raise PermissionDenied
        goal = self._goal(pk)
        return self._render(request, SellDownGoalForm(instance=goal, member=_member(request)), goal)

    def post(self, request, pk=None):
        if not _is_admin(request.user):
            raise PermissionDenied
        goal = self._goal(pk)
        before = (goal.category_id, goal.tag) if goal.pk else None
        form = SellDownGoalForm(request.POST, instance=goal, member=_member(request))
        if not form.is_valid():
            return self._render(request, form, goal)
        with transaction.atomic():
            goal = form.save(commit=False)
            goal.target_left_percent = 100 - form.cleaned_data["sell_percent"]
            if not goal.pk:
                goal.created_by = request.user
            refilter = before is not None and before != (goal.category_id, goal.tag)
            if refilter:
                # Different products, so the old starting values describe
                # something else: the goal starts again from today.
                goal.start_date = timezone.localdate()
            goal.save()
            # Books this person can't see stay as they are: the form only
            # offers, and so only changes, the books they work in.
            offered = set(form.fields["books"].queryset.values_list("pk", flat=True))
            kept = [p.book for p in goal.book_parts.select_related("book")
                    if p.book_id not in offered]
            if refilter:
                goal.book_parts.all().delete()
            sell_down.set_books(goal, kept + list(form.cleaned_data["books"]))
        return redirect("operating:sell_down_detail", pk=goal.pk)
