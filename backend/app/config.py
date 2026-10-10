"""Settings loaded from the repo-root .env. Provider mode can be switched at runtime."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCES = ROOT / "sources"
DATA = ROOT / "data"
CACHE_DIR = BACKEND / ".cache"
LLM_CACHE = CACHE_DIR / "llm"
STATE_DIR = BACKEND / "data"  # sqlite + chroma (git-ignored)
PROMPTS = Path(__file__).resolve().parent / "prompts"

load_dotenv(ROOT / ".env")

PROVIDER_MODES = ("auto", "gemini", "openrouter", "replay")


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name) or default)
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        load_dotenv(ROOT / ".env", override=True)
        mode = (os.getenv("LLM_PROVIDER") or "auto").strip().lower()
        self.provider_mode = mode if mode in PROVIDER_MODES else "auto"
        self.gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.gemini_model_fast = (os.getenv("GEMINI_MODEL_FAST") or "gemini-3.5-flash-lite").strip()
        self.gemini_model_strong = (os.getenv("GEMINI_MODEL_STRONG") or "gemini-3.5-flash").strip()
        self.gemini_rpm = _f("GEMINI_RPM", 10)
        self.gemini_timeout_s = _f("GEMINI_TIMEOUT_S", 90)
        self.gemini_model_backup = (os.getenv("GEMINI_MODEL_BACKUP") or "gemini-2.5-flash").strip()
        self.chat_limit_per_hour = int(_f("CHAT_LIMIT_PER_HOUR", 0))  # 0 = unlimited (local); set on public deploys
        # last-resort "closest cached answer" fallback; warm_cache.py turns it off so stale answers never get cached as fresh
        self.allow_near_fallback = True
        self.openrouter_api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        self.openrouter_model = (os.getenv("OPENROUTER_MODEL") or "openai/gpt-oss-120b").strip()
        self.openrouter_rpm = _f("OPENROUTER_RPM", 20)
        self.radius_miles_config = _f("QUARANTINE_RADIUS_MILES", 4.5)
        # demo pacing: small delays so the Agent Activity stepper is watchable when answers come from cache
        self.replay_delay = _f("REPLAY_STEP_DELAY", 0.6)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_model_fast)

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_model)


settings = Settings()
