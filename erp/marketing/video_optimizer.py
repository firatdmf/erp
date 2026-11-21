"""Product videos made light for the storefront.

A phone clip arrives at 4–10 Mbps with a sound track; the storefront shows
it muted in a box a few hundred pixels wide. So every product video is
re-encoded once, after it is saved, for erp.video_optimizer's WEB profile
(720p, 30 fps, no sound — the numbers live there).

If the encode comes out bigger, the original is kept. Either way the
still frame the storefront shows before playing is taken from the file
that stays, and the row is marked done (ProductFile.video_optimized_at).

The encoded file gets a new name in the same folder, and the old one is
retired the way a moved photo is (product_images.RETIRE_DAYS), since cached
pages and feeds still ask for it a while.

Nothing waits for this: an upload or a product save sets it off after the
commit (optimize_after_commit), and the hourly housekeeping catches
whatever a restart cut short (optimize_pending with no product).
"""
import os
import secrets
import shutil
import tempfile
import threading
from datetime import timedelta

from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone

from erp import video_optimizer as videos
from erp.video_optimizer import FfmpegMissing, first_frame

from . import product_images

_LOCK_SECONDS = videos.ENCODE_TIMEOUT + 60


def encode(source, target):
    """`source` re-encoded for the storefront into `target`."""
    return videos.encode(source, target, videos.WEB)


def pending(product_id=None):
    """The video URLs on our CDN not yet made light, oldest first."""
    from .models import ProductFile

    rows = ProductFile.everywhere.filter(
        file_type="video", video_optimized_at__isnull=True,
        file_url__startswith=product_images.cdn_url(""),
    )
    if product_id is not None:
        rows = rows.filter(product_id=product_id)
    return list(dict.fromkeys(rows.order_by("pk").values_list("file_url", flat=True)))


def optimize(url):
    """Make the video at `url` light, for every row showing it. Returns the
    URL the rows show afterwards, or None when nothing was done (another
    run has it, it moved meanwhile, or the download failed)."""
    from .models import ProductFile, RetiredCdnFile
    from .utils.bunny_storage import delete_from_bunny, download_from_bunny, upload_to_bunny

    lock = f"marketing.video_optimizer:{url}"
    if not cache.add(lock, True, _LOCK_SECONDS):
        return None
    work = tempfile.mkdtemp(prefix="video_")
    uploaded = []
    try:
        row = (ProductFile.everywhere.filter(file_url=url, video_optimized_at__isnull=True)
               .select_related("product").first())
        path = product_images.storage_path(url)
        if row is None or not path:
            return None
        folder, name = path.rsplit("/", 1)

        source = os.path.join(work, "source" + (os.path.splitext(name)[1] or ".mp4"))
        with download_from_bunny(path, stream=True) as response:
            response.raise_for_status()
            with open(source, "wb") as out:
                for chunk in response.iter_content(1 << 20):
                    out.write(chunk)

        encoded = os.path.join(work, "encoded.mp4")
        lighter = encode(source, encoded) and os.path.getsize(encoded) < os.path.getsize(source)
        kept = encoded if lighter else source

        new_url = url
        stem = os.path.splitext(name)[0]
        if lighter:
            new_name = product_images.new_file_name(row.product, ".mp4")
            stem = os.path.splitext(new_name)[0]
            with open(encoded, "rb") as f:
                new_url = upload_to_bunny(f, f"{folder}/{new_name}", purge=False)
            uploaded.append(new_url)

        thumbnail = None
        frame = os.path.join(work, "frame.jpg")
        if first_frame(kept, frame):
            thumb_name = f"{stem}-{secrets.token_hex(3)}-thumb.jpg"
            with open(frame, "rb") as f:
                thumbnail = upload_to_bunny(f, f"{folder}/{thumb_name}", purge=False)
            uploaded.append(thumbnail)

        with transaction.atomic():
            rows = ProductFile.everywhere.filter(file_url=url, video_optimized_at__isnull=True)
            old_thumbnails = set(rows.exclude(video_thumbnail__isnull=True)
                                 .exclude(video_thumbnail="")
                                 .values_list("video_thumbnail", flat=True))
            changes = {"file_url": new_url, "video_optimized_at": timezone.now()}
            if thumbnail:
                changes["video_thumbnail"] = thumbnail
            if not rows.update(**changes):
                raise _Superseded()
            retire = {u for u in old_thumbnails if thumbnail and u != thumbnail}
            if new_url != url:
                retire.add(url)
            for old in retire:
                RetiredCdnFile.objects.update_or_create(
                    url=old, defaults={"delete_after": timezone.now()
                                       + timedelta(days=product_images.RETIRE_DAYS)})
        uploaded.clear()
        return new_url
    except _Superseded:
        return None
    finally:
        # Files of a run that didn't land (an error, or the rows moved on
        # meanwhile) were never shown anywhere.
        for leftover in uploaded:
            try:
                delete_from_bunny(leftover)
            except Exception as exc:
                print(f"[video_optimizer] could not remove {leftover}: {exc}")
        shutil.rmtree(work, ignore_errors=True)
        cache.delete(lock)


class _Superseded(Exception):
    pass


def optimize_pending(product_id=None):
    """optimize() each pending video of the product (all, with none).
    Returns how many were done. Stops early when ffmpeg is missing."""
    done = 0
    for url in pending(product_id):
        try:
            if optimize(url):
                done += 1
        except FfmpegMissing:
            print("[video_optimizer] ffmpeg is not installed; videos wait")
            break
        except Exception as exc:
            print(f"[video_optimizer] could not optimize {url}: {exc}")
    return done


def optimize_after_commit(product_id):
    """optimize_pending(product_id) once the save is committed, off the
    request."""
    def work():
        try:
            optimize_pending(product_id)
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())
