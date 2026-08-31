"""Retire the app-wide default-book flag in favour of per-member assignment.

The flag answered "where does a record land when nothing says which?"
That question already had a better answer — the working book of whoever
is entering it — and two answers to one question disagree the moment
somebody's work moves.

Before dropping it, every member gets the book they were effectively
already working in, so nobody is left with no book at all: their own
`default_book` if they picked one, otherwise whatever the flag was
pointing at. Superusers are not seeded — `member_books` grants them
every book implicitly.
"""
from django.db import migrations


def seed_member_books(apps, schema_editor):
    Member = apps.get_model("authentication", "Member")
    Book = apps.get_model("accounting", "Book")

    fallback = (Book.objects.filter(is_default_cari_target=True).first()
                or Book.objects.order_by("id").first())
    if fallback is None:
        return  # fresh install, no books yet

    for member in Member.objects.select_related("user").all():
        if member.books.exists():
            continue
        if member.user_id and member.user.is_superuser:
            continue
        book = member.default_book or fallback
        member.books.add(book)
        if member.default_book_id is None:
            member.default_book = book
            member.save(update_fields=["default_book"])


def unseed(apps, schema_editor):
    """Assignments are additive and harmless to keep, so rolling back
    leaves them; clearing them would lose choices made since."""


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0093_alter_invoiceitem_unit_price'),
        ('authentication', '0018_member_books'),
    ]

    operations = [
        # Runs first, while is_default_cari_target still exists.
        migrations.RunPython(seed_member_books, unseed),
        migrations.RemoveConstraint(
            model_name='book',
            name='only_one_default_cari_target_book',
        ),
        migrations.RemoveField(
            model_name='book',
            name='is_default_cari_target',
        ),
    ]
