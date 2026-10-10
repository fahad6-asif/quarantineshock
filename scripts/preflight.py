"""Checks keys, providers, geocoder, Chroma index and data files. Prints a plain checklist.

Usage: python scripts/preflight.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

OK, WARN, BAD = "OK  ", "WARN", "FAIL"
problems = 0


def line(tag: str, msg: str) -> None:
    global problems
    if tag == BAD:
        problems += 1
    print(f"[{tag}] {msg}")


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from app.config import DATA, SOURCES, settings
    from app.llm import client

    line(OK if (ROOT / ".env").exists() else BAD, ".env present")
    line(OK if settings.gemini_api_key else BAD, f"GEMINI_API_KEY {'set' if settings.gemini_api_key else 'missing'}"
         f" (models: fast={settings.gemini_model_fast or '?'}, strong={settings.gemini_model_strong or '?'})")
    if settings.openrouter_api_key and not settings.openrouter_model:
        line(WARN, "OPENROUTER_API_KEY set but OPENROUTER_MODEL empty (pick a model, SPEC 6.3)")
    elif settings.openrouter_configured:
        line(OK, f"OpenRouter configured: {settings.openrouter_model}")
    else:
        line(WARN, "OpenRouter not configured (fallback disabled)")
    line(OK, f"LLM_PROVIDER={settings.provider_mode}")

    for p in ("gemini", "openrouter"):
        r = await client.check_provider(p)
        tag = OK if r["status"] == "ok" else (WARN if r["status"] == "not_configured" else BAD)
        if p == "openrouter" and r["status"] != "ok":
            tag = WARN
        line(tag, f"{p}: {r['status']}" + (f" ({r.get('latency_ms')} ms)" if r.get("latency_ms") else "")
             + (f" - {r.get('message')}" if r.get("message") else ""))

    man = SOURCES / "manifest.json"
    if man.exists():
        m = json.loads(man.read_text("utf-8"))
        line(OK, f"sources/manifest.json: {sum(d['type'] == 'notice' for d in m)} notices, {len(m)} documents")
    else:
        line(BAD, "sources/manifest.json missing (run scripts/ingest.py)")

    try:
        from app.rag import store
        n = store.collection(store.RULEBOOK).count()
        line(OK if n else BAD, f"Chroma rulebook index: {n} chunks")
    except Exception as e:  # noqa: BLE001
        line(BAD, f"Chroma index unavailable: {e}")

    for f in ("shipments.json", "host_table.json", "labels.csv", "geocode_cache.json", "fallback_geocodes.json"):
        line(OK if (DATA / f).exists() else BAD, f"data/{f}")
    from app.services import labels
    reviewed = labels()[1]
    line(OK if reviewed else WARN, "labels.csv reviewed by a human" if reviewed
         else "labels.csv not yet reviewed by Fahad (evals will say so)")
    gold = DATA / "gold_rules.json"
    n_gold = len([g for g in json.loads(gold.read_text("utf-8")).get("rules", []) if g.get("keywords")]) if gold.exists() else 0
    line(OK if n_gold >= 6 else WARN, f"gold_rules.json: {n_gold} rules written by Fahad")

    from app.geo.geocode import geocode_sync
    g = geocode_sync("El Cajon")
    line(OK if g else BAD, f"geocoder: El Cajon -> {g['lat']}, {g['lon']} ({g.get('source', 'cache')})" if g else "geocoder failed")

    print("\nAll good." if not problems else f"\n{problems} problem(s) above need fixing.")


if __name__ == "__main__":
    asyncio.run(main())
