"""Prompt templates live as Markdown next to this file. Variables use $name (string.Template)."""
from __future__ import annotations

from pathlib import Path
from string import Template

_DIR = Path(__file__).resolve().parent


def render(name: str, **values) -> str:
    text = (_DIR / f"{name}.md").read_text("utf-8")
    return Template(text).safe_substitute({k: str(v) for k, v in values.items()})
