"""Files hung off any record: a payment's bank slip, an expense's receipt,
an order's customer PO, a purchase's supplier invoice, a contact's contract.

One way for all of them, so a new place gets files by naming its record
and its folder, not by copying steps:

  * the rows are erp.models.Attachment, pointing at their record through
    a generic relation (the record model carries a GenericRelation named
    `attachments`, which also takes the files with it when it is deleted);
  * the bytes live in the Bunny storage zone under the record's app folder
    (Accounting/payments/<id>/, Operating/orders/<id>/, …), never on the
    container's disk, and are read back only through a login-required view;
  * a photo is stored as a DOCUMENT JPEG and a heavy PDF has the photos
    inside it shrunk (erp.image_optimizer, erp.pdf_optimizer); a video
    is re-encoded for erp.video_optimizer's DOCUMENT profile, sound kept,
    after the upload has answered (lighten_video_after_commit);
  * the routes are the record's own: each app wires record_file_views()
    behind the guard that already decides who may open that record, so a
    file opens for exactly the people its record opens for.

The page side is components/attachments_box.html (the box: add, take a
photo, drop, delete) with components/attachments_list.html (the rows).
"""
import logging
import mimetypes
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponseNotAllowed, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

MAX_BYTES = 25 * 1024 * 1024
# A phone video runs 2–5 MB a second as recorded; it is re-encoded to a
# fraction of that after the upload (lighten_video), so what is capped here
# is only what arrives.
VIDEO_MAX_BYTES = 100 * 1024 * 1024

# Extensions that execute rather than describe. The rule is open-minus-
# the-dangerous-ones rather than a whitelist: people attach whatever
# paperwork arrives, and these are the endings that would turn a file list
# into a way to hand a colleague a program. A zipped executable still gets
# through — the accepted cost of accepting archives.
BLOCKED_EXTENSIONS = frozenset({
    # Windows executables and installers
    "exe", "msi", "com", "scr", "pif", "cpl", "msc", "lnk", "reg",
    # Shell and script interpreters
    "bat", "cmd", "sh", "bash", "ps1", "psm1", "vbs", "vbe",
    "js", "jse", "wsf", "wsh", "hta",
    # Packaged applications
    "jar", "apk", "app", "deb", "rpm",
    # Macro-enabled Office documents — the classic mail-borne payload
    "docm", "dotm", "xlsm", "xltm", "xlam", "pptm", "potm", "ppam",
})

# Types the file view renders in the browser. A short allowlist, not "any
# image": an SVG is a document that can carry script, and rendering one
# would run it on our own origin as the signed-in user. Everything else
# downloads.
INLINE_CONTENT_TYPES = frozenset({
    "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp",
})


def validate_attachment_type(file):
    """Refuse the file endings that run instead of open.

    Only the LAST extension is examined, which is the point:
    "invoice.pdf.exe" is an executable wearing a document's name.
    """
    name = getattr(file, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            f".{ext} files cannot be attached — programs and scripts are "
            f"not accepted. Put it in a zip if it really has to travel.")
    return file


def validate_attachment_size(file):
    """Cap an attachment at 25 MB, a video at 100 MB: a signed contract scan
    or a spec sheet routinely runs past the 10 MB product-image limit, and
    half a minute of phone video past 25 MB."""
    if content_type_for(getattr(file, "name", "")).startswith("video/"):
        if file.size > VIDEO_MAX_BYTES:
            raise ValidationError("The maximum size for a video is 100MB")
    elif file.size > MAX_BYTES:
        raise ValidationError("The maximum file size that can be uploaded is 25MB")
    return file


def content_type_for(filename, declared=""):
    """A file's type from its name, not from what the client said.

    A crafted client can declare anything, and trusting it would let a
    caller choose how their file is later served. The extension is not
    proof either, but it is ours to reason about, and the file view only
    renders INLINE_CONTENT_TYPES inline.
    """
    guess, _ = mimetypes.guess_type(filename or "")
    return (guess or declared or "application/octet-stream")[:120]


class AttachmentStorageError(Exception):
    """The file could not be put somewhere it will survive."""


