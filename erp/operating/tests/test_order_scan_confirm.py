"""A camera read is a question, not an instruction.

The order form's barcode camera used to add on the decode itself: the
reader fires on whatever crosses the frame — the next roll on the shelf,
the label still in the operator's hand — so stock nobody chose joined the
order, and the only way to notice was to re-read the card. It now stops
on the first read, says what the code is, and changes the order only on a
confirm; afterwards it offers another scan. Same shape as the warehouse
page's "Find by barcode".

The seam that makes it work is the return value. coAddRoll and
coScanAddByBarcode were written for callers that ignored them, so several
of their exits simply returned. The confirm panel reads the answer to
choose between "Added to the order" and "Could not be added", and a bare
`return` is `undefined` — falsy — so a stock item that DID land would be
reported as a failure. Every exit therefore has to carry a verdict.

Run with:
    python manage.py test operating.test_order_scan_confirm
"""
import re

from django.test import SimpleTestCase

FORM = "operating/templates/operating/partials/create_order_form.html"
BASE_CSS = "erp/static/erp/css/base.css"


def read_form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def body_of(src, signature):
    """The text of one function, from its signature to its closing brace."""
    start = src.index(signature)
    depth, i = 0, src.index("{", start)
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start:j + 1]
    raise AssertionError(f"never closed: {signature}")


class TheReadWaitsToBeConfirmed(SimpleTestCase):
    def test_the_camera_has_somewhere_to_ask(self):
        form = read_form()
        self.assertIn('id="co-roll-cam-stage"', form)
        self.assertIn('id="co-roll-cam-confirm"', form)

    def test_a_decode_stops_and_asks_instead_of_adding(self):
        """The whole point: onDecode must not reach an add path."""
        decode = body_of(read_form(), "function onDecode(code)")
        self.assertIn("camPause()", decode)
        self.assertIn("camRead(code)", decode)
        self.assertNotIn("coScanAddByBarcode", decode)
        self.assertNotIn("coAddRoll", decode)

    def test_confirming_goes_through_the_ordinary_add_path(self):
        """Book adoption, the clash guard and the availability check live
        in the add functions; the panel must not grow a second copy."""
        confirm = body_of(read_form(), "window.coRollCamConfirm = function ()")
        self.assertRegex(confirm, r"window\.coScanAddByBarcode\(code[,)]")
        self.assertIn("window.coAddRoll(camTargetIndex, code)", confirm)

    def test_the_panel_offers_another_scan(self):
        form = read_form()
        self.assertIn("coRollCamAgain()", form)
        again = body_of(form, "window.coRollCamAgain = function ()")
        # Resumes the paused loop on the live stream. Stopping the tracks
        # and re-asking for the camera is the slow path, and on iOS it
        # prompts again.
        self.assertIn("camLoop()", again)
        self.assertNotIn("getRearStream", again)
        self.assertNotIn("t.stop()", again)

    def test_reopening_never_lands_on_the_last_reads_panel(self):
        opened = body_of(read_form(), "window.coOpenRollCamera = function (i)")
        self.assertIn("camStage()", opened)
        self.assertIn("camPending = ''", opened)


class EveryExitCarriesAVerdict(SimpleTestCase):
    """Pins the seam rather than either side of it.

    The confirm panel branches on what these two resolve to. A bare
    `return;` anywhere in them is `undefined`, which reads as failure —
    the stock item would join the order while the panel said it could
    not be added.
    """

    def test_the_add_functions_never_return_nothing(self):
        form = read_form()
        # Named without their parameter lists: what matters is the exit
        # values, and pinning the arguments made this fail on a rename.
        for signature in ("window.coAddRoll = function (",
                          "window.coScanAddByBarcode = function ("):
            body = body_of(form, signature)
            bare = re.findall(r"\breturn\s*;", body)
            self.assertEqual(
                bare, [],
                f"{signature.split(' =')[0]} has {len(bare)} bare return(s); "
                f"the scan confirm panel reads the resolved value and would "
                f"report a successful add as a failure.")

    def test_they_hand_back_a_promise_the_panel_can_read(self):
        form = read_form()
        add = body_of(form, "window.coAddRoll = function (")
        self.assertIn("return Promise.resolve(true)", add)
        self.assertIn("return Promise.resolve(false)", add)
        self.assertIn("return fetch(", add)
        glob = body_of(form, "window.coScanAddByBarcode = function (")
        self.assertIn("return fetch(", glob)


class TheScannerIsAPopup(SimpleTestCase):
    """The reader opens as a modal, the same one the warehouse page's
    "Find by barcode" uses. Inline, it was a 280px strip competing for
    the little height the create sidebar has left."""

    def test_it_is_an_overlay_with_a_way_out(self):
        form = read_form()
        self.assertIn('class="co-cam-overlay" id="co-roll-cam-overlay"', form)
        self.assertIn("co-cam-shell", form)
        self.assertIn("co-cam-close", form)
        # The old inline strip is gone, not merely hidden.
        self.assertNotIn("height:280px", form)

    def test_it_sits_above_the_create_sidebar(self):
        """The form is loaded INTO .sidebar-overlay. A popup that does
        not out-stack it opens behind the sidebar, where the camera runs
        and nothing is visible — so this reads both numbers rather than
        trusting one."""
        with open(BASE_CSS, encoding="utf-8") as fh:
            base = fh.read()
        sidebar = re.search(r"\.sidebar-overlay\s*\{[^}]*?z-index:\s*(\d+)", base, re.S)
        self.assertIsNotNone(sidebar, "could not read .sidebar-overlay's z-index")
        popup = re.search(r"\.co-cam-overlay\{[^}]*?z-index:(\d+)", read_form(), re.S)
        self.assertIsNotNone(popup, "could not read .co-cam-overlay's z-index")
        self.assertGreater(int(popup.group(1)), int(sidebar.group(1)))

    def test_opening_and_closing_toggle_the_same_class(self):
        form = read_form()
        opened = body_of(form, "window.coOpenRollCamera = function (i)")
        closed = body_of(form, "window.coCloseRollCamera = function ()")
        self.assertIn("camEl.classList.add('show')", opened)
        self.assertIn("camEl.classList.remove('show')", closed)

    def test_closing_gives_back_the_scroll_it_took(self):
        """Not `overflow = ''`: the create sidebar has already hidden the
        body's scrollbar, and clearing it here would let the page behind
        a still-open sidebar scroll."""
        form = read_form()
        opened = body_of(form, "window.coOpenRollCamera = function (i)")
        closed = body_of(form, "window.coCloseRollCamera = function ()")
        self.assertIn("camPrevOverflow = document.body.style.overflow", opened)
        self.assertIn("document.body.style.overflow = camPrevOverflow", closed)

    def test_escape_closes_it(self):
        self.assertRegex(
            read_form(),
            r"e\.key === 'Escape'[\s\S]{0,200}coCloseRollCamera\(\)")
