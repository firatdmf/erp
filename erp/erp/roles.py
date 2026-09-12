"""The sales-rep role: read stock and sales, write only a draft order.

A sales rep needs the two things she talks to customers about — what is
in stock at what price, and what has been sold. She also raises a new
order, which is born "pending" (Açık), and packs it: scanning rolls onto
the packing screen and sorting them into sacks.

She still may not COMPLETE one — no shipping, no delivery, no
cancelling — because completion is the step that cuts real stock and
posts money to the customer's account. Packing stops short of that: a
scan RESERVES a roll, and a reservation becomes a stock-out only when
somebody with the right to complete the order does so
(operating.views_warehouse.apply_order_status_change, which refuses
this role outright whoever calls it).

Enforcement is one choke point, `ReadOnlyRoleMiddleware`, rather than a
decorator sprinkled over several hundred views. That is deliberate: this
codebase's views are almost all plain `@login_required`, so an allowlist
that runs before URL resolution is the only way to be sure a route added
tomorrow is closed by default rather than open by default.

Two independent gates, both of which must pass:

  1. METHOD — anything that is not GET/HEAD/OPTIONS is refused, UNLESS
     the path is in WRITE_PATHS (create an order, create a customer),
     under WRITE_PREFIXES (edit an order, which needs an id), or matched
     by WRITE_PATTERNS (the packing screen's endpoints, which carry an
     id in the MIDDLE of the path so they are neither). The exact-path
     set is exact on purpose: a prefix hands over every route that
     happens to start the same way. Editing is additionally
     object-scoped — erp.ownership.can_edit lets her change only what
     she created — but that check lives in the view, not here.

  2. PATH — a GET must start with one of READ_PREFIXES *and* must not
     contain one of WRITE_SEGMENTS. The second half matters because
     several views here mutate on GET (`orders/delete/<pk>/`,
     `warehouses/<pk>/rolls/<pk>/move-here/`), so "GET is safe" is not
     true in this app and cannot be assumed.

The nav is filtered to match by asking this very gate about each
entry's own route (see may_use_nav_item), so the menu cannot drift out
of step with what she may actually do. That is still cosmetic — the
middleware is the security boundary; hiding a link is only courtesy.
"""

import re

SALES_REP = "sales_rep"


# Paths any signed-in member may reach whatever their role: the shell
# itself. Without these the sales rep cannot load a stylesheet, switch
# language, read a notification or sign out.
COMMON_PREFIXES = (
    "/static/",
    "/media/",
    "/i18n/",
    "/authentication/signin",
    "/authentication/signout",
    "/notifications/",
)

# What the sales-rep role is actually for.
READ_PREFIXES = COMMON_PREFIXES + (
    "/",                                  # the dashboard she lands on
    # STOCK — quantities and prices
    "/operating/warehouses/",
    "/marketing/product_list/",
    "/marketing/product_detail/",
    "/marketing/product-groups/",
    "/marketing/product/",                # /product/<pk>/variants/
    "/marketing/catalog/",
    # CUSTOMERS — she raises orders against these, so she has to be able
    # to look them up. This is READ of the whole customer book, not just
    # her own: a rep needs to find an existing customer before deciding
    # to add a new one. Editing stays hers-only (erp.ownership.can_edit).
    "/crm/contact/list/",
    "/crm/company/list/",
    "/crm/contact/detail/",
    "/crm/company/detail/",
    # SALES — the orders and what they add up to. The order list is
    # book-scoped, and the plain /operating/orders/ link is a redirect
    # into it, so the scoped address has to be reachable too or the
    # sales page 403s the moment she clicks it.
    "/operating/orders/",
    "/operating/books/",
)

# Path segments that mean "this writes", checked against every GET even
# inside an allowed prefix. Matched as whole slash-separated segments so
# "add" does not also swallow "address".
WRITE_SEGMENTS = frozenset({
    "create", "new", "edit", "update", "delete", "bulk-delete",
    "add", "manual-add", "account-create", "remove", "save",
    "import", "upload", "merge-duplicates", "stock-out", "move-here",
    "pack", "scan", "assign_pack", "assign_item", "complete",
})

