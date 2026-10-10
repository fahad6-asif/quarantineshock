"""Disk cache for LLM responses.

One file per key (sha256 of task + prompt + schema name, provider-agnostic). Each file keeps the
latest answer per provider so `LLM_PROVIDER=openrouter` can prove OpenRouter works on its own
while `auto` / `replay` reuse whichever answer is newest.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ..config import LLM_CACHE


def make_key(task: str, prompt: str, schema_name: str) -> str:
    return hashlib.sha256(f"{task}\x1f{schema_name}\x1f{prompt}".encode("utf-8")).hexdigest()


class LLMCache:
    def __init__(self, root: Path = LLM_CACHE) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str, provider: str | None = None) -> dict | None:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            entry = json.loads(p.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if provider:
            return entry.get("by_provider", {}).get(provider)
        return entry.get("by_provider", {}).get(entry.get("latest", ""))

    def put(self, key: str, *, task: str, scope: str | None, provider: str, model: str | None, value: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        p = self._path(key)
        entry: dict = {}
        if p.exists():
            try:
                entry = json.loads(p.read_text("utf-8"))
            except (OSError, json.JSONDecodeError):
                entry = {}
        rec = {"provider": provider, "model": model, "value": value, "created": time.time()}
        entry.update({"key": key, "task": task, "scope": scope, "latest": provider})
        entry.setdefault("by_provider", {})[provider] = rec
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, ensure_ascii=False), "utf-8")
        tmp.replace(p)

    def nearest(self, task: str, scope: str | None) -> dict | None:
        """Most recent cached answer for the same task (+ scope). Used only as a last-resort fallback."""
        if not self.root.exists():
            return None
        best, best_t = None, -1.0
        for p in self.root.glob("*.json"):
            try:
                entry = json.loads(p.read_text("utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if entry.get("task") != task or (scope is not None and entry.get("scope") != scope):
                continue
            rec = entry.get("by_provider", {}).get(entry.get("latest", ""))
            if rec and rec.get("created", 0) > best_t:
                best, best_t = rec, rec["created"]
        return best


cache = LLMCache()
