import pytest
from pydantic import BaseModel

from app.config import settings
from app.llm import client
from app.llm.cache import LLMCache
from app.llm.errors import LLMUnavailable, ProviderError


class Small(BaseModel):
    answer: str
    n: int


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "cache", LLMCache(tmp_path / "llm"))
    monkeypatch.setattr(settings, "provider_mode", "auto")
    monkeypatch.setattr(settings, "gemini_rpm", 0)
    monkeypatch.setattr(settings, "openrouter_rpm", 0)
    client.reset_health()
    yield
    client.reset_health()


def fake(provider, outputs):
    """Provider stub returning items from `outputs` in order (Exception instances are raised)."""
    calls = {"n": 0}

    async def generate(prompt, tier, schema):
        i = min(calls["n"], len(outputs) - 1)
        calls["n"] += 1
        out = outputs[i]
        if isinstance(out, Exception):
            raise out
        return out, {"model": f"{provider}-test"}

    return generate, calls


@pytest.mark.asyncio
async def test_gemini_429_falls_back_to_openrouter(monkeypatch):
    g, gc = fake("gemini", [ProviderError("gemini", "quota", "429 RESOURCE_EXHAUSTED")])
    o, oc = fake("openrouter", ['{"answer": "ok", "n": 1}'])
    monkeypatch.setattr(client.gemini, "generate", g)
    monkeypatch.setattr(client.openrouter, "generate", o)
    obj, meta = await client.generate_json("t", "prompt-1", Small, scope="s")
    assert obj.answer == "ok" and meta.provider == "openrouter"
    assert "rate limit" in (meta.note or "") and "OpenRouter" in meta.note
    assert client.is_unhealthy("gemini")
    # second call skips Gemini entirely while it is unhealthy
    await client.generate_json("t", "prompt-2", Small, scope="s")
    assert gc["n"] == 1 and oc["n"] == 2


@pytest.mark.asyncio
async def test_gemini_timeout_switches_to_openrouter_without_waiting(monkeypatch):
    g, gc = fake("gemini", [ProviderError("gemini", "timeout", "read timed out")])
    o, oc = fake("openrouter", ['{"answer": "backup", "n": 7}'])
    monkeypatch.setattr(client.gemini, "generate", g)
    monkeypatch.setattr(client.openrouter, "generate", o)
    obj, meta = await client.generate_json("t", "slow-gemini", Small, scope="s")
    assert obj.answer == "backup" and meta.provider == "openrouter"
    assert gc["n"] == 1, "a timeout must not be retried on Gemini"
    assert "didn't answer in time" in meta.note
    assert client.is_unhealthy("gemini")


@pytest.mark.asyncio
async def test_both_down_uses_cache(monkeypatch):
    ok, _ = fake("gemini", ['{"answer": "first", "n": 1}'])
    monkeypatch.setattr(client.gemini, "generate", ok)
    await client.generate_json("t", "prompt-A", Small, scope="notice-1")
    down_g, _ = fake("gemini", [ProviderError("gemini", "quota", "429")])
    down_o, _ = fake("openrouter", [ProviderError("openrouter", "auth", "401")])
    monkeypatch.setattr(client.gemini, "generate", down_g)
    monkeypatch.setattr(client.openrouter, "generate", down_o)
    client.reset_health()
    # exact same prompt -> plain cache hit
    obj, meta = await client.generate_json("t", "prompt-A", Small, scope="notice-1")
    assert obj.answer == "first" and meta.cached
    # slightly different prompt, same task + scope -> closest cached answer, labelled
    obj, meta = await client.generate_json("t", "prompt-A (edited)", Small, scope="notice-1")
    assert obj.answer == "first" and meta.cached and "closest cached" in meta.note


@pytest.mark.asyncio
async def test_both_down_no_cache_raises_clear_error(monkeypatch):
    down_g, _ = fake("gemini", [ProviderError("gemini", "quota", "429")])
    down_o, _ = fake("openrouter", [ProviderError("openrouter", "not_configured", "no key")])
    monkeypatch.setattr(client.gemini, "generate", down_g)
    monkeypatch.setattr(client.openrouter, "generate", down_o)
    with pytest.raises(LLMUnavailable) as e:
        await client.generate_json("t", "never-seen", Small, scope="x")
    assert "Gemini hit its rate limit" in str(e.value)


@pytest.mark.asyncio
async def test_no_openrouter_key_gives_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    down_g, _ = fake("gemini", [ProviderError("gemini", "quota", "429")])
    monkeypatch.setattr(client.gemini, "generate", down_g)
    with pytest.raises(LLMUnavailable) as e:
        await client.generate_json("t", "never-seen-2", Small)
    assert "OpenRouter is not configured" in str(e.value)


@pytest.mark.asyncio
async def test_json_repair_retry(monkeypatch):
    g, gc = fake("gemini", ['```json\n{"answer": "x"}\n```', '```json\n{"answer": "fixed", "n": 2}\n```'])
    monkeypatch.setattr(client.gemini, "generate", g)
    obj, meta = await client.generate_json("t", "repair-me", Small)
    assert obj.n == 2 and gc["n"] == 2 and meta.attempts == 2


@pytest.mark.asyncio
async def test_replay_mode_never_calls_network(monkeypatch):
    ok, _ = fake("gemini", ['{"answer": "cached", "n": 3}'])
    monkeypatch.setattr(client.gemini, "generate", ok)
    await client.generate_json("t", "replay-me", Small)
    boom, bc = fake("gemini", [AssertionError("network used in replay")])
    monkeypatch.setattr(client.gemini, "generate", boom)
    monkeypatch.setattr(settings, "provider_mode", "replay")
    obj, meta = await client.generate_json("t", "replay-me", Small)
    assert obj.answer == "cached" and meta.provider == "replay" and bc["n"] == 0
    with pytest.raises(LLMUnavailable):
        await client.generate_json("t", "not-cached", Small)


@pytest.mark.asyncio
async def test_server_error_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(client.asyncio, "sleep", _nosleep)
    g, gc = fake("gemini", [ProviderError("gemini", "server", "503"), '{"answer": "ok", "n": 1}'])
    monkeypatch.setattr(client.gemini, "generate", g)
    obj, meta = await client.generate_json("t", "flaky", Small)
    assert obj.answer == "ok" and gc["n"] == 2 and meta.provider == "gemini"


async def _nosleep(*_a, **_k):
    return None
