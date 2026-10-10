"""One interface for all LLM calls: disk cache -> Gemini -> OpenRouter -> cached fallback.

Every call returns (result, CallMeta). Metas are also collected in a context variable so each
agent node can report which provider answered (shown as a badge in Agent Activity).
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import re
import time
from typing import AsyncIterator, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import settings
from ..schemas import CallMeta
from . import gemini, openrouter
from .cache import cache, make_key
from .errors import LLMUnavailable, ProviderError, friendly
from .ratelimit import RateLimiter

T = TypeVar("T", bound=BaseModel)
Tier = Literal["fast", "strong"]

PROVIDERS = {"gemini": gemini, "openrouter": openrouter}
LIMITERS = {
    "gemini": RateLimiter(lambda: settings.gemini_rpm),
    "openrouter": RateLimiter(lambda: settings.openrouter_rpm),
}
UNHEALTHY_SECONDS = 600
_unhealthy_until: dict[str, float] = {}
_last_error: dict[str, str] = {}
_last_detail: dict[str, str] = {}  # raw provider message, for diagnostics (never shown as a toast)

_calls: contextvars.ContextVar[list[CallMeta] | None] = contextvars.ContextVar("llm_calls", default=None)


# ---------------------------------------------------------------- helpers
def start_collecting() -> list[CallMeta]:
    lst: list[CallMeta] = []
    _calls.set(lst)
    return lst


def _record(meta: CallMeta) -> CallMeta:
    lst = _calls.get()
    if lst is not None:
        lst.append(meta)
    return meta


def provider_chain(mode: str | None = None) -> list[str]:
    mode = mode or settings.provider_mode
    return {"auto": ["gemini", "openrouter"], "gemini": ["gemini"], "openrouter": ["openrouter"]}.get(mode, [])


def is_unhealthy(p: str) -> bool:
    return _unhealthy_until.get(p, 0) > time.time()


def mark_unhealthy(p: str, why: str) -> None:
    _unhealthy_until[p] = time.time() + UNHEALTHY_SECONDS
    _last_error[p] = why


def reset_health() -> None:
    _unhealthy_until.clear()
    _last_error.clear()


def health_snapshot() -> dict:
    return {p: {"unhealthy": is_unhealthy(p), "last_error": _last_error.get(p), "detail": _last_detail.get(p)}
            for p in PROVIDERS}


_FENCE = re.compile(r"^\s*```(?:json|JSON)?\s*|\s*```\s*$")


def strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = _FENCE.sub("", t).strip()
    # tolerate leading prose before the JSON object
    if t and t[0] not in "[{":
        i = min([x for x in (t.find("{"), t.find("[")) if x >= 0], default=-1)
        if i >= 0:
            t = t[i:]
    return t


def inline_schema(model: type[BaseModel]) -> dict:
    """Pydantic JSON schema with $refs inlined and titles removed (friendlier for providers)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {k: walk(v) for k, v in node.items() if k not in ("title",)}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


async def _call_provider(provider: str, prompt: str, tier: str, schema: dict | None) -> tuple[str, dict, int]:
    """Call with up to 2 retries on server errors (exponential backoff). Returns (text, info, attempts)."""
    mod = PROVIDERS[provider]
    attempts = 0
    delay = 2.0
    while True:
        attempts += 1
        await LIMITERS[provider].wait()
        try:
            text, info = await mod.generate(prompt, tier, schema)
            return text, info, attempts
        except ProviderError as e:
            if e.kind == "server" and attempts <= 1:  # one quick retry, then fail over
                await asyncio.sleep(delay)
                delay *= 2
                continue
            _last_detail[provider] = e.message[:300]
            raise


