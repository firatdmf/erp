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
