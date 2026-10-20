"""Where a product's photos live on the CDN, what they are called, and
what they say to someone who cannot see them.

A photo is stored once and named once:

    media/product_images/K12767/florenza-3fa9c2.avif               the product's
    media/product_images/K12767/K12767.G141/florenza-7c21e0.avif   one variant's

The name is the product's title and a random suffix, fixed at upload. The
suffix is what keeps two uploads from landing on one path (the CDN would
overwrite the first); the title is the little a file name tells a search
engine. Describing the photo is the alt text's job (see alt_texts), which is
built from the product as it is now, so it never goes stale.

The folder follows who uses the photo. A variant's editor picks its photos
from the product's shared pool, and one file can serve several variants (a
row each, sharing the URL). So a photo used by exactly one variant lives in
that variant's folder; one shared by several, or by none, lives in the
product's. When that changes, or a SKU does, the file moves (relocate). The
database is what knows who uses a photo; the folder only mirrors it.

A move gives the photo a new URL, and the old one is still held for a while
by cached storefront pages (5 min), the Meta feed (1 h) and search engines.
So the old file is kept RETIRE_DAYS before it is deleted, and a folder is
removed only once a listing shows it empty, never with what is in it.

The product page moves a product's photos after each save. Everything else
— a SKU renamed by a script, an expired file — is caught by an hourly
sweep the storefront's own calls set off (housekeep_now_and_then).

Only paths in this layout are ever moved. Older uploads
(`product_<sku>/variant_<sku>/…`) keep their URLs.
"""
import re
import secrets
import threading
import unicodedata
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

ROOT = "media/product_images"
TEMP_ROOT = "media/temp_product_files"
RETIRE_DAYS = 7
TITLE_MAX = 60

# The storefront's languages (Polish is switched off).
ALT_LANGUAGES = ("en", "tr", "ru")

# What a value says when it says nothing about the photo.
_NOTHING = {"", "none", "no"}

_CYRILLIC = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o",
     "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e",
     "yu", "ya"],
))
# The letters a decomposition leaves behind: Turkish dotless i has no plain
# base to fall back to, so it would vanish ("Kızılırmak" → "kzlrmak").
_SPECIAL = {"ı": "i", "İ": "I", "ß": "ss", "æ": "ae", "Æ": "AE", "ø": "o", "Ø": "O"}


def _plain_letters(text):
    """`text` in plain ASCII letters: "Şömine Perde" → "Somine Perde",
    "Флоренция" → "Florentsiya"."""
    out = []
    for ch in str(text or ""):
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        elif ch.lower() in _CYRILLIC:
            latin = _CYRILLIC[ch.lower()]
            out.append(latin.capitalize() if ch.isupper() else latin)
        else:
            out.append(ch)
    decomposed = unicodedata.normalize("NFKD", "".join(out))
    return decomposed.encode("ascii", "ignore").decode("ascii")


def sku_segment(sku):
    """A SKU as a folder name: its own case and dots kept ("K12767.G141"),
    anything a path cannot carry turned into a hyphen."""
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", _plain_letters(sku)).strip("-.")
    return text


def title_slug(title):
    """A title as the start of a file name: "Grek Pilise" → "grek-pilise"."""
    text = re.sub(r"[^a-z0-9]+", "-", _plain_letters(title).lower()).strip("-")
    return text[:TITLE_MAX].rstrip("-")


def new_file_name(product, extension):
    """A fresh name for one upload of `product`'s: "florenza-3fa9c2.avif"."""
    stem = title_slug(getattr(product, "title", "")) or "image"
    return f"{stem}-{secrets.token_hex(3)}{extension.lower()}"


def _folder(product_id, product_sku, variant_sku=""):
    folder = f"{ROOT}/{sku_segment(product_sku) or product_id}"
    segment = sku_segment(variant_sku)
    return f"{folder}/{segment}" if segment else folder


def product_folder(product):
    return _folder(product.pk, product.sku)


def folder_for(product, variant=None):
    """Where a photo of `product` used by `variant` alone lives (by none, or
    by several: pass no variant). A variant with no usable SKU has no folder
    of its own."""
    return _folder(product.pk, product.sku, variant.variant_sku if variant is not None else "")


def storage_path(url):
    """The CDN path of a URL on our CDN ("media/…"), else None."""
    cdn = (getattr(settings, "BUNNY_CDN_URL", "") or "").rstrip("/")
    if not url or not cdn or not url.startswith(cdn + "/"):
        return None
    return url[len(cdn) + 1:].split("?")[0]


def cdn_url(path):
    return f"{(getattr(settings, 'BUNNY_CDN_URL', '') or '').rstrip('/')}/{path}"


