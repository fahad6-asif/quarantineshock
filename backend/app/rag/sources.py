"""Read the real documents in sources/ (header comments stripped) via manifest.json."""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import SOURCES


def read_body(rel: str) -> str:
    text = (SOURCES / rel).read_text("utf-8")
    marker = "# ---\n"
    i = text.find(marker)
    return text[i + len(marker):] if i >= 0 else text


@lru_cache(maxsize=1)
def manifest() -> list[dict]:
    return json.loads((SOURCES / "manifest.json").read_text("utf-8"))


def doc(doc_id: str) -> dict:
    for d in manifest():
        if d["id"] == doc_id:
            return d
    raise KeyError(doc_id)


def notices() -> list[dict]:
    return sorted((d for d in manifest() if d["type"] == "notice"), key=lambda d: d["effective_date"])


def rule_docs() -> list[dict]:
    return [d for d in manifest() if d["type"] != "notice"]


@lru_cache(maxsize=64)
def body(doc_id: str) -> str:
    return read_body(doc(doc_id)["file"])
