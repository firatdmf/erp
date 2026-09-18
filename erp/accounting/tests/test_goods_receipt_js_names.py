# to run this test, use the command:
# python manage.py test accounting.tests.test_goods_receipt_js_names

"""Every np* function the goods-receipt page calls is one it defines.

The page is one long inline script, so a call to a name that does not
exist is not a quiet no-op: it throws at boot and the whole form stops
setting itself up — no account, no product cards, no barcodes. It looks
like "the form doesn't load my account" rather than like a typo, which is
exactly how one shipped (npBcInputs for npBcRows).

A parser would be overkill here; the names are all spelled `npFoo`, so
collecting the definitions and the call sites as text catches the typo
class this exists for.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE = (Path(settings.BASE_DIR) / "accounting" / "templates" / "accounts"
            / "goods_receipt_form.html")

# Defined as `function npFoo(`, `window.npFoo = function`, `let npFoo =`,
# `const npFoo =` — every shape the page uses.
DEFINED = re.compile(r"(?:function\s+(np[A-Za-z0-9_]*)\s*\(|"
                     r"(?:window\.)?(np[A-Za-z0-9_]*)\s*=\s*(?:function|\(|async))")
CALLED = re.compile(r"\b(np[A-Za-z0-9_]*)\s*\(")
# Not calls: the definitions' own names are caught by DEFINED, and these
# are words that merely start with "np".
NOT_FUNCTIONS = {"npLoading"}


class GoodsReceiptJsNamesTest(SimpleTestCase):
    def test_every_np_call_has_a_definition(self):
        source = TEMPLATE.read_text()
        defined = {m.group(1) or m.group(2) for m in DEFINED.finditer(source)}
        called = {m.group(1) for m in CALLED.finditer(source)} - NOT_FUNCTIONS
        missing = sorted(called - defined)
        self.assertEqual(missing, [], "called but never defined: " + ", ".join(missing))
