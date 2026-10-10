"""All HTTP endpoints (SPEC section 10)."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import db, evals, services
from .agent import graph as agent
from .agent.nodes.shipments import load_shipments
from .chat import SCRIPTED, answer_stream
from .config import PROVIDER_MODES, settings
from .events import existing
from .geo import zones as Z
from .llm import client as llm
from .matching import active_zones
from .rag import retrieve, sources
from .verify import normalize, verify_quote

router = APIRouter(prefix="/api")
_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    t = asyncio.create_task(coro)
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)


# ---------------------------------------------------------------- health + settings
@router.get("/health")
def health():
    return {"ok": True}


@router.get("/health/providers")
async def health_providers():
    g, o = await asyncio.gather(llm.check_provider("gemini"), llm.check_provider("openrouter"))
    return {"mode": settings.provider_mode, "gemini": g, "openrouter": o, "replay": {"status": "ok"},
            "health": llm.health_snapshot()}


@router.get("/settings")
def get_settings():
    return {"provider_mode": settings.provider_mode, "modes": list(PROVIDER_MODES),
            "gemini": {"configured": settings.gemini_configured, "model_fast": settings.gemini_model_fast,
                       "model_strong": settings.gemini_model_strong},
            "openrouter": {"configured": settings.openrouter_configured, "model": settings.openrouter_model or None},
            "radius_config_miles": settings.radius_miles_config, "health": llm.health_snapshot()}


class ProviderIn(BaseModel):
    mode: str


@router.post("/settings/provider")
def set_provider(body: ProviderIn):
    if body.mode not in PROVIDER_MODES:
        raise HTTPException(400, f"mode must be one of {PROVIDER_MODES}")
    settings.provider_mode = body.mode
    llm.reset_health()
    db.audit("provider_changed", body.mode, actor="user")
    return get_settings()


# ---------------------------------------------------------------- notices + runs
@router.get("/notices")
def notices():
    return services.notice_index()


def _highlights(text: str, extract: dict) -> list[dict]:
    """Character spans in the notice text for each extracted quote (for hover highlighting)."""
    spans = []
    low = text.lower()
    for i, d in enumerate(extract.get("detections", [])):
        q = (d.get("quote") or "").strip()
        j = low.find(q.lower()[:60]) if q else -1
        if j >= 0:
            end = low.find(q.lower()[-30:], j)
            spans.append({"field": f"detections[{i}]", "label": f"{d['place']} · {d.get('date') or ''}",
                          "start": j, "end": (end + 30) if end >= 0 else j + len(q),
                          "verified": (d.get("verification") or {}).get("verified")})
    for field, pat in (("stated_area_sq_mi", extract.get("stated_area_sq_mi")),
                       ("stated_commercial_acres", extract.get("stated_commercial_acres"))):
        if pat:
            s = f"{pat:g}"
            j = text.find(s)
            if j >= 0:
                spans.append({"field": field, "label": field.replace("_", " "), "start": j, "end": j + len(s), "verified": True})
    for crop in extract.get("crops_mentioned") or []:
        j = low.find(crop.lower())
        if j >= 0:
            spans.append({"field": "crops_mentioned", "label": crop, "start": j, "end": j + len(crop), "verified": True})
    return spans


@router.get("/notices/{notice_id}")
def notice_detail(notice_id: str):
    try:
        n = sources.doc(notice_id)
    except KeyError:
        raise HTTPException(404, "unknown notice")
    text = sources.body(notice_id)
    res = services.result_for(notice_id)
    ex = res.get("extract")
    return {"notice": n, "text": text, "extract": ex, "classification": res.get("classification"),
            "highlights": _highlights(text, ex) if ex else [], "processed": bool(res)}


class RunIn(BaseModel):
    notice_id: str


@router.post("/runs")
async def start_run(body: RunIn):
    try:
        run_id = agent.new_run(body.notice_id)
    except agent.OrderError as e:
        raise HTTPException(409, str(e))
    except KeyError:
        raise HTTPException(404, "unknown notice")
    _spawn(agent.execute(run_id, pace=True))
    return {"run_id": run_id}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    row = db.get_run(run_id)
    if row is None:
        raise HTTPException(404, "unknown run")
    ch = existing(run_id)

    async def gen():
        if ch is None:  # finished in an earlier server process: replay stored events
            for ev in json.loads(row.events_json or "[]"):
                yield {"event": "step", "data": json.dumps(ev, default=str)}
        else:
            async for ev in ch.subscribe():
                yield {"event": "step", "data": json.dumps(ev, default=str)}
        yield {"event": "end", "data": json.dumps({"run_id": run_id})}

    return EventSourceResponse(gen(), ping=10)


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    row = db.get_run(run_id)
    if row is None:
        raise HTTPException(404, "unknown run")
    return {"run_id": row.id, "notice_id": row.notice_id, "status": row.status, "error": row.error,
            "provider_mode": row.provider_mode, "created_at": row.created_at, "finished_at": row.finished_at,
            "events": json.loads(row.events_json or "[]"), "result": db.run_result(row) if row.status == "done" else None}


@router.get("/state")
def state(notice_id: str):
    return services.state_for(notice_id)


# ---------------------------------------------------------------- shipments
@router.get("/shipments/{shipment_id}")
def shipment_detail(shipment_id: str, notice_id: str):
    res = services.result_for(notice_id)
    if not res:
        raise HTTPException(404, "notice not processed yet")
    ship = next((s for s in load_shipments() if s["id"] == shipment_id), None)
    if ship is None:
        raise HTTPException(404, "unknown shipment")
    st = res["statuses"].get(shipment_id, {})
    n = res["normalized"].get(shipment_id, {})
    pack = (res.get("packs") or {}).get(shipment_id)
    rules = {r["id"]: r for r in res["ruleset"]["rules"]}
    evidence = []
    if pack:
        for rid in pack.get("rule_ids", []):
            r = rules.get(rid)
            if r:
                evidence.append({"kind": "rule", "id": rid, "claim": r["requirement"], "quote": r["quote"],
                                 "chunk_id": r["source_chunk_id"], "verification": r.get("verification"),
                                 "source": _source_meta(r["source_chunk_id"])})
    for code in (x["code"] for x in st.get("reasons", [])):
        if code == "FORM_AMBIGUOUS":
            for j, a in enumerate(res["ruleset"]["ambiguities"]):
                forms = {f.lower() for f in a.get("affected_forms", [])}
                if n.get("form") in forms or (n.get("form") == "processed" and forms & {"pulp", "juice", "canned"}):
                    if a.get("quote"):
                        evidence.append({"kind": "ambiguity", "id": f"A{j + 1}", "claim": a["explanation"], "topic": a["topic"],
                                         "quote": a["quote"], "chunk_id": a.get("source_chunk_id"),
                                         "verification": a.get("verification"), "source": _source_meta(a.get("source_chunk_id"))})
    if n.get("host_evidence"):
        doc_id = "mexfly_hosts" if n.get("federal_host") else "cdfa_3417"
        v = verify_quote(n["host_evidence"], sources.body(doc_id))
        evidence.append({"kind": "host_list", "id": "HOST", "claim": f"'{n['canonical_commodity']}' appears on the Mexfly host list",
                         "quote": n["host_evidence"], "chunk_id": None,
                         "verification": {"verified": v["verified"], "score": v["score"], "judge": None},
                         "source": {"title": sources.doc(doc_id)["title"], "url": sources.doc(doc_id).get("url"), "doc_id": doc_id}})
    # mini-map: zones active on the pickup date
    from datetime import date
    act = active_zones(agent_zone_versions(res), date.fromisoformat(ship["pickup_date"]))
    zones = [{"type": "Feature", "geometry": Z.to_geojson(v.geom_utm), "properties": {"quarantine": v.quarantine}} for v in act]
    history = [{"decision": d.decision, "note": d.note, "notice_id": d.notice_id, "created_at": d.created_at.isoformat()}
               for d in db.decisions_for(shipment_id)]
    return {"shipment": ship, "status": st, "normalized": n, "pack": pack, "evidence": evidence,
            "zones": {"type": "FeatureCollection", "features": zones}, "decisions": history, "notice_id": notice_id}


def agent_zone_versions(res):
    from .agent.nodes.shipments import zone_versions_from
    return zone_versions_from(res.get("zone_versions") or [])


def _source_meta(chunk_id: str | None) -> dict | None:
    if not chunk_id:
        return None
    doc_id = chunk_id.split("#")[0]
    try:
        d = sources.doc(doc_id)
    except KeyError:
        return None
    return {"title": d["title"], "url": d.get("url"), "doc_id": doc_id, "chunk_id": chunk_id}


class DecisionIn(BaseModel):
    decision: str
    notice_id: str
    note: str = ""


@router.post("/shipments/{shipment_id}/decision")
def decide(shipment_id: str, body: DecisionIn):
    if body.decision not in ("approve", "hold", "escalate"):
        raise HTTPException(400, "decision must be approve | hold | escalate")
    d = db.add_decision(db.DecisionRow(shipment_id=shipment_id, notice_id=body.notice_id, decision=body.decision,
                                       note=body.note.strip()[:1000]))
    label = {"approve": "approved review plan", "hold": "held shipment", "escalate": "escalated"}[body.decision]
    db.audit("decision", f"{shipment_id} {label} (notice {body.notice_id}) {body.note.strip()[:200]}", actor="user")
    return {"id": d.id, "shipment_id": shipment_id, "decision": d.decision, "note": d.note, "created_at": d.created_at.isoformat()}


# ---------------------------------------------------------------- chat + sources
class ChatIn(BaseModel):
    question: str


_chat_hits: dict[str, list[float]] = {}


def _chat_allowed(ip: str) -> bool:
    """Per-visitor hourly cap on chat questions (protects the API budget on public deployments)."""
    limit = settings.chat_limit_per_hour
    if limit <= 0:
        return True
    now = time.time()
    hits = [t for t in _chat_hits.get(ip, []) if now - t < 3600]
    if len(hits) >= limit:
        _chat_hits[ip] = hits
        return False
    _chat_hits[ip] = hits + [now]
    return True


@router.post("/chat")
async def chat(body: ChatIn, request: Request):
    q = body.question.strip()
    if not q:
        raise HTTPException(400, "empty question")
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    if q not in SCRIPTED and not _chat_allowed(ip):  # suggested questions are served from saved answers: free
        raise HTTPException(429, "Chat limit reached for this hour. The suggested questions still work from saved answers.")

    async def gen():
        async for ev in answer_stream(q[:500]):
            yield {"event": ev["type"], "data": json.dumps(ev, default=str)}

    return EventSourceResponse(gen(), ping=10)


@router.get("/chat/suggestions")
def chat_suggestions():
    return SCRIPTED


@router.get("/sources/{chunk_id:path}")
def source_passage(chunk_id: str):
    c = retrieve.get_chunk(chunk_id)
    if c is None:
        raise HTTPException(404, "unknown chunk")
    seq = c.get("seq", 0)
    doc_id = c["doc_id"]
    neighbours = [retrieve.get_chunk(f"{doc_id}#{i:03d}") for i in (seq - 1, seq + 1) if i >= 0]
    return {**c, "doc": sources.doc(doc_id), "before": (neighbours[0] or {}).get("text") if neighbours else None,
            "after": (neighbours[-1] or {}).get("text") if len(neighbours) > 1 else None}


@router.get("/sources")
def source_list():
    return sources.manifest()


# ---------------------------------------------------------------- evals
@router.post("/evals/run")
def evals_run():
    out = evals.run_evals()
    db.audit("evals_run", f"runs={out['runs_evaluated']}", actor="user")
    return out


@router.get("/evals")
def evals_get():
    # cheap (no LLM calls), so always computed fresh from the stored runs
    return evals.run_evals()


# ---------------------------------------------------------------- demo + audit
class ResetIn(BaseModel):
    fast_forward_to: str | None = None


_prep = {"running": False, "error": None, "done": None}


async def _fast_forward(until: str):
    _prep.update(running=True, error=None, done=None)
    try:
        ids = [n["id"] for n in sources.notices()]
        for nid in ids[: ids.index(until) + 1]:
            if nid not in db.latest_done_runs():
                await agent.run_notice(nid, pace=False)
        _prep["done"] = until
    except Exception as e:  # noqa: BLE001
        _prep["error"] = str(e)
    finally:
        _prep["running"] = False


@router.post("/demo/reset")
async def demo_reset(body: ResetIn | None = None):
    db.reset_demo()
    db.audit("demo_reset", "runs and decisions cleared (caches kept)", actor="user")
    if body and body.fast_forward_to:
        if body.fast_forward_to not in [n["id"] for n in sources.notices()]:
            raise HTTPException(404, "unknown notice")
        _spawn(_fast_forward(body.fast_forward_to))
    return {"ok": True, "fast_forward_to": body.fast_forward_to if body else None}


@router.get("/demo/status")
def demo_status():
    return {**_prep, "processed": sorted(db.latest_done_runs().keys())}


@router.get("/audit.csv")
def audit_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp_utc", "actor", "action", "detail"])
    for a in db.all_audit():
        w.writerow([a.created_at.isoformat(), a.actor, a.action, a.detail])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=quarantineshock_audit.csv"})


_ = normalize  # re-exported for tests