async def _live_json(provider: str, prompt: str, schema: type[T], tier: str) -> tuple[T, CallMeta]:
    js = inline_schema(schema)
    p = prompt
    if provider == "openrouter":
        p = f"{prompt}\n\nReturn ONLY a JSON object that matches this JSON Schema (no prose, no code fences):\n{json.dumps(js)}"
    total_attempts = 0
    last_err = ""
    t0 = time.perf_counter()
    for repair in range(3):  # first try + 2 repair retries
        text, info, n = await _call_provider(provider, p, tier, js)
        total_attempts += n
        try:
            obj = schema.model_validate(json.loads(strip_fences(text)))
            return obj, CallMeta(provider=provider, model=info.get("model"), latency_ms=int((time.perf_counter() - t0) * 1000),
                                 input_tokens=info.get("input_tokens"), output_tokens=info.get("output_tokens"),
                                 attempts=total_attempts)
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)[:800]
            p = (f"{prompt}\n\nYour previous answer was not valid JSON for the required schema. Error:\n{last_err}\n"
                 f"Return ONLY corrected JSON matching this JSON Schema:\n{json.dumps(js)}")
    raise ProviderError(provider, "bad_output", last_err)


# ---------------------------------------------------------------- public API
async def generate_json(task: str, prompt: str, schema: type[T], tier: Tier = "fast",
                        scope: str | None = None) -> tuple[T, CallMeta]:
    mode = settings.provider_mode
    key = make_key(task, prompt, schema.__name__)
    rec = cache.get(key) if mode in ("auto", "replay") else cache.get(key, provider=mode)
    if rec:
        try:
            obj = schema.model_validate(rec["value"])
            return obj, _record(CallMeta(provider="replay" if mode == "replay" else "cache", model=rec.get("model"),
                                         cached=True, task=task))
        except ValidationError:
            pass  # schema changed since caching -> treat as miss

    failures: list[ProviderError] = []
    for prov in provider_chain(mode):
        if mode == "auto" and is_unhealthy(prov):
            failures.append(ProviderError(prov, _last_error.get(prov, "quota"), "marked unhealthy for 10 minutes"))  # type: ignore[arg-type]
            continue
        try:
            obj, meta = await _live_json(prov, prompt, schema, tier)
        except ProviderError as e:
            if e.kind in ("quota", "auth", "server", "timeout", "bad_output"):
                mark_unhealthy(prov, e.kind)
            failures.append(e)
            continue
        cache.put(key, task=task, scope=scope, provider=prov, model=meta.model, value=obj.model_dump(mode="json"))
        meta.task = task
        if failures:
            meta.note = f"{friendly(failures[-1].provider, failures[-1].kind)}, switched to {prov.capitalize() if prov != 'openrouter' else 'OpenRouter'}"
        return obj, _record(meta)

    if scope is not None and settings.allow_near_fallback:
        near = cache.nearest(task, scope)
        if near:
            try:
                obj = schema.model_validate(near["value"])
                why = "; ".join(friendly(f.provider, f.kind) for f in failures) or "replay mode"
                return obj, _record(CallMeta(provider="cache", model=near.get("model"), cached=True, task=task,
                                             note=f"{why}: used the closest cached answer"))
            except ValidationError:
                pass
    raise LLMUnavailable(_unavailable_message(mode, failures))


async def generate_text(task: str, prompt: str, tier: Tier = "fast", scope: str | None = None) -> tuple[str, CallMeta]:
    mode = settings.provider_mode
    key = make_key(task, prompt, "text")
    rec = cache.get(key) if mode in ("auto", "replay") else cache.get(key, provider=mode)
    if rec:
        return rec["value"], _record(CallMeta(provider="replay" if mode == "replay" else "cache", model=rec.get("model"),
                                              cached=True, task=task))
    failures: list[ProviderError] = []
    for prov in provider_chain(mode):
        if mode == "auto" and is_unhealthy(prov):
            continue
        t0 = time.perf_counter()
        try:
            text, info, n = await _call_provider(prov, prompt, tier, None)
        except ProviderError as e:
            if e.kind in ("quota", "auth", "server", "timeout"):
                mark_unhealthy(prov, e.kind)
            failures.append(e)
            continue
        cache.put(key, task=task, scope=scope, provider=prov, model=info.get("model"), value=text)
        return text, _record(CallMeta(provider=prov, model=info.get("model"), latency_ms=int((time.perf_counter() - t0) * 1000),
                                      input_tokens=info.get("input_tokens"), output_tokens=info.get("output_tokens"),
                                      attempts=n, task=task))
    if scope is not None and settings.allow_near_fallback:
        near = cache.nearest(task, scope)
        if near:
            return near["value"], _record(CallMeta(provider="cache", cached=True, task=task, note="closest cached answer"))
    raise LLMUnavailable(_unavailable_message(mode, failures))


