"""A whole column of barcodes, pasted in one go.

Barcodes arrive copied out of an Excel column, which means one per line.
That single fact decides most of this:

  * The field is a <textarea>, not an <input>. Pasting text with newlines
    into an <input> does not fail loudly — the browser strips or collapses
    them, so "KZL001\\nKZL002" becomes one code that matches nothing, and
    the operator is told the barcode does not exist.
  * Enter still submits, because a hardware scanner sends one after every
    read and that path must keep working exactly as it did. Shift+Enter
    is how a line gets typed by hand.
  * The codes are added STRICTLY one at a time. Each one can create an
    order line, and two in flight for the same new SKU would both look,
    both find no line yet, and both add the product.

Failures are collected rather than toasted. Twenty codes would otherwise
raise twenty toasts, each replaced before it could be read, and which
codes did NOT go on is the entire point of pasting a list.

Run with:
    python manage.py test operating.test_order_bulk_barcode
"""
import re

from django.test import SimpleTestCase

FORM = "operating/templates/operating/partials/create_order_form.html"


def read_form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def body_of(src, signature):
    start = src.index(signature)
    depth = 0
    for j in range(src.index("{", start), len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start:j + 1]
    raise AssertionError(f"never closed: {signature}")


class ThePasteBoxTakesNewlines(SimpleTestCase):
    def test_the_field_is_a_textarea(self):
        """An <input> would mangle the paste silently."""
        form = read_form()
        self.assertIn('<textarea id="co-global-bc"', form)
        self.assertNotIn('<input type="text" id="co-global-bc"', form)

    def test_enter_still_submits_for_the_scanner(self):
        form = read_form()
        m = re.search(r'<textarea id="co-global-bc".*?</textarea>', form, re.S)
        self.assertIsNotNone(m)
        field = m.group(0)
        # Enter submits; Shift+Enter is left alone so a line can be typed.
        self.assertIn("event.key==='Enter'", field)
        self.assertIn("!event.shiftKey", field)
        self.assertIn("coScanAdd()", field)

    def test_the_splitter_handles_every_separator_a_paste_brings(self):
        """Mirrors the regex in the template so the intent is pinned even
        though the split itself runs in the browser."""
        pattern = re.search(r"\.split\(/\[([^\]]+)\]\+/\)", read_form())
        self.assertIsNotNone(pattern, "the barcode splitter is gone")
        chars = pattern.group(1)
        for needed in (r"\s", ",", ";"):
            self.assertIn(needed, chars)


class OneAtATime(SimpleTestCase):
    def test_the_next_code_waits_for_the_one_before_it(self):
        """The recursion happens INSIDE .then — that is what serialises
        it. A loop calling step() for every index would fire them all at
        once and race to create the same line twice."""
        batch = body_of(read_form(), "function coAddBarcodeList(codes)")
        self.assertRegex(batch, r"\.then\(function \(ok\) \{[\s\S]*?step\(i \+ 1\)")
        self.assertNotRegex(batch, r"codes\.forEach|for \(var i = 0")

    def test_a_single_code_keeps_its_old_behaviour(self):
        """One barcode is the common case and must not grow a results box
        or lose its toast."""
        add = body_of(read_form(), "window.coScanAdd = function ()")
        self.assertIn("codes.length === 1", add)
        self.assertRegex(add, r"coScanAddByBarcode\(codes\[0\]\)")


class TheBatchTakesTheToasts(SimpleTestCase):
    """showToast is a function declaration inside the form's IIFE, not a
    property of window — so a batch cannot mute it by reassigning
    window.showToast, which is exactly the trap this was written into.
    The sink is a variable the function itself checks."""

    def test_show_toast_consults_the_sink(self):
        toast = body_of(read_form(), "function showToast(msg, type)")
        self.assertIn("coToastSink", toast)
        self.assertRegex(toast, r"if \(coToastSink\) \{[^}]*return")

    def test_the_sink_is_never_left_installed(self):
        """Left in place it would silence every message on the form for
        the rest of the page's life."""
        batch = body_of(read_form(), "function coAddBarcodeList(codes)")
        self.assertIn("coToastSink = null", body_of(batch, "function finish()"))
        self.assertRegex(batch, r"catch \(e\) \{ coToastSink = null; throw e; \}")

    def test_the_failures_are_reported_with_their_reasons(self):
        batch = body_of(read_form(), "function coAddBarcodeList(codes)")
        self.assertIn("failed.map(", batch)
        self.assertIn("esc(f.why)", batch)
        self.assertIn("esc(f.code)", batch)
