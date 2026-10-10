"""OpenRouter adapter via the OpenAI-compatible endpoint."""
from __future__ import annotations

from typing import AsyncIterator

from ..config import settings
from .errors import ProviderError

BASE_URL = "https://openrouter.ai/api/v1"
_client = None
_client_key = None


def _get_client():
    global _client, _client_key
    from openai import AsyncOpenAI

    if _client is None or _client_key != settings.openrouter_api_key:
        _client = AsyncOpenAI(base_url=BASE_URL, api_key=settings.openrouter_api_key, timeout=90,
                              default_headers={"HTTP-Referer": "http://localhost:3000", "X-Title": "QuarantineShock"})
        _client_key = settings.openrouter_api_key
    return _client


def _classify(e: Exception) -> ProviderError:
    import openai

    msg = str(e)[:300]
    if isinstance(e, openai.RateLimitError):
        return ProviderError("openrouter", "quota", msg)
    if isinstance(e, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ProviderError("openrouter", "auth", msg)
    if isinstance(e, openai.APIStatusError):
        code = e.status_code
        if code == 402:
            return ProviderError("openrouter", "quota", msg)
        if code >= 500:
            return ProviderError("openrouter", "server", msg)
        return ProviderError("openrouter", "other", msg)
    if isinstance(e, openai.APITimeoutError):
        return ProviderError("openrouter", "timeout", msg)
    if isinstance(e, openai.APIConnectionError):
        return ProviderError("openrouter", "server", msg)
    return ProviderError("openrouter", "other", msg)


def _check() -> None:
    if not settings.openrouter_configured:
        raise ProviderError("openrouter", "not_configured", "OPENROUTER_API_KEY / OPENROUTER_MODEL not set")


async def _create(prompt: str, response_format: dict | None, stream: bool = False):
    kwargs: dict = {"extra_body": {"reasoning": {"effort": "low"}}}  # keeps reasoning models fast and cheap
    if response_format is not None:
        kwargs["response_format"] = response_format
    return await _get_client().chat.completions.create(
        model=settings.openrouter_model, temperature=0.2, stream=stream,
        messages=[{"role": "user", "content": prompt}], **kwargs)


async def generate(prompt: str, tier: str, json_schema: dict | None) -> tuple[str, dict]:
    _check()
    fmt = None
    if json_schema is not None:
        fmt = {"type": "json_schema", "json_schema": {"name": "result", "strict": False, "schema": json_schema}}
    try:
        try:
            resp = await _create(prompt, fmt)
        except Exception as e:  # noqa: BLE001
            # some models/providers reject json_schema: fall back to plain JSON mode (schema is in the prompt)
            if fmt is not None and getattr(e, "status_code", None) == 400:
                resp = await _create(prompt, {"type": "json_object"})
            else:
                raise
    except Exception as e:  # noqa: BLE001
        raise _classify(e) from e
    if not resp.choices:
        raise ProviderError("openrouter", "server", "empty response")
    usage = getattr(resp, "usage", None)
    return resp.choices[0].message.content or "", {
        "model": settings.openrouter_model,
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
    }


async def stream(prompt: str, tier: str) -> AsyncIterator[str]:
    _check()
    try:
        it = await _create(prompt, None, stream=True)
        async for chunk in it:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except ProviderError:
        raise
    except Exception as e:  # noqa: BLE001
        raise _classify(e) from e
