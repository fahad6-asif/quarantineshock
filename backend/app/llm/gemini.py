"""Gemini adapter (google-genai SDK)."""
from __future__ import annotations

from typing import AsyncIterator

from ..config import settings
from .errors import ProviderError

_client = None
_client_key = None


def _get_client():
    global _client, _client_key
    from google import genai
    from google.genai import types

    if _client is None or _client_key != settings.gemini_api_key:
        # a stuck free-tier request must fail over instead of hanging the demo
        _client = genai.Client(api_key=settings.gemini_api_key,
                               http_options=types.HttpOptions(timeout=int(settings.gemini_timeout_s * 1000)))
        _client_key = settings.gemini_api_key
    return _client


def _classify(e: Exception) -> ProviderError:
    from google.genai import errors

    if isinstance(e, errors.APIError):
        code = getattr(e, "code", 0) or 0
        status = str(getattr(e, "status", "") or "")
        msg = str(getattr(e, "message", "") or e)[:300]
        if code == 429 or "RESOURCE_EXHAUSTED" in status or "quota" in msg.lower():
            return ProviderError("gemini", "quota", msg)
        if code in (401, 403) or "API_KEY" in msg.upper() or "PERMISSION" in status:
            return ProviderError("gemini", "auth", msg)
        if code == 400 and "api key" in msg.lower():
            return ProviderError("gemini", "auth", msg)
        if code >= 500 or "UNAVAILABLE" in status or "overloaded" in msg.lower():
            return ProviderError("gemini", "server", msg)
        return ProviderError("gemini", "other", msg)
    text = f"{type(e).__name__} {e}".lower()
    if any(k in text for k in ("timeout", "timed out")):
        return ProviderError("gemini", "timeout", str(e)[:300] or type(e).__name__)
    connectionish = any(k in text for k in ("readerror", "connecterror", "connection"))
    return ProviderError("gemini", "server" if connectionish else "other", str(e)[:300] or type(e).__name__)


def model_for(tier: str) -> str:
    return settings.gemini_model_strong if tier == "strong" else settings.gemini_model_fast


async def generate(prompt: str, tier: str, json_schema: dict | None) -> tuple[str, dict]:
    from google.genai import types

    if not settings.gemini_configured:
        raise ProviderError("gemini", "not_configured", "GEMINI_API_KEY / GEMINI_MODEL_FAST not set")
    cfg = types.GenerateContentConfig(temperature=0.2)
    if json_schema is not None:
        cfg.response_mime_type = "application/json"
        cfg.response_json_schema = json_schema
    models = [model_for(tier)]
    if settings.gemini_model_backup and settings.gemini_model_backup not in models:
        models.append(settings.gemini_model_backup)
    for i, model in enumerate(models):
        try:
            resp = await _get_client().aio.models.generate_content(model=model, contents=prompt, config=cfg)
            break
        except Exception as e:  # noqa: BLE001
            err = _classify(e)
            # overloaded model (fast 503): try the backup Gemini model. A timeout is NOT retried here:
            # Gemini isn't answering, so the client switches straight to OpenRouter instead of waiting again.
            if err.kind == "server" and i + 1 < len(models):
                continue
            raise err from e
    usage = getattr(resp, "usage_metadata", None)
    text = resp.text or ""
    return text, {
        "model": model,
        "input_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
    }


async def stream(prompt: str, tier: str) -> AsyncIterator[str]:
    from google.genai import types

    if not settings.gemini_configured:
        raise ProviderError("gemini", "not_configured", "GEMINI_API_KEY / GEMINI_MODEL_FAST not set")
    try:
        it = await _get_client().aio.models.generate_content_stream(
            model=model_for(tier), contents=prompt, config=types.GenerateContentConfig(temperature=0.2))
        async for chunk in it:
            if chunk.text:
                yield chunk.text
    except ProviderError:
        raise
    except Exception as e:  # noqa: BLE001
        raise _classify(e) from e
