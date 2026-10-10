"""LangGraph wiring: 10 nodes in sequence, each wrapped to stream SSE events and report its provider."""
from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .. import db
from ..config import settings
from ..events import channel
from ..llm import LLMUnavailable
from ..llm.client import start_collecting
from ..rag import sources
from . import nodes
from .context import RunContext

NODE_ORDER = [
    ("classify_notice", nodes.classify_notice, "Reading the notice: is this a quarantine change?"),
    ("extract_notice", nodes.extract_notice, "Extracting detections, area and crops from the notice text"),
    ("geocode_detections", nodes.geocode_detections, "Locating detection sites"),
    ("build_zone", nodes.build_zone, "Drawing the quarantine zone"),
    ("extract_rules", nodes.extract_rules, "Reading the regulations and host list (RAG)"),
    ("normalize_shipments", nodes.normalize_shipments, "Matching messy product labels to commodities"),
    ("match", nodes.match, "Checking every scheduled pickup against the zone (deterministic code)"),
    ("verify_citations", nodes.verify_citations, "Verifying every quote against the source documents"),
    ("draft_actions", nodes.draft_actions, "Drafting review checklists, emails and driver notes"),
    ("summarize", nodes.summarize, "Writing the run summary"),
]
NODE_NAMES = [n for n, _, _ in NODE_ORDER]
AI_NODES = {"classify_notice", "extract_notice", "extract_rules", "normalize_shipments", "verify_citations",
            "draft_actions", "summarize", "build_zone"}


class AgentState(TypedDict, total=False):
    ctx: Any
    classification: dict
    extract: dict
    detections: list
    radius: dict
    zone: dict
    zone_versions: list
    ruleset: dict
    normalized: dict
    statuses: dict
    counts: dict
    grounding: dict
    packs: dict
    summary: str
    node_meta: dict


def _aggregate(metas) -> dict | None:
    if not metas:
        return None
    provs = [m.provider for m in metas]
    live = [m for m in metas if not m.cached]
    lead = live[-1] if live else metas[-1]
    return {"provider": lead.provider if len(set(provs)) == 1 else "+".join(sorted(set(provs))),
            "model": lead.model, "cached": all(m.cached for m in metas), "calls": len(metas),
            "latency_ms": sum(m.latency_ms for m in metas),
            "input_tokens": sum(m.input_tokens or 0 for m in metas) or None,
            "output_tokens": sum(m.output_tokens or 0 for m in metas) or None,
            "attempts": sum(m.attempts for m in metas),
            "notes": [m.note for m in metas if m.note]}


def _wrap(name: str, fn, start_msg: str):
    async def run(state: AgentState) -> dict:
        ctx: RunContext = state["ctx"]
        await ctx.channel.emit(name, "started", start_msg, prompt=name if name in AI_NODES else None)
        metas = start_collecting()
        t0 = time.perf_counter()
        try:
            update = await fn(state, ctx)
        except LLMUnavailable as e:
            await ctx.channel.emit(name, "error", str(e), meta=_aggregate(metas), toast=str(e))
            raise
        except Exception as e:  # noqa: BLE001
            await ctx.channel.emit(name, "error", f"{type(e).__name__}: {e}", meta=_aggregate(metas),
                                   toast=f"Step '{name}' failed: {e}")
            raise
        agg = _aggregate(metas)
        for note in (agg or {}).get("notes", []):
            await ctx.channel.emit(name, "progress", note, toast=note)
        if ctx.pace and (agg is None or agg["cached"]):
            await asyncio.sleep(settings.replay_delay * random.uniform(0.7, 1.3))
        msg = update.pop("_message", "")
        output = update.pop("_output", None)
        elapsed = int((time.perf_counter() - t0) * 1000)
        await ctx.channel.emit(name, "done", msg, meta=agg, output=output, elapsed_ms=elapsed)
        node_meta = dict(state.get("node_meta") or {})
        node_meta[name] = {"message": msg, "meta": agg, "elapsed_ms": elapsed, "output": output}
        update["node_meta"] = node_meta
        return update

    return run


def build_graph():
    g = StateGraph(AgentState)
    for name, fn, msg in NODE_ORDER:
        g.add_node(name, _wrap(name, fn, msg))
    g.add_edge(START, NODE_NAMES[0])
    for a, b in zip(NODE_NAMES, NODE_NAMES[1:]):
        g.add_edge(a, b)
    g.add_edge(NODE_NAMES[-1], END)
    return g.compile()


_GRAPH = None


def graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


# ---------------------------------------------------------------- run orchestration
class OrderError(Exception):
    pass


def prior_results(notice_id: str) -> list[dict]:
    order = [n["id"] for n in sources.notices()]
    if notice_id not in order:
        raise KeyError(notice_id)
    done = db.latest_done_runs()
    out = []
    for nid in order[: order.index(notice_id)]:
        if nid not in done:
            raise OrderError(f"Process the earlier notice '{nid}' first.")
        out.append(db.run_result(done[nid]))
    return out


_RUN_LOCK = asyncio.Lock()


def new_run(notice_id: str) -> str:
    prior_results(notice_id)  # validates order before we create anything
    run_id = f"run_{notice_id[:10]}_{uuid.uuid4().hex[:6]}"
    db.save_run(db.RunRow(id=run_id, notice_id=notice_id, provider_mode=settings.provider_mode))
    channel(run_id)
    return run_id


async def execute(run_id: str, pace: bool = True) -> dict:
    row = db.get_run(run_id)
    ch = channel(run_id)
    async with _RUN_LOCK:  # one run at a time: runs depend on earlier runs
        notice = next(n for n in sources.notices() if n["id"] == row.notice_id)
        ctx = RunContext(run_id=run_id, notice=notice, notice_text=sources.body(notice["id"]),
                         prev_results=prior_results(notice["id"]), channel=ch, pace=pace)
        await ch.emit("run", "started", f"New notice received: {notice['title']} ({notice['effective_date']})",
                      notice_id=notice["id"], provider_mode=settings.provider_mode)
        try:
            final = await graph().ainvoke({"ctx": ctx})
        except Exception as e:  # noqa: BLE001
            row.status, row.error, row.finished_at = "error", str(e), db.now()
            row.events_json = json.dumps(ch.events, default=str)
            db.save_run(row)
            db.audit("run_failed", f"{run_id} {notice['id']}: {e}")
            await ch.emit("run", "error", str(e), toast=str(e))
            await ch.close()
            return {}
        result = {k: v for k, v in final.items() if k != "ctx"}
        result.update({"run_id": run_id, "notice_id": notice["id"], "notice": notice, "warnings": ctx.warnings,
                       "provider_mode": row.provider_mode})
        await ch.emit("run", "done", final.get("summary", ""), counts=final.get("counts"),
                      grounding=final.get("grounding"), warnings=ctx.warnings)
        row.status, row.finished_at = "done", db.now()
        row.result_json = json.dumps(result, default=str)
        row.events_json = json.dumps(ch.events, default=str)
        db.save_run(row)
        db.audit("run_done", f"{run_id} {notice['id']}: {final.get('counts')}")
        await ch.close()
        return result


async def run_notice(notice_id: str, pace: bool = False) -> dict:
    """Convenience for scripts/tests: create + execute synchronously."""
    rid = new_run(notice_id)
    res = await execute(rid, pace=pace)
    if not res:
        raise RuntimeError(db.get_run(rid).error)
    return res
