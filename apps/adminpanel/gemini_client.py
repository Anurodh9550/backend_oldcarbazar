"""Gemini assistant client for Old Car Bazar.

Uses the official ``google-genai`` SDK when available, with a REST
fallback. Accepts Google AI Studio API keys in both legacy (``AIza``)
and current (``AQ.``) formats.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import error as urlerror, request as urlrequest

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


def get_gemini_api_key() -> str:
    """Read GEMINI_API_KEY from Django settings, then os.environ."""
    key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    return str(key).strip()


def get_gemini_model() -> str:
    """Preferred model name (default gemini-2.5-flash)."""
    model = getattr(settings, "GEMINI_MODEL", "") or os.environ.get("GEMINI_MODEL", "")
    return (model or DEFAULT_MODEL).strip()


def _key_prefix(api_key: str) -> str:
    if not api_key:
        return "(empty)"
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-2:]}"


def is_plausible_gemini_api_key(api_key: str) -> bool:
    """Return True for known Google AI Studio key shapes (AIza… or AQ.…)."""
    if not api_key or len(api_key) < 20:
        return False
    if api_key.startswith(("AIza", "AQ.")):
        return True
    # Future-proof: allow other non-whitespace keys from Google AI Studio.
    return " " not in api_key and len(api_key) >= 24


def validate_gemini_api_key(api_key: str) -> str | None:
    """User-facing hint when the key shape looks wrong; None if OK."""
    if not api_key:
        return None
    if is_plausible_gemini_api_key(api_key):
        return None
    return (
        "Gemini API key invalid lag rahi hai. "
        "https://aistudio.google.com/app/apikey se nayi key lein "
        "(AIza… ya AQ.… format) aur hosting env me GEMINI_API_KEY set karein."
    )


def _models_to_try() -> list[str]:
    preferred = get_gemini_model()
    models: list[str] = []
    if preferred:
        models.append(preferred)
    for name in MODEL_FALLBACKS:
        if name not in models:
            models.append(name)
    return models


def _call_gemini_sdk(
    api_key: str,
    question: str,
    system_instruction: str,
) -> tuple[str | None, str | None]:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning("google-genai not installed; will use REST fallback")
        return None, "google-genai not installed"

    try:
        client = genai.Client(api_key=api_key)
        logger.info(
            "Gemini SDK client initialized (key_prefix=%s, preferred_model=%s)",
            _key_prefix(api_key),
            get_gemini_model(),
        )
    except Exception as exc:
        logger.exception("Gemini SDK client initialization failed: %s", exc)
        return None, str(exc)

    last_error: str | None = None
    for model in _models_to_try():
        try:
            response = client.models.generate_content(
                model=model,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.35,
                    max_output_tokens=450,
                ),
            )
            reply = (getattr(response, "text", None) or "").strip()
            if reply:
                logger.info("Gemini SDK success (model=%s)", model)
                return reply, None
            last_error = "Empty response from Gemini."
            logger.warning("Gemini SDK empty response (model=%s)", model)
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "Gemini SDK request failed (model=%s): %s",
                model,
                exc,
                exc_info=True,
            )
    return None, last_error


def _call_gemini_rest(
    api_key: str,
    question: str,
    system_instruction: str,
) -> tuple[str | None, str | None]:
    """REST fallback using generativelanguage.googleapis.com."""
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 450},
    }
    body = json.dumps(payload).encode("utf-8")
    last_error: str | None = None
    models = _models_to_try()

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        req = urlrequest.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=25) as res:
                data = json.loads(res.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                last_error = str(err_json.get("error", {}).get("message", err_body))
            except json.JSONDecodeError:
                last_error = err_body[:500] or str(exc)
            logger.error(
                "Gemini REST HTTP error (model=%s, status=%s): %s",
                model,
                exc.code,
                last_error,
            )
            if exc.code in (400, 404) and model != models[-1]:
                continue
            break
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.error("Gemini REST network/parse error (model=%s): %s", model, exc)
            break
        else:
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                reply = "\n".join(
                    part.get("text", "")
                    for part in parts
                    if isinstance(part, dict)
                ).strip()
                if reply:
                    logger.info("Gemini REST success (model=%s)", model)
                    return reply, None
            last_error = "Empty response from Gemini."
            logger.warning("Gemini REST empty response (model=%s)", model)

    return None, last_error


def generate_gemini_reply(
    question: str,
    system_instruction: str,
) -> tuple[str | None, str | None, bool]:
    """Generate a reply.

    Returns ``(reply, error_message, configured)``.
    ``configured`` is False when GEMINI_API_KEY is missing or invalid.
    """
    api_key = get_gemini_api_key()
    logger.info(
        "Gemini request: key_loaded=%s key_prefix=%s model=%s",
        bool(api_key),
        _key_prefix(api_key),
        get_gemini_model(),
    )

    if not api_key:
        return None, "GEMINI_API_KEY not set", False

    validation_error = validate_gemini_api_key(api_key)
    if validation_error:
        logger.warning(
            "Gemini API key failed shape validation (prefix=%s)",
            _key_prefix(api_key),
        )
        return None, validation_error, False

    reply, err = _call_gemini_sdk(api_key, question, system_instruction)
    if reply:
        return reply, None, True

    if err and err != "google-genai not installed":
        logger.info("Gemini SDK failed (%s); trying REST fallback", err)

    reply, err = _call_gemini_rest(api_key, question, system_instruction)
    if reply:
        return reply, None, True

    return None, err, True
