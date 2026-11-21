"""Bring every product's Turkish and Russian text up to its English.

The same work a product save and the hourly housekeeping do
(marketing.product_translation), all at once: for the first run over the
catalog, or after a bulk change to the English. Translations typed by hand
before are kept until their English changes.
"""
from django.core.management.base import BaseCommand

from marketing import product_translation
from marketing.models import Product


class Command(BaseCommand):
    help = "Translate product texts into the storefront's other languages, from the English."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Count what would be translated or kept; ask Gemini nothing.")
        parser.add_argument("--max-requests", type=int, default=None)

    def handle(self, *args, dry_run=False, max_requests=None, **options):
        if dry_run:
            translate = keep = 0
            for title, raw in Product.everywhere.values_list("title", "description"):
                _source, _key, todo, kept = product_translation._plan(title, raw)
                translate += bool(todo)
                keep += bool(kept)
            self.stdout.write(f"to translate: {translate} products; to keep as written: {keep}")
            return
        counts = product_translation.translate(max_requests=max_requests)
        self.stdout.write(f"translated {counts['translated']}, kept {counts['kept']}, "
                          f"left {counts['left']}")
