from __future__ import annotations

from typing import Literal

Kind = Literal["quota", "auth", "server", "timeout", "not_configured", "bad_output", "other"]


class ProviderError(Exception):
    def __init__(self, provider: str, kind: Kind, message: str) -> None:
        super().__init__(f"{provider}: {kind}: {message}")
        self.provider = provider
        self.kind = kind
        self.message = message


class LLMUnavailable(Exception):
    """Raised when no provider and no cache can answer. Message is shown to the user as-is."""


def friendly(provider: str, kind: str) -> str:
    name = {"gemini": "Gemini", "openrouter": "OpenRouter"}.get(provider, provider)
    return {
        "quota": f"{name} hit its rate limit",
        "auth": f"{name} rejected the API key",
        "server": f"{name} is having server problems",
        "timeout": f"{name} didn't answer in time",
        "not_configured": f"{name} is not configured",
        "bad_output": f"{name} kept returning invalid JSON",
    }.get(kind, f"{name} failed")
