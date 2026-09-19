"""Screens for what the rate has done to the book.

`services_fx` works out the figures; these two views are where they are
read and, when someone decides to, recorded. Nothing posts on its own:
the panel and the report state the gap, and a deliberate POST records it.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View

from .models_accounts import CurrentAccount
from .services_fx import book_fx_positions, fx_position, post_fx_difference


@method_decorator(login_required, name="dispatch")
class FxReport(View):
    """Every foreign-currency account in the book, and what the rate has
    done to each — the question a per-account panel cannot answer, because
    a gain on one customer and a loss on another are the same question."""

    template_name = "accounts/fx_report.html"

    def get(self, request):
        report = book_fx_positions(request.book)
        return render(request, self.template_name, {
            "report": report,
            "book": request.book,
        })


@method_decorator(login_required, name="dispatch")
class FxPost(View):
    """Record one account's difference, as the person looking at it asks.

    A POST, and only ever for the figure just shown: the position is taken
    again here, so a rate that moved between the page loading and the
    button being pressed records what is true now rather than what the
    screen happened to say.
    """

    def post(self, request, pk):
        account = get_object_or_404(CurrentAccount, pk=pk)
        position = fx_position(account)
        if not position or position.get("unavailable"):
            messages.warning(request, _(
                "No rate for %(currency)s today, so the difference could not be worked out.")
                % {"currency": getattr(account.own_currency, "code", "")})
        else:
            movement = post_fx_difference(
                account, member=getattr(request.user, "member", None),
                position=position)
            if movement is None:
                messages.info(request, _(
                    "Nothing to record: the book already carries this balance at today's rate."))
            else:
                messages.success(request, _(
                    "Exchange rate difference recorded: %(amount)s. "
                    "%(name)s still owes %(owed)s %(currency)s.")
                    % {"amount": movement.amount, "name": account.name,
                       "owed": position["own_balance"], "currency": position["currency"]})
        back = request.POST.get("next") or ""
        if back.startswith("/"):
            return redirect(back)
        return redirect("accounts:detail", pk=account.pk)
