"""Fail on Django template comments that would print on the page.

The system check reports these as warnings on every runserver; this command
exits non-zero so a git hook or CI can stop them getting in at all.

    python manage.py lint_templates            # whole project
    python manage.py lint_templates a.html b.html   # only these (for a hook)
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from erp.template_lint import find_multiline_comments, _unterminated


class Command(BaseCommand):
    help = "Find multi-line {# #} template comments, which render as page text."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*",
                            help="Specific files to check. Defaults to the whole project.")

    def handle(self, *args, **options):
        paths = options["paths"]
        if paths:
            hits = []
            for p in paths:
                if not p.endswith(".html"):
                    continue
                try:
                    with open(p, encoding="utf-8", errors="ignore") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                hits += [(p, n, l.strip()) for n, l in enumerate(lines, 1)
                         if _unterminated(l)]
        else:
            hits = find_multiline_comments(settings.BASE_DIR)

        if not hits:
            self.stdout.write(self.style.SUCCESS("No multi-line {# #} comments."))
            return

        for path, n, line in hits:
            self.stdout.write(self.style.ERROR(f"{path}:{n}: {line}"))
        self.stdout.write("")
        self.stdout.write("{# #} is single-line only — a comment spanning lines is "
                          "printed on the page, delimiters and all.")
        self.stdout.write("Use {% comment %} … {% endcomment %} instead.")
        raise SystemExit(1)