def in_layout(url):
    """True for a photo stored in this module's layout — the only ones a
    move may touch."""
    path = storage_path(url)
    if not path:
        return False
    parts = path.split("/")
    return (
        "/".join(parts[:2]) == ROOT
        and len(parts) in (4, 5)
        and not parts[2].startswith("product_")
    )


# ── Moving photos to the folder their use calls for ─────────────────────

def _misplaced(urls_q, adopt=()):
    """[(url, thumbnail, target path)] for every photo matching `urls_q` that
    is not where its use and SKUs put it. One query, however many photos."""
    from .models import ProductFile

    adopt = set(adopt)
    uses = {}
    for url, thumbnail, pid, sku, title, vid, variant_sku in (
        ProductFile.everywhere.filter(urls_q).exclude(file_url__isnull=True).values_list(
            "file_url", "video_thumbnail", "product_id", "product__sku", "product__title",
            "product_variant_id", "product_variant__variant_sku")
    ):
        if in_layout(url) or url in adopt:
            uses.setdefault(url, []).append((thumbnail, pid, sku, title, vid, variant_sku))

    plan = []
    for url, rows in uses.items():
        products = {pid for _, pid, *_ in rows}
        if len(products) != 1 or None in products:
            continue  # nobody's, or several products': not ours to file
        thumbnail, pid, sku, title, _, _ = rows[0]
        users = {(vid, variant_sku) for *_, vid, variant_sku in rows}
        variant_sku = ""
        if len(users) == 1:
            vid, only_sku = users.pop()
            variant_sku = only_sku if vid is not None else ""
        name = storage_path(url).rsplit("/", 1)[-1]
        if url in adopt:
            name = new_file_name(SimpleNamespace(title=title), name[name.rfind("."):] if "." in name else "")
        target = f"{_folder(pid, sku, variant_sku or '')}/{name}"
        if target != storage_path(url):
            plan.append((url, next((t for t, *_ in rows if t), None), target))
    return plan


def _move(old_url, new_path):
    """Copy the file, point everything that used it at the copy, and retire
    the original. Returns the new URL."""
    from .models import ProductCategory, ProductFile, RetiredCdnFile, VariantAttributeValueImage
    from .utils.bunny_storage import download_from_bunny, upload_to_bunny

    content = download_from_bunny(storage_path(old_url), stream=False).content
    new_url = upload_to_bunny(content, new_path, purge=False)
    with transaction.atomic():
        ProductFile.everywhere.filter(file_url=old_url).update(file_url=new_url)
        ProductFile.everywhere.filter(video_thumbnail=old_url).update(video_thumbnail=new_url)
        VariantAttributeValueImage.objects.filter(image_url=old_url).update(image_url=new_url)
        ProductCategory.objects.filter(image_url=old_url).update(image_url=new_url)
        RetiredCdnFile.objects.update_or_create(
            url=old_url,
            defaults={"delete_after": timezone.now() + timedelta(days=RETIRE_DAYS)},
        )
    return new_url


def relocate(product_id, adopt=()):
    """Move every photo of the product that sits in the wrong folder.

    `adopt` names URLs outside the layout to bring into it under a fresh
    name — the uploads a new product made before it had a SKU. Safe to run
    again: a photo already where it belongs is left alone, and a move that
    fails leaves the photo working where it was.
    """
    from .models import ProductFile

    urls = ProductFile.everywhere.filter(product_id=product_id).values("file_url")
    return _carry_out(_misplaced(Q(file_url__in=urls), adopt), adopt)


def sweep():
    """relocate() for every product at once: catches SKUs and picks changed
    anywhere but the product page — a shell fix, a bulk rename."""
    return _carry_out(_misplaced(Q(file_url__startswith=cdn_url(ROOT + "/"))))


def _carry_out(plan, adopt=()):
    adopt = set(adopt)
    moved = 0
    for url, thumbnail, target in plan:
        try:
            _move(url, target)
            moved += 1
        except Exception as exc:
            print(f"[product_images] could not move {url}: {exc}")
            continue
        # A video's still frame goes where the video went.
        if thumbnail and (in_layout(thumbnail) or thumbnail in adopt):
            thumb_target = f"{target.rsplit('/', 1)[0]}/{storage_path(thumbnail).rsplit('/', 1)[-1]}"
            if thumb_target != storage_path(thumbnail):
                try:
                    _move(thumbnail, thumb_target)
                except Exception as exc:
                    print(f"[product_images] could not move {thumbnail}: {exc}")
    return moved


