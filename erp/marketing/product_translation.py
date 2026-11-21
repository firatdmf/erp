"""A product's text in the storefront's other languages, worked out from the English.

People write a product's text once, in English: its name (Product.title)
and the description, care instructions and additional info the product
form keeps in Product.description as {"translations": {"en": {...}}}.
Gemini writes the same text in each of TARGETS into the slots the
storefront already reads ({"translations": {"tr": {...}, "ru": {...}}}),
and "translated_from" records which English each was made from. So an
edit to the English is translated again, and nothing else is.

A translation stored with no record of what it was made from (typed by
hand before the form went English-only) is taken as made from the English
as it now stands: it stays until that English changes.

Runs once a product is saved, off the request, and on the hourly
housekeeping (product_images.housekeep_now_and_then) for whatever that
missed: no key, Gemini out, a product written by a receipt or a shell.
The catalog wordings go in as a glossary, so a product reads in the
catalog's own words ("sedef" is nacre here, not pearl).
"""
import hashlib
import json
import logging
import threading
import time

from django.db import connection, transaction

logger = logging.getLogger(__name__)

# The storefront's languages besides English (EN, TR, RU; Polish is off).
TARGETS = ("tr", "ru")
LANGUAGE_NAMES = {"en": "English", "tr": "Turkish", "ru": "Russian"}
TEXTS = ("description", "care_instructions", "additional_info")
FIELDS = ("title",) + TEXTS

# One request carries several products, up to about this much English;
# the free tier counts requests, not words.
BATCH_CHARACTERS = 4000
BATCH_PRODUCTS = 25
# Free-tier requests per minute are few: a run spaces its requests out.
PAUSE_SECONDS = 4
HOURLY_REQUESTS = 20
_GLOSSARY_LINES = 150


def parse(raw):
    """Product.description as a dict; {} when empty or not JSON."""
    raw = (raw or "").strip()
    if not raw.startswith("{"):
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def dump(data):
    """`data` as Product.description stores it; None when nothing is left."""
    translations = {lang: texts for lang, texts in (data.get("translations") or {}).items() if texts}
    data = {**data, "translations": translations}
    if not translations:
        data.pop("translations")
    if not data.get("translated_from"):
        data.pop("translated_from", None)
    return json.dumps(data, ensure_ascii=False, indent=2) if data else None


def with_english(stored, posted):
    """The stored description with its English replaced by the English
    `posted` by the product form, every other language and its record
    kept. The name is the product's title, so the English keeps no title
    of its own."""
    data = parse(stored)
    english = ((parse(posted).get("translations") or {}).get("en") or {})
    english = {f: str(english[f]).strip() for f in TEXTS if str(english.get(f) or "").strip()}
    translations = dict(data.get("translations") or {})
    translations["en"] = english
    return dump({**data, "translations": translations})


def english_source(title, data):
    """What the translations are made from: the name and the English texts."""
    english = (data.get("translations") or {}).get("en") or {}
    source = {"title": " ".join(str(title or "").split())}
    source.update({f: english[f] for f in TEXTS if english.get(f)})
    return {k: v for k, v in source.items() if v}


