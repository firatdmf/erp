"""The one definition of the main navigation.

The desktop sidebar (`components/_sidebar_nejum.html`) and the mobile
drawer (`components/_mobile_shell.html`) render the SAME sections and
items from this list — they differ only in markup and CSS. Each used to
carry its own hand-written copy, and they drifted: the drawer spent a
long time with no way to create a task, contact or company at all, and
was missing "Add warehouse" and both product-group entries, while the
sidebar was missing Perakende Satışları.

Adding a menu entry means editing this file and nothing else.

A SECTION is either
  * a link — `url` and no `groups`; renders as one tile on the desktop
    and lands in the drawer's "Workspace" section, or
  * a menu — `groups`, each holding items; renders as a hover flyout on
    the desktop and as a labelled section in the drawer.

`key` is load-bearing: it becomes `data-flyout="…"` on the desktop tile,
which shell.css targets by name (`[data-flyout="accounting"]` gets its own
compact treatment because that flyout is the tallest — it holds the ledger
entries, the current accounts and the reports).

An ITEM points somewhere in exactly one of three ways:
  * `url`   — a URL name, reversed at render time (`query` is appended)
  * `href`  — a literal path
  * `action`— the name of a JS function base.html defines (the drawer
              closes itself before calling it; the sidebar doesn't need
              to)
"""
from django.utils.translation import gettext_lazy as _

# Sections the drawer floats to the top, in this order. The daily flow
# on a phone is warehouse → orders → current accounts, so those come first
# there; the desktop keeps the declared order. "cari" used to name its own
# section and is now a group inside accounting, so the phone floats
# accounting instead — dropping the key entirely would have silently
# reordered the drawer.
MOBILE_FIRST = ("operations", "accounting")

# The drawer has no room for a tile per link-only section, so it
# collects them all under one heading.
MOBILE_LINKS_SECTION = _("Workspace")