def _store(upload, folder, record):
    """Put an uploaded file where it will survive, under
    `folder`/<record id>/, and say where.

    Returns `(storage_path, local_file)`, exactly one of which is set.

    Bunny, or nothing: MEDIA_ROOT is a container path with no volume, so a
    file written there looks saved and is gone on the next deploy. The
    local disk is used only where it is the intent — a dev box with
    USE_BUNNY_CDN off. In production that setting means the storage is
    misconfigured, and the upload is refused rather than lost later.
    """
    if not getattr(settings, "USE_BUNNY_CDN", False):
        if not settings.DEBUG:
            raise AttachmentStorageError(
                "File storage is not configured on this server, so the "
                "upload was refused rather than saved somewhere it would "
                "be lost. Ask an administrator to check USE_BUNNY_CDN.")
        return "", upload

    from django.utils.crypto import get_random_string
    from marketing.utils.bunny_storage import upload_to_bunny

    # A random prefix, so two uploads of "contract.pdf" onto the same
    # record do not overwrite one another.
    path = f"{folder}/{record.pk}/{get_random_string(8)}_{_safe_name(upload.name)}"
    try:
        upload_to_bunny(upload, path, content_type=getattr(upload, "content_type", None))
    except Exception as exc:
        logger.exception("Bunny upload failed for an attachment")
        raise AttachmentStorageError(
            "Upload failed — the file was not saved. Please try again.") from exc
    return path, None


def _lighter(upload):
    """A photo as a DOCUMENT JPEG, a heavy PDF with its photos shrunk;
    anything else, or anything neither can read, as it came."""
    kind = content_type_for(upload.name)
    if not (kind.startswith("image/") or kind == "application/pdf"):
        return upload
    from django.core.files.uploadedfile import SimpleUploadedFile
    from erp.image_optimizer import DOCUMENT, OptimizedImage, optimize_image
    from erp.pdf_optimizer import OptimizedPdf, optimize_pdf

    optimize = optimize_pdf if kind == "application/pdf" else optimize_image
    smaller = optimize(upload, DOCUMENT)
    if isinstance(smaller, (OptimizedImage, OptimizedPdf)):
        return SimpleUploadedFile(smaller.name, smaller.getvalue(), smaller.content_type)
    return upload


def save_uploads(request, record, folder):
    """Store each file in `request.FILES` as an attachment of `record`,
    under `folder` in the storage zone; returns a complaint per file that
    was not kept. The ones that made it are kept whatever happened to the
    others, because their bytes are already safe."""
    from .models import Attachment

    uploads = request.FILES.getlist("files") or request.FILES.getlist("file")
    skipped = []
    for upload in uploads:
        try:
            validate_attachment_size(upload)
            validate_attachment_type(upload)
        except ValidationError as exc:
            skipped.append(f"{upload.name}: {exc.messages[0]}")
            continue
        upload = _lighter(upload)
        try:
            path, local = _store(upload, folder, record)
        except AttachmentStorageError as exc:
            skipped.append(f"{upload.name}: {exc}")
            continue
        attachment = Attachment.objects.create(
            record=record,
            name=upload.name[:255],
            path=path,
            file=local,
            size=upload.size or 0,
            content_type=content_type_for(upload.name, getattr(upload, "content_type", "")),
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        if path and attachment.content_type.startswith("video/"):
            lighten_video_after_commit(attachment.pk)
    return skipped


def _safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)[-80:].strip("-._")


