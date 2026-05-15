"""Convert {% trans "...\"..." %} (double-quoted with escaped inner quotes) to
   {% trans '..."...' %} (single-quoted outer, plain double quotes inside).
   Django's smart_split can't reliably handle backslash-escaped quotes in trans
   tags, so we sidestep by switching the outer quote style.
"""
import re
from pathlib import Path

path = Path("current_account/templates/current_account/help.html")
text = path.read_text(encoding="utf-8")

# Pattern: {% trans "..." %} where the content has \"
pattern = re.compile(r'''\{%\s*trans\s+"((?:[^"\\]|\\.)*)"\s*%\}''')


def fix(match):
    raw = match.group(1)
    if r'\"' not in raw:
        return match.group(0)  # leave alone
    # Unescape \"  →  "
    inner = raw.replace(r'\"', '"')
    return "{% trans '" + inner + "' %}"


new_text = pattern.sub(fix, text)
if new_text != text:
    path.write_text(new_text, encoding="utf-8")
    print("Updated help.html")
else:
    print("No changes needed")
