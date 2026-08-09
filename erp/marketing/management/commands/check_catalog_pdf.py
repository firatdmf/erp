"""Verify the catalog PDF toolchain on whatever machine this runs on.

The point is deployment: WeasyPrint needs Pango as a SYSTEM library, which
pip cannot install, so "it works locally" says nothing about the server. Run
this on Railway after deploying to confirm the box can actually render.

    python manage.py check_catalog_pdf

Exits non-zero if anything essential is missing, so it can gate a release.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check that the catalog PDF renderer works on this machine."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write", metavar="PATH",
            help="Also write the rendered probe PDF here, to eyeball it.",
        )

    def handle(self, *args, **options):
        failures = []

        def ok(label, detail=""):
            self.stdout.write(self.style.SUCCESS(f"  PASS  {label}") + (f"  {detail}" if detail else ""))

        def fail(label, detail=""):
            failures.append(label)
            self.stdout.write(self.style.ERROR(f"  FAIL  {label}") + (f"  {detail}" if detail else ""))

        def warn(label, detail=""):
            self.stdout.write(self.style.WARNING(f"  WARN  {label}") + (f"  {detail}" if detail else ""))

        self.stdout.write("Catalog PDF toolchain\n")

        # 1. The system libraries. This is the check that matters on a new
        #    host: WeasyPrint dlopens Pango at import time, so a missing
        #    apt package surfaces here as an OSError, not at render time.
        try:
            import weasyprint
            ok("weasyprint imports", f"v{weasyprint.__version__} (Pango found)")
        except OSError as error:
            fail("weasyprint imports", f"{error}")
            self.stdout.write(
                "\n        Missing system libraries. Install the apt packages:\n"
                "          libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0\n"
                "        On Railway these belong in railpack.json under deploy.aptPackages.\n"
            )
            raise SystemExit(1)
        except ImportError as error:
            fail("weasyprint imports", f"{error} — is it in requirements.txt?")
            raise SystemExit(1)

        # 2. AVIF: product photos are AVIF on the CDN. Without a decoder they
        #    embed blank, which is silent — the PDF still renders.
        from marketing.catalog_pdf import check_image_support
        if check_image_support():
            ok("AVIF decoding", "product photos will embed")
        else:
            fail("AVIF decoding", "photos will be BLANK — need pillow-avif-plugin or Pillow>=11.3")

        # 3. The bundled font, resolved the way the stylesheet asks for it.
        from django.conf import settings
        from marketing.catalog_pdf import _static_path
        font = _static_path(f"{settings.STATIC_URL}marketing/catalog/fonts/DejaVuSans.ttf")
        if font:
            ok("catalog font resolves", font)
        else:
            fail("catalog font resolves", "run collectstatic? text will fall back to a serif")

        # 4. An end-to-end render, including a non-ASCII glyph — the whole
        #    reason the font is bundled rather than left to the system.
        from marketing.catalog_pdf import read_catalog_css, render_catalog_pdf
        css = read_catalog_css()
        if css:
            ok("stylesheet loads", f"{len(css):,} bytes")
        else:
            fail("stylesheet loads", "catalog_print.css not found")

        try:
            html = (
                f"<style>{css}</style>"
                "<div class='page'><div class='wordmark'>DEMFİRAT ŞĞÜ</div></div>"
            )
            pdf = render_catalog_pdf(html)
            if pdf[:5] == b"%PDF-":
                ok("renders a PDF", f"{len(pdf):,} bytes")
            else:
                fail("renders a PDF", "output is not a PDF")
            if options.get("write"):
                with open(options["write"], "wb") as handle:
                    handle.write(pdf)
                self.stdout.write(f"\n  wrote {options['write']}")
        except Exception as error:
            fail("renders a PDF", f"{type(error).__name__}: {error}")

        # 5. Real data — a catalog with no products renders an empty document.
        try:
            from marketing.catalog_builder import catalog_queryset
            count = catalog_queryset().count()
            (ok if count else warn)("featured products", f"{count} available to put in a catalog")
        except Exception as error:
            warn("featured products", f"could not query: {type(error).__name__}: {error}")

        self.stdout.write("")
        if failures:
            self.stdout.write(self.style.ERROR(f"{len(failures)} check(s) failed: {', '.join(failures)}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("All checks passed — this machine can render catalogs."))
