"""Nodes 9-10: draft action packs (batched) for flagged shipments; summarize the run."""
from __future__ import annotations

import hashlib
import json
import re

from ... import prompts
from ...config import CACHE_DIR, settings
from ...llm import generate_json, generate_text
from ...schemas import ActionBatch
from ..context import RunContext
from .shipments import load_shipments

PACKS_FILE = CACHE_DIR / "action_packs.json"
BANNED = re.compile(r"\b(cleared|approved for shipment|safe to ship|is safe|compliant)\b", re.I)


def _load_packs() -> dict:
    try:
        return json.loads(PACKS_FILE.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_packs(p: dict) -> None:
    PACKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PACKS_FILE.write_text(json.dumps(p, ensure_ascii=False), "utf-8")


def _fingerprint(ship: dict, st: dict, norm: dict, rules_txt: str) -> str:
    blob = json.dumps([ship, st["status"], [r["code"] for r in st["reasons"]], norm.get("canonical_commodity"),
                       norm.get("form"), rules_txt], sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


async def draft_actions(state: dict, ctx: RunContext) -> dict:
    ships = {s["id"]: s for s in load_shipments()}
    statuses, normalized = state["statuses"], state["normalized"]
    verified_rules = [r for r in state["ruleset"]["rules"] if r.get("verification", {}).get("verified")]
    rules_txt = "\n".join(f'- {r["id"]}: {r["requirement"]} (applies to: {", ".join(r["applies_to"])}; '
                          f'exemptions: {"; ".join(r["exemptions"]) or "none"}) QUOTE: "{r["quote"]}"' for r in verified_rules)
    amb_txt = "\n".join(f'- {a["topic"]}: {a["explanation"]} (forms: {", ".join(a["affected_forms"])})'
                        for a in state["ruleset"]["ambiguities"]) or "none"
    flagged = [sid for sid, st in statuses.items() if st["status"] in ("REVIEW", "UNCLEAR")]
    store = _load_packs()
    # an explicitly chosen live provider must really draft (proves that provider works end to end)
    reuse = settings.provider_mode in ("auto", "replay")
    packs, todo = {}, []
    for sid in flagged:
        fp = _fingerprint(ships[sid], statuses[sid], normalized.get(sid, {}), rules_txt)
        if reuse and fp in store:
            packs[sid] = store[fp]
        else:
            todo.append((sid, fp))
    reused = len(packs)
    if todo:
        lines = []
        for sid, _ in todo:
            s, st, n = ships[sid], statuses[sid], normalized.get(sid, {})
            reasons = " | ".join(r["text"] for r in st["reasons"])
            lines.append(f'- id: {sid} | status: {st["status"]} | label: "{s["product_raw"]}" -> {n.get("canonical_commodity", "?")} '
                         f'({n.get("form", "?")}) | pickup: {s["pickup_date"]} | origin: {s["origin_name"]} | '
                         f'destination: {s["destination"]} | reasons: {reasons}')
        batch, _ = await generate_json("draft_actions", prompts.render("draft_actions", rules=rules_txt or "none",
                                                                       ambiguities=amb_txt, shipments="\n".join(lines)),
                                       ActionBatch, "fast", scope=f"draft:{ctx.notice_id}")
        got = {p.shipment_id: p for p in batch.packs}
        valid_ids = {r["id"] for r in verified_rules}
        for sid, fp in todo:
            p = got.get(sid)
            if p is None:
                ctx.warnings.append(f"no draft returned for {sid}")
                continue
            d = p.model_dump(mode="json")
            d["rule_ids"] = [r for r in d["rule_ids"] if r in valid_ids]  # only verified rules may be cited
            store[fp] = d
            packs[sid] = d
        _save_packs(store)
    for sid, d in packs.items():
        text = " ".join([d["explanation"], d["email_body"], d["driver_hold_note"], *d["checklist"]])
        if BANNED.search(text):
            d["wording_warning"] = "Draft contains wording that implies certainty; edit before sending."
    return {"packs": packs, "_message": f"Drafted {len(packs)} action pack(s) for flagged loads"
            + (f" ({reused} reused, {len(todo)} new in 1 call)" if reused else ""),
            "_output": {k: {"explanation": v["explanation"], "rule_ids": v["rule_ids"]} for k, v in packs.items()}}


async def summarize(state: dict, ctx: RunContext) -> dict:
    c, z, g = state["counts"], state["zone"], state["grounding"]
    ex = state["extract"]
    facts = [
        f"Notice: {ctx.notice['title']} (effective {ctx.notice['effective_date']}).",
        f"Quarantine: {z['quarantine']}; generated zone {z['area_sq_mi']} sq mi; official {z['official_sq_mi']} sq mi.",
        f"Commercial agriculture stated in notice: {ex.get('stated_commercial_acres')} acres; crops: {', '.join(ex.get('crops_mentioned') or []) or 'none stated'}.",
        f"New detections in this notice: {', '.join(d['place'] for d in ex['detections']) or 'none'}.",
        f"Shipments: {c['REVIEW']} needs review, {c['UNCLEAR']} unclear (human check), {c['NOT_HOST']} no flag (not a host), {c['OUTSIDE']} no flag (outside zone).",
        f"Newly flagged since the previous notice: {c['newly_flagged']} ({', '.join(c['newly_flagged_ids']) or 'none'}).",
        f"Citations verified: {g['verified']}/{g['total']}.",
    ]
    text, _ = await generate_text("summarize", prompts.render("summarize", facts="\n".join(facts)), "fast",
                                  scope=f"summary:{ctx.notice_id}")
    return {"summary": text.strip(), "_message": "Run summary ready", "_output": {"summary": text.strip()}}
