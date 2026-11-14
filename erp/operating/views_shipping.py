"""The page where shipping between countries is set (operating.shipping):
one row per destination country that doesn't simply take goods from
anywhere."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .countries import country_choices, country_name
from .models import ShippingRule, Warehouse
from .views_warehouse import _is_admin

MODES = ("anywhere", "inside", "except")


def _codes(values, known):
    out = []
    for value in values:
        value = (value or "").strip().upper()
        if value in known and value not in out:
            out.append(value)
    return out


def _rows_from(request, known):
    """The rows as sent: [{destination, mode, not_from, best_from}]."""
    rows = []
    for key in request.POST.getlist("row"):
        destination = (request.POST.get(f"dest_{key}") or "").strip().upper()
        mode = request.POST.get(f"mode_{key}")
        rows.append({
            "destination": destination if destination in known else "",
            "mode": mode if mode in MODES else "anywhere",
            "not_from": _codes(request.POST.getlist(f"not_from_{key}"), known),
            "best_from": _codes(request.POST.getlist(f"best_from_{key}"), known),
        })
    return rows


def _rows_of(rules):
    return [{
        "destination": rule.destination,
        "mode": "inside" if rule.only_from_inside else ("except" if rule.not_from else "anywhere"),
        "not_from": list(rule.not_from),
        "best_from": list(rule.best_from),
    } for rule in rules]


def _page(request, rows, status=200):
    names = dict(country_choices())
    for row in rows:
        row["not_from_named"] = [(c, names.get(c, c)) for c in row["not_from"]]
        row["best_from_named"] = [(c, names.get(c, c)) for c in row["best_from"]]
    # Where the stock is, so the rules can be read against it.
    places = {}
    unplaced = []
    for warehouse in Warehouse.objects.filter(kind="normal", on_storefront=True).order_by("name"):
        if warehouse.country:
            places.setdefault(warehouse.country, []).append(warehouse.name)
        else:
            unplaced.append(warehouse.name)
    return render(request, "operating/shipping_rules.html", {
        "rows": rows,
        "countries": country_choices(),
        "places": sorted(((country_name(c), names_) for c, names_ in places.items())),
        "unplaced": unplaced,
        "can_edit": _is_admin(request.user),
    }, status=status)


@login_required
def shipping_rules(request):
    if request.method != "POST":
        return _page(request, _rows_of(ShippingRule.objects.all()))
    if not _is_admin(request.user):
        messages.error(request, _("Only an admin can change where goods may be sent."))
        return redirect("operating:shipping_rules")

    known = {code for code, _name in country_choices()}
    rows = [row for row in _rows_from(request, known)
            if row["destination"] or row["not_from"] or row["best_from"]]
    destinations = [row["destination"] for row in rows]
    if "" in destinations:
        messages.error(request, _("Choose the country each row is about."))
        return _page(request, rows, status=400)
    twice = {code for code in destinations if destinations.count(code) > 1}
    if twice:
        messages.error(request, _("Each country can have one row only: %(countries)s.")
                       % {"countries": ", ".join(sorted(country_name(c) for c in twice))})
        return _page(request, rows, status=400)
    for row in rows:
        # A country always takes its own goods; naming it is a slip.
        row["not_from"] = [c for c in row["not_from"] if c != row["destination"]]
        row["best_from"] = [c for c in row["best_from"]
                            if c != row["destination"] and c not in row["not_from"]]
        if row["mode"] == "except" and not row["not_from"]:
            row["mode"] = "anywhere"

    with transaction.atomic():
        ShippingRule.objects.exclude(destination__in=destinations).delete()
        for row in rows:
            inside = row["mode"] == "inside"
            ShippingRule.objects.update_or_create(destination=row["destination"], defaults={
                "only_from_inside": inside,
                "not_from": [] if inside or row["mode"] == "anywhere" else row["not_from"],
                "best_from": [] if inside else row["best_from"],
            })
    messages.success(request, _("Saved. The storefront offers stock by these rules from now on."))
    return redirect("operating:shipping_rules")