# What each "action" nav item actually posts to, by URL NAME. An action
# item names a JS function rather than a route, so there is nothing to
# reverse and nothing to check — this is the missing link that turns
# "openCompanySidebar" into "POST crm:create_company", which the gate
# below can then answer for.
#
# By url name rather than a literal path so a route that moves is
# followed automatically. An action missing from this map is HIDDEN:
# an unmapped sidebar is one nobody has confirmed is safe to offer.
NAV_ACTION_ENDPOINTS = {
    "openMainContactSidebar":        "crm:create_contact",
    "openCompanySidebar":            "crm:create_company",
    "openOrderSidebar":              "operating:create_order",
    "openTaskSidebar":               "todo:create_task",
    "openAddSupplierSidebar":        "crm:create_supplier_partial",
    "openWarehouseSidebar":          "operating:create_warehouse_partial",
    "openBookSidebar":               "accounting:create_book",
    "openRawMaterialSidebar":        "operating:create_raw_material_good_json",
    "openRawMaterialReceiptSidebar": "operating:create_raw_material_receipt_partial",
    "openRawMaterialItemSidebar":    "operating:create_raw_material_item_partial",
}


def may_use_nav_item(item):
    """Whether a sales rep should be shown one nav item.

    The point of this function is that the menu is DERIVED from the same
    gate the middleware enforces, rather than from a second hand-written
    list of allowed entries. A hand-written list is a copy, and a copy
    drifts: widen the gate and the menu hides something she can use;
    narrow it and the menu offers a door that 403s. Reversing the item's
    own route and asking may_read/may_write cannot drift, because there
    is only one answer to disagree with.

    A link is a page she navigates to, so it is checked with may_read;
    an action posts, so it is checked with may_write. Anything that
    cannot be resolved to a path is hidden — default deny, same as
    everywhere else in this module.
    """
    from django.urls import NoReverseMatch, reverse

    if item.get("action"):
        name = NAV_ACTION_ENDPOINTS.get(item["action"])
        if not name:
            return False
        try:
            return may_write(reverse(name))
        except NoReverseMatch:
            return False

    if item.get("url"):
        try:
            return may_read(reverse(item["url"]))
        except NoReverseMatch:
            return False

    if item.get("href"):
        return may_read(item["href"])

    return False


# The ONLY paths a sales rep may write to. Exact matches — never
# prefixes. "/operating/orders/create" is the order form's POST target
# (operating:create_order); note the sibling "/operating/orders/create/"
# WITH a trailing slash is create_web_order, the storefront checkout
# API, and is deliberately NOT here.
WRITE_PATHS = frozenset({
    "/operating/orders/create",
    # A sale needs a customer. The order form creates one inline; the
    # Add menu's Contact/Company sidebars use the full CRM endpoints.
    "/crm/quick_create_customer/",
    "/crm/contact/create/",
    "/crm/company/create/",
})

# Write paths that carry an id, so they cannot be exact strings. Kept
# tiny and specific for the same reason WRITE_PATHS is exact: each entry
# here opens every route beneath it. Object-level permission is NOT this
# gate's job — OrderEdit.dispatch decides whose order it is, via
# erp.ownership.can_edit. This only decides that the route is reachable.
WRITE_PREFIXES = (
    "/operating/orders/edit/",
    "/crm/contact/update/",
    "/crm/update_company/",
)

# GETs that must bypass the WRITE_SEGMENTS check because "create" is in
# the path. The form itself is loaded over HTMX GET, and it looks up
# rolls and barcodes over GET while the user fills it in.
READ_PATHS = frozenset({
    "/operating/orders/create",
    "/operating/orders/create/roll_list/",
    "/operating/orders/create/barcode_check/",
    "/operating/orders/create/barcode_resolve/",
    # The two lookups the order form is USELESS without. Writing an
    # order is the one thing this role exists to do, and an order needs
    # a product and a customer; with these closed the rep could open the
    # sidebar and post it, but could not find anything to put in it —
    # both searches returned the read-only 403 page into the dropdown,
    # which renders as a silently empty list.
    #
    # Neither widens what she can reach. The product search is already
    # scoped to the books she is assigned (_books_in_scope), and the
    # customer search reads the same contact/company names that
    # /crm/contact/list/ hands her in full above.
    "/operating/product_autocomplete/",
    "/crm/customer_autocomplete/",
    # The top-bar command palette (Ctrl-K). It is on every page she can
    # reach, so leaving it closed meant a search box that answered every
    # keystroke with a 403 and rendered as "no results". What it hands
    # back is filtered to what she may open — erp.views.GlobalSearch runs
    # each result's own URL through may_read — so this opens the box, not
    # the records behind it.
    "/search/",
})

