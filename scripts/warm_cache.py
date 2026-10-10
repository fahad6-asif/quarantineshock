"""Run every notice through the full agent once (fills the LLM cache), plus the 5 scripted chat
questions, then print a plain status table. After this, LLM_PROVIDER=replay works with zero network.

Usage: python scripts/warm_cache.py [--provider auto|gemini|openrouter|replay] [--until NOTICE_ID] [--no-chat] [--keep]
  --keep   do not reset existing runs first
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

STATUS_SHORT = {"REVIEW": "REVIEW", "UNCLEAR": "UNCLR", "NOT_HOST": "nohost", "OUTSIDE": "out", None: "-"}


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider")
    ap.add_argument("--until")
    ap.add_argument("--no-chat", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    from app import db
    from app.agent import graph as agent
    from app.chat import SCRIPTED, answer_stream
    from app.config import settings
    from app.rag import sources

    from app.llm import client as llm_client

    db.init()
    if a.provider:
        settings.provider_mode = a.provider
    settings.allow_near_fallback = settings.provider_mode == "replay"
    print(f"Provider mode: {settings.provider_mode}")
    if not a.keep:
        db.reset_demo()
    ids = [n["id"] for n in sources.notices()]
    if a.until:
        ids = ids[: ids.index(a.until) + 1]
    results = []
    done = db.latest_done_runs()
    for nid in ids:
        if a.keep and nid in done:
            results.append(db.run_result(done[nid]))
            continue
        print(f"\n=== {nid}")
        llm_client.reset_health()  # a transient overload on the previous notice should not skip Gemini here
        rid = agent.new_run(nid)
        res = await agent.execute(rid, pace=False)
        from app.events import channel
        for ev in channel(rid).events:
            if ev["status"] in ("done", "error") and ev["node"] != "run":
                m = ev.get("meta") or {}
                prov = (m.get("provider") or "code") + (" (cached)" if m.get("cached") else "")
                print(f"  {ev['node']:<20} {ev['status']:<5} [{prov}] {ev['message']}")
        if not res:
            print(f"  RUN FAILED: {db.get_run(rid).error}")
            print(f"  provider detail: {llm_client.health_snapshot()}")
            print("  Re-run with --keep to continue from this notice.")
            sys.exit(1)
        for w in res.get("warnings", []):
            print(f"  warning: {w}")
        results.append(res)

    # status table
    print("\nStatus per notice (pickup-date aware):")
    hdr = f"{'id':<8} {'label':<34} {'pickup':<10} " + " ".join(f"{r['notice']['effective_date'][5:]:>7}" for r in results)
    print(hdr)
    for sid in sorted(results[-1]["statuses"]):
        s = next(x for x in results[-1]["statuses"].items() if x[0] == sid)
        from app.agent.nodes.shipments import load_shipments
        ship = next(x for x in load_shipments() if x["id"] == sid)
        row = f"{sid:<8} {ship['product_raw'][:34]:<34} {ship['pickup_date']:<10} "
        cells = []
        for r in results:
            st = r["statuses"][sid]
            cells.append(f"{STATUS_SHORT[st['status']] + ('*' if st['changed_since_previous_notice'] else ''):>7}")
        print(row + " ".join(cells))
    print("(* = changed with that notice)")
    for r in results:
        c, z, g = r["counts"], r["zone"], r["grounding"]
        print(f"{r['notice']['effective_date']}  zone {z['area_sq_mi']:>6} vs {z['official_sq_mi']} sq mi ({z['error_pct']:+}%)  "
              f"newly flagged {c['newly_flagged']}  citations {g['verified']}/{g['total']} supports {g['supports']}/{g['judged']}")

    if not a.no_chat:
        print("\nWarming chat answers:")
        for q in SCRIPTED:
            final = None
            async for ev in answer_stream(q):
                if ev["type"] in ("done", "error"):
                    final = ev
            if final["type"] == "error":
                print(f"  FAIL {q}: {final['message']}")
                continue
            ver = sum(x["verified"] for x in final["quotes"])
            print(f"  OK   {q}  -> {len(final['citations'])} citations, quotes verified {ver}/{len(final['quotes'])}"
                  + ("  [certainty warning]" if final["certainty_warning"] else ""))
    from app.evals import run_evals
    run_evals()
    print("\nCache warm. Replay mode (LLM_PROVIDER=replay) will now work offline.")


if __name__ == "__main__":
    asyncio.run(main())
