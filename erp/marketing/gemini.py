"""One way to ask Gemini, for everything that does: label reading when Claude
is out, and the wording suggestions.

A plain call to its REST API with requests. The google-genai SDK was never
in requirements.txt, so neither caller could run on the server, and it
needs google-auth >= 2.56 while the Gmail and Drive clients pin 2.25.2.

Models come and go: gemini-2.5-flash was closed to new keys in 2026. The
call tries GEMINI_MODEL when it is set, then the models below, and moves
on from one that is gone, overloaded or too slow. Only a refused key
stops it at once.
"""
import base64
import logging
import os

logger = logging.getLogger(__name__)

MODELS = ("gemini-3.5-flash-lite", "gemini-flash-latest")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiUnavailable(Exception):
    """No answer: no key, a refused key, or every model failed."""


def env(key):
    """An env var from the process or the project's .env."""
    value = os.environ.get(key)
    if value:
        return value
    try:
        from decouple import config
        return config(key, default=None)
    except Exception:
        return None


def _part(part):
    if isinstance(part, tuple):
        data, mime_type = part
        return {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(data).decode()}}
    return {"text": part}


def ask_gemini(parts, *, max_output_tokens=1024, timeout=30):
    """Gemini's text answer to `parts` — strings, and (bytes, mime type)
    pairs for images — asked for as JSON. Raises GeminiUnavailable."""
    import requests

    api_key = env("GOOGLE_AI_API_KEY")
    if not api_key:
        raise GeminiUnavailable("GOOGLE_AI_API_KEY is not set")
    models = list(dict.fromkeys(m for m in (env("GEMINI_MODEL"), *MODELS) if m))
    body = {"contents": [{"parts": [_part(p) for p in parts]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                                 "maxOutputTokens": max_output_tokens}}
    failures = []
    for model in models:
        try:
            resp = requests.post(_URL.format(model=model), headers={"x-goog-api-key": api_key},
                                 json=body, timeout=timeout)
        except requests.RequestException as e:
            failures.append(f"{model}: {type(e).__name__}")
            continue
        if resp.status_code in (401, 403):
            raise GeminiUnavailable(f"Gemini key refused ({resp.status_code})")
        if resp.status_code != 200:
            try:
                message = resp.json().get("error", {}).get("message", "")
            except ValueError:
                message = ""
            failures.append(f"{model}: {resp.status_code} {message[:120]}")
            continue
        try:
            return "".join(p.get("text", "") for p in
                           resp.json()["candidates"][0]["content"]["parts"]).strip()
        except (ValueError, KeyError, IndexError, TypeError):
            failures.append(f"{model}: no answer")
    logger.warning("Gemini unavailable: %s", "; ".join(failures))
    raise GeminiUnavailable("; ".join(failures) or "no model to ask")