# GET prefixes that must bypass WRITE_SEGMENTS: the edit form is loaded
# over GET before it is posted back.
READ_PREFIXES_EXTRA = WRITE_PREFIXES

# GETs that must bypass WRITE_SEGMENTS but name a book, so they can be
# neither an exact path (READ_PATHS) nor a prefix (which would hand over
# every route under /operating/books/<id>/). Anchored end to end for
# that reason, and kept as tiny as the two lists above.
#
# This is the order form's PAGE face: the same form as the drawer, from
# the same view, with its book named in the URL. It is what the "New
# order" button on the book-scoped order list links to, so with it
# closed the rep could reach the sales list and 403 on the one button
# the role exists to press.
#
# It opens nothing the drawer did not: the route is book_scoped, so a
# book she is not assigned still 404s, and the form still POSTs to
# "/operating/orders/create" above.
READ_PATTERNS = (
    re.compile(r"^/operating/books/\d+/orders/create/$"),
    # The packing screen ("Paketleme"), linked from every order's detail
    # page. Its id sits in the middle, and the segment "pack" is in
    # WRITE_SEGMENTS — rightly, since the screen creates Pack #1 as a
    # GET side effect.
    re.compile(r"^/operating/orders/\d+/pack/$"),
)

# The packing screen's own endpoints. Patterns rather than exact paths
# because the order id sits in the MIDDLE, and rather than the prefix
# "/operating/orders/" because that is every order route there is.
#
# Named one by one, and only the three the screen actually posts to, so
# that the fourth sibling — "/operating/orders/<id>/pack/complete/" — is
# refused by this list simply by not being on it. Completion is the step
# that turns reservations into a stock-out and bills the customer, and
# it is the line this role does not cross. apply_order_status_change
# refuses her again on the way through, so the two are independent:
# adding "complete" here by accident would still not ship an order.
#
# reserve_remove and reserve_update are deliberately absent too — no
# template calls them, and an allowlist is for what is used, not for
# what exists.
WRITE_PATTERNS = (
    re.compile(r"^/operating/orders/\d+/pack/add/$"),
    re.compile(r"^/operating/orders/\d+/pack/assign_pack/$"),
    re.compile(r"^/operating/orders/\d+/pack/assign_item/$"),
    # Adding and deleting a sack. The packing screen posts its pack
    # housekeeping to the packing list's own URL (its `data-pack-crud-url`),
    # which is why a read-only-looking address is in the WRITE list.
    re.compile(r"^/operating/orders/\d+/packing_list/$"),
)


def may_write(path):
    """Whether a sales rep may POST to `path`.

    Route-level only. Whether it is HER order or customer is settled by
    erp.ownership.can_edit inside the view, which is where the object
    actually is — and, for the packing routes, by the `book_guarded`
    wrapper on them in operating/urls.py.
    """
    return (path in WRITE_PATHS
            or path.startswith(WRITE_PREFIXES)
            or any(pattern.match(path) for pattern in WRITE_PATTERNS))


def is_sales_rep(actor):
    """True for a Member carrying the sales_rep permission.

    `actor` may be a User OR a Member: the order pipeline calls
    apply_order_status_change with a Member in one place and
    request.user everywhere else, and a check that silently answered
    False for one of them would be a hole exactly where it matters.

    Superusers are never sales reps however they are flagged — an admin
    locked out of their own install by a stray permission row would have
    no way back in.
    """
    if actor is None:
        return False

    # A Member has `.permissions`; a User reaches it through `.member`.
    if hasattr(actor, "permissions"):
        member = actor
        user = getattr(actor, "user", None)
    else:
        if not getattr(actor, "is_authenticated", False):
            return False
        member = getattr(actor, "member", None)
        user = actor

    if member is None:
        return False
    if getattr(user, "is_superuser", False):
        return False
    try:
        return member.permissions.filter(name=SALES_REP).exists()
    except Exception:
        return False


def may_read(path):
    """Whether a sales rep may GET `path`."""
    if not path.startswith(READ_PREFIXES):
        # "/" is in READ_PREFIXES and prefixes everything, so this is
        # unreachable in practice — kept so the rule reads honestly.
        return False
    if path == "/":
        return True
    if path in READ_PATHS or path.startswith(READ_PREFIXES_EXTRA):
        return True
    if any(pattern.match(path) for pattern in READ_PATTERNS):
        return True
    if any(seg in WRITE_SEGMENTS for seg in path.strip("/").split("/")):
        return False
    return any(
        path.startswith(p) for p in READ_PREFIXES if p != "/"
    )