def source_key(source):
    """A short fingerprint of `source`: equal while the English is unchanged."""
    text = json.dumps(source, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _plan(title, raw):
    """(source, key, languages to translate, languages to keep as they are)."""
    data = parse(raw)
    source = english_source(title, data)
    if not source:
        return source, None, [], []
    key = source_key(source)
    made = data.get("translated_from") or {}
    translations = data.get("translations") or {}
    stale = [lang for lang in TARGETS if made.get(lang) != key]
    keep = [lang for lang in stale if lang not in made and translations.get(lang)]
    return source, key, [lang for lang in stale if lang not in keep], keep


def _record(product_id, key, translated):
    """Store {language: texts} as made from the English fingerprinted `key`
    — None texts keep what is there. Skipped when the English has changed
    since, the next run picks that up. True when stored."""
    from .models import Product

    with transaction.atomic():
        row = (Product.everywhere.select_for_update()
               .filter(pk=product_id).values_list("title", "description").first())
        if not row:
            return False
        title, raw = row
        data = parse(raw)
        if source_key(english_source(title, data)) != key:
            return False
        translations = dict(data.get("translations") or {})
        made = dict(data.get("translated_from") or {})
        for lang, texts in translated.items():
            if texts is not None:
                translations[lang] = texts
            made[lang] = key
        stored = dump({**data, "translations": translations, "translated_from": made})
        Product.everywhere.filter(pk=product_id).update(description=stored)
    return True


def _glossary(texts):
    """The catalog wordings in TARGETS whose English appears in `texts`, as
    "english = wording (Language)" lines."""
    import re

    from .attributes import _wordings, fold_term

    words = set(fold_term(re.sub(r"<[^>]+>", " ", " ".join(texts))).replace("+", " ").split())
    lines = []
    for (_kind, _scope, key, lang), wording in _wordings().items():
        if lang not in TARGETS or not wording:
            continue
        key_words = fold_term(key).replace("+", " ").split()
        if key_words and set(key_words) <= words:
            lines.append((len(key_words) * -1, f"{key} = {wording} ({LANGUAGE_NAMES[lang]})"))
    return [line for _rank, line in sorted(set(lines))[:_GLOSSARY_LINES]]


def _prompt(items):
    texts = [v for item in items for v in item.values() if isinstance(v, str)]
    glossary = _glossary(texts)
    languages = ", ".join(f'"{lang}" ({LANGUAGE_NAMES[lang]})' for lang in TARGETS)
    return (
        "You translate the product texts of a home-textile shop's website from English into "
        f"{languages}.\n"
        "- Keep every HTML tag and attribute exactly as it is; translate only the text between tags.\n"
        "- Keep product codes, SKUs and the design or collection name itself (such as \"K13094\", "
        "\"LUCAS\", \"Aura Glitter Ring\", \"Florenza\") as they are, in any capitals. Translate "
        "every other word of a title: what the product is, its fabric and finish "
        "(\"ALBERT | Lux Sateen Core Sheet Set\" keeps \"ALBERT\" and translates the rest).\n"
        "- Write as a shop writes for its customers: natural and grammatical, not word for word.\n"
        "- Capitals follow each language's own rule for a shop's product titles, whatever the "
        "English or the glossary uses: Turkish titles capitalise each word; Russian titles "
        "capitalise only the first word and names. Words typed in all capitals in the English "
        "are written normally, except codes and the design name.\n"
        + ("- The glossary is how the shop labels its products' attributes in each language. "
           "Use it to pick the right term (which word means this fabric or finish), then inflect "
           "and phrase it as the sentence needs; don't paste a label where it doesn't fit.\n"
           "Glossary:\n" + "\n".join(glossary) + "\n" if glossary else "")
        + "Products, as JSON:\n" + json.dumps({"items": items}, ensure_ascii=False) + "\n"
        "Answer with JSON only: {\"items\": [{\"id\": <id>, "
        + ", ".join(f'"{lang}": {{<the same keys, translated>}}' for lang in TARGETS)
        + "}]} — every product, every key it was given, nothing else."
    )


def _ask(items):
    """{product id: {language: texts}} for `items`. Raises GeminiUnavailable;
    {} for an answer that can't be read."""
    from .gemini import ask_gemini

    text = ask_gemini([_prompt(items)], max_output_tokens=16384, timeout=120)
    start, end = text.find("{"), text.rfind("}")
    try:
        answer = json.loads(text[start:end + 1]) if start != -1 and end > start else {}
    except ValueError:
        return {}
    wanted = {item["id"]: [f for f in FIELDS if f in item] for item in items}
    result = {}
    for row in answer.get("items") or []:
        if not isinstance(row, dict) or row.get("id") not in wanted:
            continue
        fields = wanted[row["id"]]
        texts = {}
        for lang in TARGETS:
            given = row.get(lang) if isinstance(row.get(lang), dict) else {}
            translated = {f: str(given[f]).strip() for f in fields if str(given.get(f) or "").strip()}
            if len(translated) == len(fields):
                texts[lang] = translated
        if texts:
            result[row["id"]] = texts
    return result


def _batches(queue):
    batch, size = [], 0
    for entry in queue:
        length = sum(len(v) for v in entry[1].values())
        if batch and (size + length > BATCH_CHARACTERS or len(batch) >= BATCH_PRODUCTS):
            yield batch
            batch, size = [], 0
        batch.append(entry)
        size += length
    if batch:
        yield batch


def translate(product_ids=None, max_requests=None, pause=PAUSE_SECONDS):
    """Bring the translations of `product_ids` (every product when None) up
    to their English. {"translated": n, "kept": n, "left": n} — left are
    the ones not done this run (out of requests, Gemini out, an answer
    without them)."""
    from .gemini import GeminiUnavailable
    from .models import Product

    rows = Product.everywhere.order_by("pk").values_list("pk", "title", "description")
    if product_ids is not None:
        rows = rows.filter(pk__in=list(product_ids))
    counts = {"translated": 0, "kept": 0, "left": 0}
    queue = []
    for pk, title, raw in rows.iterator():
        source, key, todo, keep = _plan(title, raw)
        if keep and _record(pk, key, {lang: None for lang in keep}):
            counts["kept"] += 1
        if todo:
            queue.append((pk, source, key, todo))

    pending = list(_batches([(pk, source, key, todo) for pk, source, key, todo in queue]))
    requests = 0
    while pending:
        batch = pending.pop(0)
        if max_requests is not None and requests >= max_requests:
            counts["left"] += len(batch) + sum(len(b) for b in pending)
            break
        if requests and pause:
            time.sleep(pause)
        requests += 1
        try:
            answer = _ask([{"id": pk, **source} for pk, source, _key, _todo in batch])
        except GeminiUnavailable as exc:
            logger.warning("Product translation stopped: %s", exc)
            counts["left"] += len(batch) + sum(len(b) for b in pending)
            break
        missed = []
        for pk, source, key, todo in batch:
            texts = answer.get(pk) or {}
            if all(lang in texts for lang in todo):
                if _record(pk, key, {lang: texts[lang] for lang in todo}):
                    counts["translated"] += 1
            else:
                missed.append((pk, source, key, todo))
        # A long answer cut short loses its last products: those are asked
        # again in halves; a single product that still fails waits.
        if missed and len(batch) > 1:
            half = (len(missed) + 1) // 2
            pending[:0] = [missed[:half], missed[half:]] if len(missed) > 1 else [missed]
        else:
            counts["left"] += len(missed)
    return counts


def translate_after_commit(product_id):
    """translate() for one product once its save is committed, off the
    request: the person saving needn't wait for Gemini."""

    def work():
        try:
            translate([product_id], max_requests=3, pause=0)
        except Exception as exc:
            print(f"[product_translation] product {product_id}: {exc}")
        finally:
            connection.close()

    transaction.on_commit(lambda: threading.Thread(target=work, daemon=True).start())