async def stream_text(task: str, prompt: str, tier: Tier = "fast", scope: str | None = None,
                      meta_out: list | None = None) -> AsyncIterator[str]:
    """Streams text. Cached answers are re-streamed in small chunks so the UI behaves the same."""
    mode = settings.provider_mode
    key = make_key(task, prompt, "text")
    rec = cache.get(key) if mode in ("auto", "replay") else cache.get(key, provider=mode)
    if rec is None and not provider_chain(mode) and scope is not None:
        rec = cache.nearest(task, scope)
    if rec:
        if meta_out is not None:
            meta_out.append(CallMeta(provider="replay" if mode == "replay" else "cache", model=rec.get("model"), cached=True, task=task))
        text = rec["value"]
        for i in range(0, len(text), 12):
            yield text[i : i + 12]
            await asyncio.sleep(0.015)
        return
    failures: list[ProviderError] = []
    for prov in provider_chain(mode):
        if mode == "auto" and is_unhealthy(prov):
            continue
        parts: list[str] = []
        t0 = time.perf_counter()
        try:
            await LIMITERS[prov].wait()
            async for piece in PROVIDERS[prov].stream(prompt, tier):
                parts.append(piece)
                yield piece
        except ProviderError as e:
            if parts:  # already streaming: cannot switch provider mid-answer
                raise LLMUnavailable(f"{friendly(prov, e.kind)} while answering. Please ask again.") from e
            if e.kind in ("quota", "auth", "server", "timeout"):
                mark_unhealthy(prov, e.kind)
            failures.append(e)
            continue
        text = "".join(parts)
        cache.put(key, task=task, scope=scope, provider=prov, model=None, value=text)
        if meta_out is not None:
            note = f"{friendly(failures[-1].provider, failures[-1].kind)}, switched to OpenRouter" if failures else None
            meta_out.append(CallMeta(provider=prov, latency_ms=int((time.perf_counter() - t0) * 1000), task=task, note=note))
        return
    raise LLMUnavailable(_unavailable_message(mode, failures))


def _unavailable_message(mode: str, failures: list[ProviderError]) -> str:
    if mode == "replay":
        return "Replay mode has no cached answer for this step. Run scripts/warm_cache.py with a live provider first."
    if not failures:
        return "No LLM provider is configured. Add GEMINI_API_KEY (and optionally OpenRouter) to .env."
    parts = [friendly(f.provider, f.kind) for f in failures]
    if "openrouter" not in {f.provider for f in failures} and mode == "auto":
        parts.append("OpenRouter is not configured")
    return "; ".join(parts) + ", and no cached answer was available."


async def check_provider(provider: str) -> dict:
    """Tiny live call for the health endpoint. Never uses or writes the cache."""
    mod = PROVIDERS[provider]
    configured = settings.gemini_configured if provider == "gemini" else settings.openrouter_configured
    model = settings.gemini_model_fast if provider == "gemini" else settings.openrouter_model
    if not configured:
        return {"status": "not_configured", "model": model or None}
    t0 = time.perf_counter()
    try:
        await LIMITERS[provider].wait()
        text, _ = await mod.generate("Reply with the single word OK.", "fast", None)
    except ProviderError as e:
        status = {"quota": "quota", "auth": "bad_key"}.get(e.kind, "error")
        if status in ("quota", "bad_key"):
            mark_unhealthy(provider, e.kind)
        return {"status": status, "model": model, "message": e.message[:200]}
    _unhealthy_until.pop(provider, None)
    return {"status": "ok", "model": model, "latency_ms": int((time.perf_counter() - t0) * 1000)}
