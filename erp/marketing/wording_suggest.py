"""A first guess at a value's wording in another language, for a person to check.

Values are stored in English and read in other languages through the
catalog wordings. When somebody types a word no wording knows ("fildişi"),
or a value has no wording yet in some language, Gemini offers one. It is
only ever a suggestion shown in the field: what is saved is what the
person leaves there. Gemini is told the wordings already written for the
attribute, so it follows the catalog's own vocabulary ("sedef" is nacre
here, not pearl) rather than a dictionary's.

Uses the GOOGLE_AI_API_KEY label reading already uses. With no key, no
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
    """Gemini's JSON answer to `prompt`, or None."""
    api_key = _env("GOOGLE_AI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None
    config = dict(response_mime_type="application/json", temperature=0, max_output_tokens=200)
    try:
        config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:
        pass
    try:
        resp = genai.Client(api_key=api_key).models.generate_content(
            model=_env("GEMINI_MODEL") or "gemini-2.5-flash",
            contents=[prompt], config=types.GenerateContentConfig(**config))
        text = (getattr(resp, "text", None) or "").strip()
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1]) if start != -1 and end > start else None
    except Exception:
        logger.warning("wording suggestion failed", exc_info=True)
        return None


def suggest_wordings(attribute_name, text, source, targets):
    """{language: suggested wording} for `text`, a value of `attribute_name`
    written in `source`, in each of `targets`. {} when there is none."""
    text = " ".join(str(text or "").split())
    targets = [t for t in targets if t in LANGUAGE_NAMES and t != source]
    if not text or source not in LANGUAGE_NAMES or not targets:
        return {}
    examples = _examples(attribute_name, {source, *targets, "en"})
    wanted = ", ".join(f'"{t}": {LANGUAGE_NAMES[t]}' for t in targets)
    prompt = (
        "You word the attribute values of a product catalog. "
        + (f'Attribute: "{attribute_name}". ' if attribute_name else "")
        + f'Value, in {LANGUAGE_NAMES[source]}: "{text}".\n'
        f"Give the same value in: {wanted}. English is written in lower case, "
        "American spelling. A code, model number or measurement stays exactly "
        "as it is. Follow the catalog's own wordings below where they apply.\n"
        + ("\n".join(examples) + "\n" if examples else "")
        + "Answer with JSON only, one key per language code."
    )
    answer = _ask(prompt)
    if not isinstance(answer, dict):
        return {}
    return {t: " ".join(str(answer[t]).split())[:255]
            for t in targets if isinstance(answer.get(t), str) and answer[t].strip()}
