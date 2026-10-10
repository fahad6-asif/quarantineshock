"""Node 8: verify every quote against its source (code), then a light LLM judge (supports the claim?)."""
from __future__ import annotations

from ... import prompts
from ...llm import generate_json
from ...rag import retrieve, sources
from ...schemas import JudgeBatch
from ...verify import verify_quote
from ..context import RunContext


def _source_text(chunk_id: str | None) -> tuple[str, str | None]:
    """Chunk text, falling back to the whole document it belongs to."""
    if not chunk_id:
        return "", None
    chunk = retrieve.get_chunk(chunk_id)
    doc_id = chunk_id.split("#")[0]
    try:
        full = sources.body(doc_id)
    except KeyError:
        full = ""
    return (chunk["text"] if chunk else "") + "\n\n" + full, doc_id


async def verify_citations(state: dict, ctx: RunContext) -> dict:
    items = []  # (kind, id, claim, quote, source_text, holder)
    for i, d in enumerate(state["extract"]["detections"]):
        claim = f"Detection of {d.get('sex_status') or 'a fly'} in {d['place']} on {d.get('date')}: {d['detail']}"
        items.append(("detection", f"D{i + 1}", claim, d["quote"], ctx.notice_text, d))
    rs = state["ruleset"]
    for r in rs["rules"]:
        text, _ = _source_text(r["source_chunk_id"])
        items.append(("rule", r["id"], r["requirement"], r["quote"], text, r))
    for j, a in enumerate(rs["ambiguities"]):
        if a.get("quote"):
            text, _ = _source_text(a.get("source_chunk_id"))
            items.append(("ambiguity", f"A{j + 1}", a["explanation"], a["quote"], text, a))
    rad = state.get("radius") or {}
    if rad.get("quote"):
        text, _ = _source_text(rad.get("chunk_id"))
        items.append(("radius", "RADIUS", f"The quarantine radius is {rad['miles']} miles around detections", rad["quote"], text, rad))

    for kind, iid, claim, quote, src, holder in items:
        v = verify_quote(quote, src)
        holder["verification"] = {"verified": v["verified"], "score": v["score"], "judge": None}

    verified = [it for it in items if it[5]["verification"]["verified"]]
    if verified:
        lines = "\n".join(f'- id: {iid} | CLAIM: {claim} | QUOTE: "{quote}"' for _, iid, claim, quote, _, _ in verified)
        try:
            jb, _ = await generate_json("judge_citations", prompts.render("judge_citations", items=lines), JudgeBatch,
                                        "fast", scope=f"judge:{ctx.notice_id}")
            verdicts = {v.id: v.verdict for v in jb.verdicts}
        except Exception as e:  # noqa: BLE001  judge is advisory; verification above still stands
            ctx.warnings.append(f"citation judge unavailable: {e}")
            verdicts = {}
        for _, iid, _, _, _, holder in verified:
            holder["verification"]["judge"] = verdicts.get(iid)

    total = len(items)
    n_ver = len(verified)
    n_sup = sum(1 for it in verified if it[5]["verification"]["judge"] == "supports")
    n_judged = sum(1 for it in verified if it[5]["verification"]["judge"])
    unverified = [f"{k} {i}" for k, i, *_ , h in items if not h["verification"]["verified"]]
    grounding = {"total": total, "verified": n_ver, "supports": n_sup, "judged": n_judged, "unverified": unverified}
    return {"extract": state["extract"], "ruleset": rs, "radius": rad, "grounding": grounding,
            "_message": f"Citations verified: {n_ver}/{total} · Supports claim: {n_sup}/{n_judged or n_ver}",
            "_output": grounding}
