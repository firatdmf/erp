"""Keeping a page about one record behind its customer's directory.

The models wall themselves (crm.models.DirectoryManager): a company,
contact or supplier outside the reader's directories is simply not
found. What that cannot cover is a page keyed by SOMETHING ELSE's id
that goes on to name the customer — an order's printout, its packing
list. Django follows `order.contact` with the base manager, on purpose,
so such a page has to be asked whether its reader may see who it is
about.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import Http404

from .models import of_books_in_reach, within_directories


def customer_guarded(view, model, *paths, kwarg="pk", book=None):
    """Refuse an object page whose row names a customer or supplier
    outside the reader's directories.

    `paths` are the row's foreign keys to CRM records ("contact",
    "company", "order__contact"). A row naming nobody passes: this is
    the customer wall, not a book check, and it changes nothing between
    two books that share a directory.

    `book` is the path to the row's book, where it has one. A customer
    can be shared between two businesses, and then being able to see the
    customer is not enough: the row has to be of a book on the reader's
    own side as well (crm.models.of_books_in_reach).

    404 rather than 403, as accounting.book_scope does it: whether a row
    exists is not something to be probed by watching the status code.
    Applied in the URLconf, beside those guards, so the rule is read in
    one place.
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        rows = model._base_manager.filter(pk=kwargs.get(kwarg))
        # A row that does not exist at all is the view's to report.
        if rows.exists():
            mine = within_directories(rows, *paths)
            if book:
                mine = of_books_in_reach(mine, book)
            if not mine.exists():
                raise Http404("No such record.")
        return view(request, *args, **kwargs)
    return wrapper
