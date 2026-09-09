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
        for signature in ("window.coAddRoll = function (i, barcodeOverride)",
                          "window.coScanAddByBarcode = function (barcode, fromCamera)"):
            body = body_of(form, signature)
            bare = re.findall(r"\breturn\s*;", body)
            self.assertEqual(
                bare, [],
                f"{signature.split(' =')[0]} has {len(bare)} bare return(s); "
                f"the scan confirm panel reads the resolved value and would "
                f"report a successful add as a failure.")

    def test_they_hand_back_a_promise_the_panel_can_read(self):
        form = read_form()
        add = body_of(form, "window.coAddRoll = function (i, barcodeOverride)")
        self.assertIn("return Promise.resolve(true)", add)
        self.assertIn("return Promise.resolve(false)", add)
        self.assertIn("return fetch(", add)
        glob = body_of(form,
                       "window.coScanAddByBarcode = function (barcode, fromCamera)")
        self.assertIn("return fetch(", glob)