NAV_SECTIONS = [
    {
        "key": "add",
        "label": _("Add"),
        "icon": "plus",
        "title": _("Add new record"),
        "title_icon": "plus-circle",
        "groups": [
            {"title": _("ADD SINGLE RECORD"), "items": [
                {"label": _("Contact"),   "icon": "user",          "action": "openMainContactSidebar"},
                {"label": _("Company"),   "icon": "building-2",    "action": "openCompanySidebar"},
                {"label": _("Task"),      "icon": "check-circle",  "action": "openTaskSidebar"},
                {"label": _("Product"),   "icon": "tag",           "url": "marketing:product_create"},
                {"label": _("Order"),     "icon": "shopping-cart", "action": "openOrderSidebar"},
                {"label": _("Blog post"), "icon": "book-open",     "url": "marketing:blog_create"},
                {"label": _("Supplier"),  "icon": "truck",         "action": "openAddSupplierSidebar"},
                {"label": _("Warehouse"), "icon": "warehouse",     "action": "openWarehouseSidebar"},
            ]},
        ],
    },
    {
        "key": "dashboard",
        "label": _("Dashboard"),
        "icon": "layout-grid",
        "url": "index",
    },
    {
        "key": "team",
        "label": _("My Team"),
        "icon": "users",
        "groups": [
            {"title": _("TEAM MANAGEMENT"), "items": [
                {"label": _("Team members"),     "icon": "list",           "url": "team:team_list"},
                {"label": _("Assign task"),      "icon": "list-checks",    "url": "team:team_tasks"},
                {"label": _("Messages"),         "icon": "message-circle", "url": "team:team_messages"},
                {"label": _("Manage roles"),     "icon": "shield",         "url": "team:team_roles"},
                {"label": _("Schedule meeting"), "icon": "video",          "url": "team:team_meetings"},
            ]},
        ],
    },
    # Accounting holds everything ledger-related: the books themselves, the
    # current accounts that used to sit in their own top-level "Accounts"
    # flyout, and the entry actions that used to be buttons on the book
    # detail page. That page is a report now — it shows the position, it
    # does not change it — so the actions had to live somewhere, and
    # splitting them across two top-level menus is what made them hard to
    # find in the first place.
    #
    # The ENTRIES items are book-scoped but the menu has no book, so each
    # points at an accounting:go_* redirect that resolves the member's
    # working book (see WorkingBookRedirect).
    #
    # Deliberately absent: "Add Receivable" and "Add Payable". A receivable
    # is what an order or an invoice leaves behind, and a payable what a
    # purchase does; typing one in directly creates a balance with no
    # document under it, which is how the ledger and the cari cards drift
    # apart. Raise an order or record a payment instead.
    {
        "key": "accounting",
        "label": _("Accounting"),
        "icon": "calculator",
        "groups": [
            {"title": _("LEDGERS"), "items": [
                {"label": _("View ledgers"),   "icon": "book",            "url": "accounting:index"},
                {"label": _("Create ledger"),  "icon": "plus-circle",     "action": "openBookSidebar"},
                # Turkish-only label, deliberately not translated.
                {"label": "Perakende Satışları", "icon": "shopping-basket", "url": "accounts:retail"},
            ]},
            {"title": _("ENTRIES"), "items": [
                {"label": _("Add capital"),       "icon": "circle-plus",   "url": "accounting:go_add_capital"},
                {"label": _("Add revenue"),       "icon": "arrow-up",      "url": "accounting:go_add_revenue"},
                {"label": _("Add expense"),       "icon": "arrow-down",    "url": "accounting:go_add_expense"},
                {"label": _("Pay dividend"),      "icon": "hand-coins",    "url": "accounting:go_pay_dividend"},
                {"label": _("Add asset"),         "icon": "home",          "url": "accounting:go_add_asset"},
                {"label": _("Add cash account"),  "icon": "wallet",        "url": "accounting:go_add_cash_account"},
            ]},
            {"title": _("TRANSACTIONS"), "items": [
                {"label": _("All transactions"),   "icon": "list",     "url": "accounting:go_transactions"},
                {"label": _("Expenses"),           "icon": "receipt",  "url": "accounting:go_expenses"},
                {"label": _("Transfer"),           "icon": "shuffle",  "url": "accounting:go_transfer"},
                {"label": _("Currency exchange"),  "icon": "refresh-cw", "url": "accounting:go_currency_exchange"},
            ]},
            {"title": _("CURRENT ACCOUNTS"), "items": [
                {"label": _("All Accounts"), "icon": "id-card",   "url": "accounts:list"},
                {"label": _("New Account"),  "icon": "user-plus", "url": "accounts:create"},
            ]},
            {"title": _("INVOICES"), "items": [
                {"label": _("All Invoices"), "icon": "file-text", "url": "accounts:invoice_list"},
                {"label": _("New Invoice"),  "icon": "file-plus", "url": "accounts:invoice_create"},
            ]},
            {"title": _("COLLECTION / PAYMENT"), "items": [
                {"label": _("All Payments"),              "icon": "wallet",     "url": "accounts:payment_list"},
                {"label": _("New Collection / Payment"),  "icon": "hand-coins", "url": "accounts:payment_create"},
            ]},
            {"title": _("CHECK / PROMISSORY NOTE"), "items": [
                {"label": _("Portfolio"),          "icon": "scroll-text", "url": "accounts:check_list"},
                {"label": _("New Check / Note"),   "icon": "plus-circle", "url": "accounts:check_create"},
            ]},
            {"title": _("SHARES"), "items": [
                {"label": _("Cap table"),        "icon": "pie-chart", "url": "accounting:go_cap_table"},
                {"label": _("Add stakeholder"),  "icon": "user-plus", "url": "accounting:go_add_stakeholder"},
            ]},
            {"title": _("REPORTS"), "items": [
                {"label": _("Sales dashboard"), "icon": "bar-chart-3",    "url": "accounting:sales_dashboard"},
                {"label": _("Report Center"), "icon": "pie-chart",      "url": "accounts:report_index"},
                {"label": _("Aging"),         "icon": "clock",          "url": "accounts:report_aging"},
                {"label": _("Trial Balance"), "icon": "layout-grid",    "url": "accounts:report_trial_balance"},
                {"label": _("Due Calendar"),  "icon": "calendar-clock", "url": "accounts:report_due_calendar"},
                {"label": _("Credit Limit"),  "icon": "shield-alert",   "url": "accounts:report_credit_limit"},
            ]},
            {"title": _("HELP"), "items": [
                {"label": _("User Guide"), "emoji": "📘", "icon": "book-open", "url": "accounts:help"},
            ]},
        ],
    },
    {
        "key": "marketing",
        "label": _("Marketing"),
        "icon": "target",
        "groups": [
            {"title": _("PRODUCTS"), "items": [
                {"label": _("Create product"),   "icon": "plus-circle", "url": "marketing:product_create"},
                {"label": _("Product list"),     "icon": "list",        "url": "marketing:product_list"},
                {"label": _("Product groups"),   "icon": "layers",      "url": "marketing:product_group_list"},
                {"label": _("Add product group"), "icon": "plus-circle", "url": "marketing:product_group_create"},
            ]},
            {"title": _("CUSTOMERS"), "items": [
                {"label": _("Companies"), "icon": "building-2", "url": "crm:company_list"},
                {"label": _("Contacts"),  "icon": "users",      "url": "crm:contact_list"},
            ]},
            {"title": _("BLOG"), "items": [
                {"label": _("Create blog post"), "icon": "plus-circle", "url": "marketing:blog_create"},
                {"label": _("Blog list"),        "icon": "book-open",   "url": "marketing:blog_list"},
            ]},
        ],
    },
    {
        "key": "operations",
        "label": _("Operations"),
        "icon": "settings-2",
        "groups": [
            {"title": _("QR ACTIONS"), "items": [
                {"label": _("QR scan"),         "icon": "qr-code",   "url": "operating:scan_order_item_unit"},
                {"label": _("QR scan package"), "icon": "package-2", "url": "operating:scan_order_item_unit_pack"},
            ]},
            {"title": _("RAW MATERIAL"), "items": [
                {"label": _("Raw material list"),    "icon": "list",        "url": "operating:raw_material_good_list"},
                {"label": _("Create raw material"),  "icon": "box",         "action": "openRawMaterialSidebar"},
                {"label": _("Raw material receipt"), "icon": "file-text",   "action": "openRawMaterialReceiptSidebar"},
                {"label": _("Raw material item"),    "icon": "plus-square", "action": "openRawMaterialItemSidebar"},
            ]},
            {"title": _("ORDERS"), "items": [
                {"label": _("Create order"), "icon": "plus-circle", "action": "openOrderSidebar"},
                {"label": _("Order list"),   "icon": "list",        "url": "operating:order_list"},
            ]},
            {"title": _("WAREHOUSE"), "items": [
                {"label": _("My warehouses"), "icon": "warehouse",   "url": "operating:warehouse_list"},
                {"label": _("Add warehouse"), "icon": "plus-circle", "url": "operating:create_warehouse"},
            ]},
        ],
    },
    {
        "key": "procurement",
        "label": _("Procurement"),
        "icon": "shopping-basket",
        "groups": [
            {"title": _("PURCHASING"), "items": [
                {"label": _("Purchases"),         "icon": "package-plus", "url": "accounts:invoice_list",
                 "query": "?type=purchase"},
                {"label": _("Purchase requests"), "icon": "file-text",    "url": "procurement:request_list"},
                {"label": _("Purchase orders"),   "icon": "receipt",      "url": "accounts:purchase_order_list"},
            ]},
            {"title": _("SUPPLIERS"), "items": [
                {"label": _("Supplier list"), "icon": "truck",       "url": "crm:supplier_list"},
                {"label": _("Add supplier"),  "icon": "plus-circle", "action": "openAddSupplierSidebar"},
            ]},
        ],
    },
    {
        "key": "analytics",
        "label": _("Analytics"),
        "icon": "line-chart",
        "url": "operating:order_analytics",
    },
    {
        "key": "mail",
        "label": _("Mail"),
        "icon": "mail",
        "groups": [
            # No group title on this one — a single unlabelled group.
            {"items": [
                {"label": _("Email automation"), "icon": "gauge", "url": "email_automation:dashboard"},
                {"label": _("My emails"),        "icon": "inbox", "url": "email_automation:my_emails"},
            ]},
        ],
    },
    {
        "key": "notes",
        "label": _("Notes"),
        "icon": "sticky-note",
        "url": "notes:index",
    },
]


def mobile_sections():
    """NAV_SECTIONS as the drawer wants them: the daily-flow sections
    first, link-only sections collected into one "Workspace" section so
    each doesn't need a heading of its own."""
    menus = [s for s in NAV_SECTIONS if s.get("groups")]
    links = [s for s in NAV_SECTIONS if not s.get("groups")]

    ordered = (
        [s for k in MOBILE_FIRST for s in menus if s["key"] == k]
        + [s for s in menus if s["key"] not in MOBILE_FIRST]
    )
    if links:
        ordered.append({
            "key": "workspace",
            "label": MOBILE_LINKS_SECTION,
            "groups": [{"items": [
                {"label": s["label"], "icon": s["icon"], "url": s["url"]}
                for s in links
            ]}],
        })
    return ordered
