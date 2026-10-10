"""Nodes 6-7: normalize messy labels (embeddings + one batched LLM call), then deterministic matching."""
from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from ... import prompts
from ...config import DATA
from ...geo import zones as Z
from ...llm import generate_json
from ...matching import Normalized, ZoneVersion, match_all
from ...rag import retrieve
from ...schemas import NormalizedBatch
from ..context import RunContext

FORM_ALIASES = {"pulp": "processed", "juice": "processed", "canned": "processed", "puree": "processed"}


def load_shipments() -> list[dict]:
    return json.loads((DATA / "shipments.json").read_text("utf-8"))["shipments"]


@lru_cache(maxsize=1)
def host_table() -> dict:
    return json.loads((DATA / "host_table.json").read_text("utf-8"))


async def normalize_shipments(state: dict, ctx: RunContext) -> dict:
    ships = load_shipments()
    lines, cands = [], {}
    batch_cands = retrieve.commodity_candidates_batch([s["product_raw"] for s in ships], k=5)
    for s, c in zip(ships, batch_cands):
        cands[s["id"]] = c
        lines.append(f'- id: {s["id"]} | label: "{s["product_raw"]}" | candidates: {", ".join(x["canonical"] for x in c)}')
    batch, _ = await generate_json("normalize_shipments", prompts.render("normalize_shipments", items="\n".join(lines)),
                                   NormalizedBatch, "fast", scope="normalize")
    by_id = {it.id: it for it in batch.items}
    table = host_table()
    out = {}
    for s in ships:
        it = by_id.get(s["id"])
        if it is None:
            continue
        canon = it.canonical_commodity.strip().lower()
        row = table.get(canon)
        # AI identifies the product; code decides host status from the real host lists.
        host = ("host" if row["host"] else "not_host") if row else "unclear"
        out[s["id"]] = {**it.model_dump(mode="json"), "canonical_commodity": canon, "llm_host_status": it.host_status,
                        "host_status": host, "host_source": "official host lists" if row else "not in vocabulary",
                        "federal_host": row["federal"] if row else None, "state_host": row["state"] if row else None,
                        "host_evidence": (row["federal_evidence"] or row["state_evidence"]) if row else None,
                        "candidates": cands[s["id"]]}
    low = sum(1 for v in out.values() if v["confidence"] < 0.7)
    missing = len(ships) - len(out)
    msg = f"Normalized {len(out)} labels in 1 batched call · {low} low-confidence"
    if missing:
        msg += f" · {missing} not returned"
    return {"normalized": out, "_message": msg,
            "_output": {k: {f: v[f] for f in ("canonical_commodity", "form", "host_status", "confidence")} for k, v in out.items()}}


def zone_versions_from(result_versions: list[dict]) -> list[ZoneVersion]:
    from datetime import date

    return [ZoneVersion(notice_id=v["notice_id"], quarantine=v["quarantine"],
                        effective_date=date.fromisoformat(v["effective_date"]),
                        geom_utm=Z.from_geojson(v["geojson"]), supersedes=v.get("supersedes") or [])
            for v in result_versions]


def ambiguous_forms(ruleset: dict) -> set[str]:
    forms = set()
    for a in ruleset.get("ambiguities", []):
        for f in a.get("affected_forms", []):
            f = f.strip().lower()
            forms.add(FORM_ALIASES.get(f, f))
    forms.discard("fresh")  # fresh host fruit is the baseline regulated article, never "ambiguous"
    return forms


def exemptions(ruleset: dict) -> list[dict]:
    """Exemption text from rules whose quote is verbatim in the source. An exemption from a rule with an
    unverifiable quote is never allowed to influence a status."""
    from ...verify import verify_quote
    from .citations import _source_text

    out = []
    for r in ruleset.get("rules", []):
        if not r.get("exemptions"):
            continue
        if not verify_quote(r["quote"], _source_text(r["source_chunk_id"])[0])["verified"]:
            continue
        out += [{"rule_id": r["id"], "text": e} for e in r["exemptions"] if e]
    return out


async def match(state: dict, ctx: RunContext) -> dict:
    ships = load_shipments()
    norm = {k: Normalized(v["canonical_commodity"], v["form"], v["host_status"], v["confidence"])
            for k, v in state["normalized"].items()}
    prev = {k: v["status"] for k, v in (ctx.previous or {}).get("statuses", {}).items()}
    res = match_all(ships, norm, zone_versions_from(state["zone_versions"]), ambiguous_forms(state["ruleset"]),
                    exemptions(state["ruleset"]), prev or None)
    counts = Counter(r["status"] for r in res.values())
    flagged = {"REVIEW", "UNCLEAR"}
    newly = [k for k, r in res.items() if r["status"] in flagged and (r["previous_status"] not in flagged)
             and r["previous_status"] is not None]
    if not prev:
        newly = []
    summary = {"REVIEW": counts.get("REVIEW", 0), "UNCLEAR": counts.get("UNCLEAR", 0),
               "NOT_HOST": counts.get("NOT_HOST", 0), "OUTSIDE": counts.get("OUTSIDE", 0),
               "newly_flagged": len(newly), "newly_flagged_ids": newly,
               "changed": sum(1 for r in res.values() if r["changed_since_previous_notice"])}
    msg = (f"{summary['REVIEW']} needs review · {summary['UNCLEAR']} unclear · {summary['NOT_HOST']} not host · "
           f"{summary['OUTSIDE']} outside")
    if prev:
        msg += f" · {len(newly)} newly flagged"
    return {"statuses": res, "counts": summary, "_message": msg,
            "_output": {k: {"status": v["status"], "changed": v["changed_since_previous_notice"]} for k, v in res.items()}}
