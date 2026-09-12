"""Book scoping for the ledger.

A ledger page shows one book's money. Which book was, until now, never
said: /accounting/accounts/ listed every account in every book and summed
their balances into one figure, so a factory's receivables were added to a
wholesaler's and the total meant nothing.

The book is named in the URL — /accounting/books/5/accounts/ — rather than
carried in the session, so a page can be bookmarked, shared and opened in
two tabs on two books at once.

Applied in the URLconf rather than as a view mixin: the ledger's 19
collection pages are spread over five modules and are a mix of View,
TemplateView and plain functions, and wrapping them where they are routed
keeps the rule in one readable place instead of in nineteen class
headers. The wrapper swallows `book_id` and hands the view
`request.book`, so no view signature changes.
"""
from functools import wraps

from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import Book
from .services_accounts import member_can_use_book


def book_scoped(view):
    """Resolve `book_id` from the URL onto `request.book`, or 404.

    404 rather than 403 for a book the member is not assigned: whether a
    given book exists is not something an unassigned member should be
    able to probe by watching the status code change.
    """
    @wraps(view)
    def wrapper(request, *args, book_id=None, **kwargs):
        book = get_object_or_404(Book, pk=book_id)
        member = getattr(request.user, "member", None)
        if not member_can_use_book(member, book):
            raise Http404("No such book.")
        request.book = book
        return view(request, *args, **kwargs)
    return wrapper


def book_guarded(view, model, book_path="book"):
    """Refuse an OBJECT page whose row belongs to a book the viewer is
    not assigned, and put that row's book on `request.book`.

    Object routes do not name their book in the path, and should not:
    /books/5/accounts/912/ where 912 belongs to book 2 is a mismatch
    every view would then have to check for, so the row's own FK is the
    single answer. But "the row knows its book" quietly became "nobody
    checks the row's book". Collections were scoped and objects were
    left open, so a member assigned only to Ergene could read a Laleli
    customer's statement, and edit its orders, by walking sequential ids.

    `book_path` is how to get from the row to its book — "book" for an
    invoice, "current_account.book" for an order (an Order carries no book of its
    own), "accounting_book" for a warehouse.

    404 rather than 403, for the same reason book_scoped does it: which
    books exist is not something an unassigned member should be able to
    probe by watching the status code change.

    Applied in the URLconf beside `scoped`, per the note at the top of
    this module: the rule stays in one readable place instead of being
    repeated in twenty view bodies that are a mix of View, DetailView
    and plain functions.
    """
    @wraps(view)
    def wrapper(request, *args, pk=None, **kwargs):
        obj = get_object_or_404(model, pk=pk)
        book = obj
        for step in book_path.split("."):
            book = getattr(book, step, None)
            if book is None:
                break
        member = getattr(request.user, "member", None)
        if not member_can_use_book(member, book):
            raise Http404("No such record.")
        request.book = book
        return view(request, *args, pk=pk, **kwargs)
    return wrapper


def book_guarded_for_sales_rep(view, model, book_path="book"):
    """`book_guarded`, but only for the sales-rep role.

    The packing screen is reached by every warehouse hand and every
    manager, and it names an order by id alone. Guarding it outright —
    the way order_detail and edit_order are guarded — is the tidier rule
    and probably the right one eventually, but it cannot be done here
    without changing what everybody else sees: an order carries its book
    through its CURRENT ACCOUNT, and `create_web_order` files a storefront
    order without one, so a blanket guard would 404 the packing screen
    for every web order that ever arrives. (Prod has none today, which is
    the only reason that is not already a live bug on order_detail.)

    So the guard is applied where the exposure is actually new. The
    sales-rep role reaches these routes for the first time in
    erp.roles.WRITE_PATTERNS, and her book assignment is the only thing
    that says which orders are hers to pack; without this she could scan
    rolls onto another book's order by walking sequential ids. Everyone
    else passes through exactly as before.

    Narrow on purpose, and worth revisiting as one rule once a web order
    is given a current account.
    """
    guarded = book_guarded(view, model, book_path)

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from erp.roles import is_sales_rep

        if is_sales_rep(getattr(request, "user", None)):
            return guarded(request, *args, **kwargs)
        return view(request, *args, **kwargs)
    return wrapper


def current_book(request):
    """Context processor: the book the page is about.

    `request.book` when the URL named one, else the viewer's working
    book, so a page outside the ledger — the sidebar, a CRM record —
    can still say which book the reader is in and link into it.
    """
    book = getattr(request, "book", None)
    if book is None:
        user = getattr(request, "user", None)
        member = getattr(user, "member", None) if user else None
        if member is None:
            return {"current_book": None, "my_books": []}
        from .services_accounts import get_default_book, member_books
        books = member_books(member)
        return {"current_book": get_default_book(member) if books.exists() else None,
                "my_books": books}
    from .services_accounts import member_books
    member = getattr(getattr(request, "user", None), "member", None)
    return {"current_book": book, "my_books": member_books(member)}
