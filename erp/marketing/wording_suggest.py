"""A first guess at a value's wording in another language, for a person to check.

Values are stored in English and read in other languages through the
catalog wordings. When somebody types a word no wording knows ("fildişi"),
or a value has no wording yet in some language, Gemini offers one. It is
only ever a suggestion shown in the field: what is saved is what the
person leaves there. Gemini is told the wordings already written for the
attribute, so it follows the catalog's own vocabulary ("sedef" is nacre
here, not pearl) rather than a dictionary's.

Uses GOOGLE_AI_API_KEY, the key label reading uses. With no key, no
network or no answer, there is simply no suggestion.
"""
import json
import logging

from .attributes import WORDING_VALUE, _wordings, term_key

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "tr": "Turkish", "ru": "Russian", "pl": "Polish"}
_EXAMPLES = 60


def _env(key):
    import os
    value = os.environ.get(key)
    if value:
        return value
    try:
        from decouple import config
        return config(key, default=None)
    except Exception:
        return None


def _examples(attribute_name, languages):
    """The wordings already written for this attribute in `languages`, as
    "english key = wording" lines."""
    scope = term_key(attribute_name)
    lines = []
    for (kind, held_scope, key, language), text in _wordings().items():
        if kind == WORDING_VALUE and held_scope in (scope, "") and language in languages:
            lines.append(f"{key} = {text} ({LANGUAGE_NAMES.get(language, language)})")
        if len(lines) >= _EXAMPLES:
            break
    return lines


def _ask(prompt):
    """Gemini's JSON answer to `prompt`, or None. A plain call to its REST
    API: the google-genai SDK wants a newer google-auth than the Gmail and
    Drive clients are pinned to."""
    import requests

    api_key = _env("GOOGLE_AI_API_KEY")
    if not api_key:
        return None
    model = _env("GEMINI_MODEL") or "gemini-2.5-flash"
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                                       "maxOutputTokens": 200,
                                       "thinkingConfig": {"thinkingBudget": 0}}},
            timeout=10)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1]) if start != -1 and end > start else None
    except Exception:
        logger.warning("wording suggestion failed", exc_info=True)
        return None


def suggest_wordings(attribute_name, text, source, targets):
    """({language: suggested wording}, the language `text` is in) for
    `text`, a value of `attribute_name`, in each of `targets`. `source` is
    the language it is written in, or "auto" when nobody knows — a word
    typed into the goods receipt may be in any language whatever the
    screen's. ({}, None) when there is no suggestion."""
    text = " ".join(str(text or "").split())
    targets = [t for t in targets if t in LANGUAGE_NAMES and t != source]
    if not text or (source not in LANGUAGE_NAMES and source != "auto") or not targets:
        return {}, None
    examples = _examples(attribute_name,
                         set(LANGUAGE_NAMES) if source == "auto" else {source, *targets, "en"})
    wanted = ", ".join(f'"{t}": {LANGUAGE_NAMES[t]}' for t in targets)
    written = ("in a language to work out (one of "
               + ", ".join(f'"{c}" {n}' for c, n in LANGUAGE_NAMES.items()) + ")"
               if source == "auto" else f"in {LANGUAGE_NAMES[source]}")
    prompt = (
        "You word the attribute values of a product catalog. "
        + (f'Attribute: "{attribute_name}". ' if attribute_name else "")
        + f'Value, {written}: "{text}".\n'
        f"Give the same value in: {wanted}. English is written in lower case, "
        "American spelling. A code, model number or measurement stays exactly "
        "as it is. Follow the catalog's own wordings below where they apply.\n"
        + ("\n".join(examples) + "\n" if examples else "")
        + "Answer with JSON only, one key per language code"
        + (', and "language": the code of the language the value is written in.'
           if source == "auto" else ".")
    )
    answer = _ask(prompt)
    if not isinstance(answer, dict):
        return {}, None
    language = source if source != "auto" else answer.get("language")
    language = language if language in LANGUAGE_NAMES else None
    return ({t: " ".join(str(answer[t]).split())[:255]
             for t in targets if isinstance(answer.get(t), str) and answer[t].strip()},
            language)
