"""A camera read: checked, then added, one label at a time.

Since 2026-11-19 the order form adds a good read straight away
(addOnRead), as the packing page always has: Muhammed found the extra
confirm tap slowed picking. What stays is below — the loop stops on each
read, so one label is one add, and the order's own check runs first.

The history that shaped it:

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


CAMERA = "erp/static/erp/js/barcode_camera.js"


def read_camera():
    """The one camera reader every page shares."""
    with open(CAMERA, encoding="utf-8") as fh:
        return fh.read()


class TheReadWaitsToBeConfirmed(SimpleTestCase):
    def test_the_order_form_uses_the_shared_reader(self):
        form = read_form()
        self.assertIn("window.NejumCamera.open(", form)
        # No copy of its own: one reader, one place to fix it.
        self.assertNotIn("zxing", form)
        self.assertNotIn("getUserMedia", form)

    def test_a_decode_stops_and_is_checked_before_anything_is_added(self):
        """One label is one read, and the page's lookup — already on the
        order, another book, nothing left — runs before the add."""
        cam = read_camera()
        # The popup's handler for a read: stop reading, then handle it.
        popup = cam[cam.index("rd = reader({"):]
        handler = popup[popup.index("onCode: function (code) {"):]
        handler = handler[:handler.index("},")]
        self.assertIn("rd.pause()", handler)
        self.assertIn("camRead(code)", handler)
        self.assertNotIn("opts.confirm", handler)
        read = body_of(cam, "function camRead(code)")
        self.assertLess(read.index("opts.lookup"), read.index("confirmPending("))
        self.assertIn("if (!r.ok)", read)

    def test_the_order_adds_on_a_good_read(self):
        opened = body_of(read_form(), "window.coOpenRollCamera = function (i)")
        self.assertIn("addOnRead: true", opened)

    def test_confirming_goes_through_the_ordinary_add_path(self):
        """Book adoption, the clash guard and the availability check live
        in the add functions; the camera must not grow a second copy."""
        opened = body_of(read_form(), "window.coOpenRollCamera = function (i)")
        self.assertRegex(opened, r"window\.coScanAddByBarcode\(code[,)]")
        self.assertIn("window.coAddRoll(camTargetIndex, code)", opened)
        confirm = body_of(read_camera(), "function confirmPending(found)")
        self.assertIn("opts.confirm(code)", confirm)

    def test_a_code_already_on_the_order_is_answered_before_asking(self):
        opened = body_of(read_form(), "window.coOpenRollCamera = function (i)")
        self.assertIn("Already on this order", opened)

    def test_the_panel_offers_another_scan(self):
        cam = read_camera()
        self.assertIn("data-nj-cam=", cam)
        again = body_of(cam, "function again()")
        # Resumes the paused reader on the live stream. Stopping the tracks
        # and re-asking for the camera is the slow path, and on iOS it
        # prompts again.
        self.assertIn("rd.resume()", again)
        self.assertNotIn("rearStream", again)
        resume = cam[cam.index("resume: function () {"):cam.index("stop: function () {")]
        self.assertIn("if (stream && video.srcObject)", resume)

    def test_reopening_never_lands_on_the_last_reads_panel(self):
        opened = body_of(read_camera(), "function open(options)")
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
    """The reader opens as a modal over everything. Inline, it was a 280px
    strip competing for the little height the create sidebar has left."""

    def test_it_is_an_overlay_with_a_way_out(self):
        cam = read_camera()
        self.assertIn("nj-cam-overlay", cam)
        self.assertIn("nj-cam-shell", cam)
        self.assertIn("nj-cam-close", cam)
        self.assertNotIn("height:280px", read_form())

    def test_it_sits_above_the_create_sidebar(self):
        """The order form is loaded INTO .sidebar-overlay. A popup that does
        not out-stack it opens behind the sidebar, where the camera runs
        and nothing is visible — so this reads both numbers rather than
        trusting one."""
        with open(BASE_CSS, encoding="utf-8") as fh:
            base = fh.read()
        sidebar = re.search(r"\.sidebar-overlay\s*\{[^}]*?z-index:\s*(\d+)", base, re.S)
        self.assertIsNotNone(sidebar, "could not read .sidebar-overlay's z-index")
        popup = re.search(r"\.nj-cam-overlay\{[^}]*?z-index:(\d+)", read_camera(), re.S)
        self.assertIsNotNone(popup, "could not read .nj-cam-overlay's z-index")
        self.assertGreater(int(popup.group(1)), int(sidebar.group(1)))

    def test_opening_and_closing_toggle_the_same_class(self):
        cam = read_camera()
        self.assertIn("el.classList.add('show')", body_of(cam, "function open(options)"))
        self.assertIn("el.classList.remove('show')", body_of(cam, "function close()"))

    def test_closing_gives_back_the_scroll_it_took(self):
        """Not `overflow = ''`: the create sidebar has already hidden the
        body's scrollbar, and clearing it here would let the page behind
        a still-open sidebar scroll."""
        cam = read_camera()
        self.assertIn("camPrevOverflow = document.body.style.overflow", body_of(cam, "function open(options)"))
        self.assertIn("document.body.style.overflow = camPrevOverflow", body_of(cam, "function close()"))

    def test_escape_closes_it(self):
        self.assertRegex(read_camera(), r"e\.key === 'Escape'[\s\S]{0,200}close\(\)")

    def test_every_page_has_it(self):
        with open("erp/templates/base.html", encoding="utf-8") as fh:
            self.assertIn('{% include "components/barcode_camera.html" %}', fh.read())


class OneReaderForEveryPage(SimpleTestCase):
    """No page carries its own camera or decoder (Muhammed, 2026-11-17:
    "so we won't have duplicates when it comes to barcode scanning")."""

    PAGES = (
        "operating/templates/operating/partials/create_order_form.html",
        "operating/templates/operating/order_pack_scan.html",
        "operating/templates/operating/warehouse_detail.html",
        "accounting/templates/accounts/goods_receipt_form.html",
    )

    def test_no_page_has_a_copy(self):
        for page in self.PAGES:
            with self.subTest(page=page), open(page, encoding="utf-8") as fh:
                src = fh.read()
                self.assertNotIn("zxing", src)
                self.assertNotIn("getUserMedia", src)
                self.assertIn("NejumCamera", src)