def relocate_after_commit(product_id, adopt=()):
    """relocate() once the save is committed, off the request: a move is a
    download and an upload per photo, which the person saving needn't wait
    for. Expired retired files are cleared on the same run."""
    adopt = tuple(adopt)

    def work():
        try:
            relocate(product_id, adopt)
            delete_expired()
        except Exception as exc:
            print(f"[product_images] relocate {product_id} stopped: {exc}")
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())


HOUSEKEEPING_EVERY = 60 * 60
_HOUSEKEEPING_KEY = "marketing.product_images.housekept"


def housekeep_now_and_then():
    """At most once an hour, off the request: sweep() and delete_expired().

    Nothing here runs on a timer, so the storefront's own calls are the
    clock — it asks for products all day. Each server process keeps its own
    hour; a second run finds nothing left to do. Started on commit, so it
    sees committed data: a plain request starts it at once, a test's
    transaction never does.
    """
    if not cache.add(_HOUSEKEEPING_KEY, True, HOUSEKEEPING_EVERY):
        return

    def work():
        try:
            sweep()
            delete_expired()
        except Exception as exc:
            print(f"[product_images] housekeeping stopped: {exc}")
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())


# ── Deleting what a move left behind ─────────────────────────────────────

def delete_expired(now=None):
    """Delete the retired files whose wait is over, then any folder that
    is left empty by it. A file something has started using again is kept."""
    from .models import RetiredCdnFile
    from .signals import cdn_url_in_use
    from .utils.bunny_storage import delete_empty_bunny_folder, delete_from_bunny

    now = now or timezone.now()
    deleted = 0
    folders = set()
    for retired in RetiredCdnFile.objects.filter(delete_after__lte=now):
        path = storage_path(retired.url)
        if not cdn_url_in_use(retired.url) and path:
            if not delete_from_bunny(retired.url):
                continue  # try again next run
            deleted += 1
            folders.add(path.rsplit("/", 1)[0])
        retired.delete()

    # Deepest first, so a variant folder goes before its product's.
    for folder in sorted(folders, key=lambda f: f.count("/"), reverse=True):
        while folder.count("/") >= 2 and folder != ROOT:
            if not delete_empty_bunny_folder(folder):
                break
            folder = folder.rsplit("/", 1)[0]
    return deleted


# ── Alt text ──────────────────────────────────────────────────────────────

def _localized_title(title, description, language):
    """The product's title in `language` when its description carries one
    (the storefront's translations JSON), else the title as stored."""
    import json

    raw = (description or "").strip()
    if raw.startswith("{"):
        try:
            translations = json.loads(raw).get("translations") or {}
            return (translations.get(language) or {}).get("title") or title
        except (ValueError, AttributeError):
            pass
    return title


def alt_texts(title, description, group, attributes):
    """What a photo shows, per storefront language:

        "Florenza, Fabric. Color: Undyed, Width: 320 cm, Yarn: 103 semi-matte gold"

    `attributes` are the (name, value) pairs the photo shows: its variant's,
    the ones its variants share (alt_texts_by_row), none for the product's
    own photo. Every name and value reads in the
    language's wording where one exists. A value that says nothing ("none",
    "no") is left out.
    """
    from .attributes import attribute_label, display_value, group_label, term_key

    pairs = sorted(
        (name, value) for name, value in attributes
        if term_key(value) not in _NOTHING
    )
    texts = {}
    for language in ALT_LANGUAGES:
        head = _localized_title(title, description, language) or ""
        if group:
            label = group_label(group, language).replace("_", " ")
            head = f"{head}, {label[:1].upper()}{label[1:]}" if head else label
        details = ", ".join(
            f"{attribute_label(name, language)}: {display_value(name, value, language)}"
            for name, value in pairs
        )
        texts[language] = f"{head}. {details}" if details else head
    return texts


def alt_texts_by_row(rows, title, description, group, variant_pairs):
    """{row id: alt_texts} for one product's photo rows.

    `rows` are dicts with "id", "file_url" and "product_variant_id";
    `variant_pairs` maps a variant id to its (name, value) pairs. A photo
    several variants share shows what they have in common — a fabric's
    every colourway is not "Color: White" — so it is described by the
    attribute values all of them hold, the same for each of its rows.
    """
    users = {}
    for row in rows:
        if row["product_variant_id"] is not None:
            users.setdefault(row["file_url"], set()).add(row["product_variant_id"])

    texts = {}
    by_users = {}
    for row in rows:
        variants = frozenset(users.get(row["file_url"], ()))
        if variants not in by_users:
            shared = None
            for vid in variants:
                pairs = set(variant_pairs.get(vid, ()))
                shared = pairs if shared is None else shared & pairs
            by_users[variants] = alt_texts(title, description, group, shared or ())
        texts[row["id"]] = by_users[variants]
    return texts