def lighten_video(attachment_id):
    """Re-encode a video attachment for the DOCUMENT profile (sound kept)
    and store it in place of the original, which is then deleted — the
    file is private, so no cached page still asks for the old path.

    Kept as it came when the encode can't read it or isn't smaller. If the
    attachment was deleted meanwhile, the new file goes too."""
    import os
    import shutil
    import tempfile

    from django.utils.crypto import get_random_string
    from erp import video_optimizer as videos
    from marketing.utils.bunny_storage import delete_from_bunny, download_from_bunny, upload_to_bunny
    from .models import Attachment

    attachment = Attachment.objects.filter(pk=attachment_id).first()
    if attachment is None or not attachment.path:
        return False
    old_path = attachment.path
    work = tempfile.mkdtemp(prefix="attachment_video_")
    try:
        source = os.path.join(work, "source" + os.path.splitext(old_path)[1])
        with download_from_bunny(old_path, stream=True) as response:
            with open(source, "wb") as out:
                for chunk in response.iter_content(1 << 20):
                    out.write(chunk)
        encoded = os.path.join(work, "encoded.mp4")
        if not videos.lighter(source, encoded, videos.DOCUMENT):
            return False

        name = f"{os.path.splitext(attachment.name)[0]}.mp4"[-255:]
        new_path = f"{old_path.rsplit('/', 1)[0]}/{get_random_string(8)}_{_safe_name(name)}"
        with open(encoded, "rb") as f:
            upload_to_bunny(f, new_path, content_type="video/mp4", purge=False)
        changed = Attachment.objects.filter(pk=attachment_id, path=old_path).update(
            path=new_path, name=name, size=os.path.getsize(encoded), content_type="video/mp4")
        delete_from_bunny(old_path if changed else new_path)
        return bool(changed)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def lighten_video_after_commit(attachment_id):
    """lighten_video() once the upload is committed, off the request: an
    encode takes seconds to minutes, which the person uploading needn't
    wait for. Until it lands, the original is what opens."""
    import threading

    from django.db import connection, transaction

    def work():
        try:
            lighten_video(attachment_id)
        except Exception:
            logger.exception("Could not re-encode video attachment %s", attachment_id)
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())


def files_of(record):
    """`record`'s attachments, newest first."""
    from django.contrib.contenttypes.models import ContentType
    from .models import Attachment

    return (Attachment.objects
            .filter(record_type=ContentType.objects.get_for_model(record), record_id=record.pk)
            .select_related("uploaded_by").order_by("-uploaded_at", "-id"))


def attachment_response(attachment):
    """The file behind `attachment`, for a reader already let in."""
    inline = attachment.content_type in INLINE_CONTENT_TYPES
    filename = attachment.name.replace('"', "")

    if attachment.path:
        from marketing.utils.bunny_storage import download_from_bunny
        try:
            upstream = download_from_bunny(attachment.path)
        except Exception:
            logger.exception("Could not read attachment %s back from Bunny", attachment.pk)
            raise Http404("This file could not be read from storage")
        response = StreamingHttpResponse(
            upstream.iter_content(chunk_size=64 * 1024),
            content_type=attachment.content_type or "application/octet-stream")
        if attachment.size:
            response["Content-Length"] = attachment.size
    elif attachment.file:
        response = FileResponse(
            attachment.file.open("rb"),
            content_type=attachment.content_type or "application/octet-stream")
    else:
        raise Http404("This attachment has no file behind it")

    response["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    # Never let a shared cache hold a document behind a login.
    response["Cache-Control"] = "private, max-age=0, no-store"
    # And never let the browser decide a text file is really HTML.
    response["X-Content-Type-Options"] = "nosniff"
    return response


def record_file_views(folder, record_of, url_name):
    """The three views behind a record's files box, for `urls.py` to wire
    behind the guard of the record's own pages:

        files(request, pk)               GET the list, POST `files` then the list
        file(request, pk, doc_pk)        the file itself
        delete(request, pk, doc_pk)      POST: remove it, then the list

    `record_of(pk)` finds the record (404 when it is not one); `folder` is
    its app's folder in the storage zone; `url_name` is the name the list
    route is wired under, with `_file` and `_delete` after it for the
    other two, which the rows link to.
    """

    def answer(request, record, errors=()):
        html = render_to_string("components/attachments_list.html", {
            "documents": files_of(record), "record": record, "url_name": url_name,
        }, request=request)
        return JsonResponse({"success": not errors, "html": html, "errors": list(errors)})

    def document(record, doc_pk):
        return get_object_or_404(files_of(record), pk=doc_pk)

    @login_required
    def files(request, pk):
        record = record_of(pk)
        if request.method == "POST":
            return answer(request, record, save_uploads(request, record, folder))
        return answer(request, record)

    @login_required
    def file(request, pk, doc_pk):
        return attachment_response(document(record_of(pk), doc_pk))

    @login_required
    def delete(request, pk, doc_pk):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        record = record_of(pk)
        document(record, doc_pk).delete()
        return answer(request, record)

    return files, file, delete
