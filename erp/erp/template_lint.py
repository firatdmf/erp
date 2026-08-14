"""Catch Django template comments that silently print on the page.

`{# … #}` is SINGLE-LINE only. Spread one across lines and the parser never
sees a comment at all: the whole thing, delimiters included, is emitted as
page text. It looks perfectly correct in an editor, which is why it keeps
happening — nine have reached this codebase so far, one of them inside an
invoice row template, so it printed once per line item.

`{% comment %} … {% endcomment %}` is the multi-line form.

Used from two places: a Django system check (visible on runserver/check) and
the `lint_templates` command (exits non-zero, for a git hook or CI).
"""
from pathlib import Path

# Directories that are not ours to lint.
SKIP_DIRS = {
    "vir_env", "venv", ".venv", "node_modules", "__pycache__",
    ".git", "staticfiles", "static_root", "media", "site-packages",
}


def _unterminated(line):
    """True if `line` opens a {# comment that it never closes.

    Compares the LAST opener with the last closer, so a line holding a
    complete comment followed by a fresh opener is still caught.
    """
    return line.rfind("{#") > line.rfind("#}")


def find_multiline_comments(root):
    """Return [(path, line_number, text), …] for every unterminated {#.

    Lines inside {% verbatim %} are skipped: their whole point is to emit
    template syntax literally, so a bare {# there is deliberate.
    """
    hits = []
    root = Path(root)
    for path in root.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "{#" not in text:
            continue
        verbatim = 0
        for n, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if "{% verbatim" in lowered:
                verbatim += 1
            if "{% endverbatim" in lowered:
                verbatim = max(0, verbatim - 1)
                continue
            if verbatim:
                continue
            if _unterminated(line):
                hits.append((str(path), n, line.strip()))
    return hits


def check_template_comments(app_configs=None, **kwargs):
    """Django system check. WARNING, not ERROR, on purpose: a leaked comment
    is ugly, never dangerous, and blocking `migrate` (and so a deploy) over
    cosmetics would be worse than the bug. The `lint_templates` command is
    the one that fails hard, at commit time, where stopping is cheap."""
    from django.conf import settings
    from django.core.checks import Warning as CheckWarning

    hits = find_multiline_comments(settings.BASE_DIR)
    return [
        CheckWarning(
            f"{path}:{n} — multi-line {{# #}} comment renders as page text.",
            hint=("{# #} is single-line only. Use "
                  "{% comment %} … {% endcomment %} instead."),
            obj=f"{path}:{n}",
            id="templates.W001",
        )
        for path, n, _line in hits
    ]
