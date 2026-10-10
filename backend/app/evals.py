"""Evaluation: normalizer vs labels.csv, rules vs gold_rules.json, citation grounding, zone area error."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import db, services
from .config import DATA

NON_FRESH = {"frozen", "processed", "dried", "mixed"}
CLASSES = ["host", "not_host", "unclear"]


def effective_host_status(n: dict) -> str:
    if n.get("form") in NON_FRESH or n.get("host_status") == "unclear":
        return "unclear"
    return n.get("host_status") or "unclear"


def run_evals() -> dict:
    done = db.latest_done_runs()
    results = [db.run_result(r) for r in done.values()]
    results.sort(key=lambda r: r["notice"]["effective_date"])
    latest = results[-1] if results else {}

    # 1. normalizer
    labels, reviewed = services.labels()
    norm = latest.get("normalized", {})
    confusion = {a: {b: 0 for b in CLASSES} for a in CLASSES}
    canon_ok = status_ok = n = 0
    rows = []
    for sid, lab in labels.items():
        got = norm.get(sid)
        if not got:
            continue
        n += 1
        pred = effective_host_status(got)
        confusion[lab["host_status"]][pred] += 1
        c_ok = got["canonical_commodity"] == lab["canonical_commodity"].strip().lower()
        s_ok = pred == lab["host_status"]
        canon_ok += c_ok
        status_ok += s_ok
        rows.append({"id": sid, "label": lab["canonical_commodity"], "predicted": got["canonical_commodity"],
                     "label_status": lab["host_status"], "predicted_status": pred, "form": got.get("form"),
                     "confidence": got.get("confidence"), "canonical_ok": c_ok, "status_ok": s_ok})
    normalizer = {"n": n, "canonical_accuracy": round(canon_ok / n, 3) if n else None,
                  "host_status_accuracy": round(status_ok / n, 3) if n else None,
                  "confusion": confusion, "rows": rows, "reviewed_by_human": reviewed,
                  "method": "exact match of canonical name; host status = code lookup in the official host lists, 'unclear' for frozen/processed/dried/mixed forms"}

    # 2. rule extraction vs gold rules (keyword method)
    gold = services.gold_rules()
    extracted = (latest.get("ruleset") or {}).get("rules", [])
    hay = [(r["id"], " ".join([r["requirement"], r["quote"], " ".join(r["applies_to"]), " ".join(r["exemptions"]),
                               " ".join(r["conditions"])]).lower()) for r in extracted]
    gold_rows = []
    for g in gold:
        kws = [k.lower() for k in g["keywords"]]
        hit = next((rid for rid, text in hay if all(k in text for k in kws)), None)
        gold_rows.append({"id": g.get("id"), "description": g.get("description", ""), "keywords": g["keywords"], "matched_rule": hit})
    rules = {"gold_count": len(gold), "matched": sum(1 for r in gold_rows if r["matched_rule"]), "rows": gold_rows,
             "extracted_count": len(extracted),
             "method": "keyword matching: a gold rule counts as found if one extracted rule contains all its keywords"}

    # 3. citation grounding across all runs
    tot = sum((r.get("grounding") or {}).get("total", 0) for r in results)
    ver = sum((r.get("grounding") or {}).get("verified", 0) for r in results)
    sup = sum((r.get("grounding") or {}).get("supports", 0) for r in results)
    judged = sum((r.get("grounding") or {}).get("judged", 0) for r in results)
    grounding = {"total": tot, "verified": ver, "supports": sup, "judged": judged,
                 "verified_pct": round(ver / tot * 100, 1) if tot else None,
                 "supports_pct": round(sup / judged * 100, 1) if judged else None,
                 "per_run": [{"notice_id": r["notice_id"], **(r.get("grounding") or {})} for r in results]}

    # 4. zone accuracy
    zones = [{"notice_id": r["notice_id"], "title": r["notice"]["title"], "effective_date": r["notice"]["effective_date"],
              "generated": r["zone"]["area_sq_mi"], "official": r["zone"]["official_sq_mi"],
              "error_pct": r["zone"]["error_pct"]} for r in results]

    out = {"computed_at": datetime.now(timezone.utc).isoformat(), "runs_evaluated": len(results),
           "normalizer": normalizer, "rules": rules, "grounding": grounding, "zones": zones,
           "radius": latest.get("radius")}
    (DATA / "eval_results.json").write_text(json.dumps(out, indent=2), "utf-8")
    return out


def load_evals() -> dict | None:
    p = DATA / "eval_results.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else None
