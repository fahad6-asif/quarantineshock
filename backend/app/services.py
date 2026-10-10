"""Read-side helpers shared by routes, evals and scripts."""
from __future__ import annotations

import csv
import json
from datetime import date

from . import db
from .agent.nodes.shipments import load_shipments, zone_versions_from
from .config import DATA
from .matching import active_zones
from .rag import sources


def notice_index() -> list[dict]:
    done = db.latest_done_runs()
    out = []
    for n in sources.notices():
        r = done.get(n["id"])
        res = db.run_result(r) if r else {}
        out.append({
            "id": n["id"], "title": n["title"], "effective_date": n["effective_date"], "quarantine": n["quarantine"],
            "stated_area_sq_mi": n.get("stated_area_sq_mi"), "publisher": n.get("publisher"), "url": n.get("url"),
            "source_quality": n.get("source_quality", "primary"), "processed": bool(r), "run_id": r.id if r else None,
            "generated_area_sq_mi": (res.get("zone") or {}).get("area_sq_mi"),
            "counts": res.get("counts"),
            "sources": [{"title": s["title"], "url": s["url"], "published": s["published"]} for s in n.get("excerpt_of", [])],
        })
    return out


def result_for(notice_id: str) -> dict:
    r = db.latest_done_runs().get(notice_id)
    return db.run_result(r) if r else {}


def previous_notice_id(notice_id: str) -> str | None:
    ids = [n["id"] for n in sources.notices()]
    i = ids.index(notice_id)
    return ids[i - 1] if i > 0 else None


def _features(result: dict, on: date, role: str, current_q: str | None) -> list[dict]:
    vers = result.get("zone_versions") or []
    if not vers:
        return []
    act = active_zones(zone_versions_from(vers), on)
    keep = {(v.notice_id, v.quarantine) for v in act}
    feats = []
    for v in vers:
        if (v["notice_id"], v["quarantine"]) in keep:
            feats.append({"type": "Feature", "geometry": v["geojson"],
                          "properties": {"role": role, "quarantine": v["quarantine"], "notice_id": v["notice_id"],
                                         "effective_date": v["effective_date"], "area_sq_mi": v["area_sq_mi"],
                                         "current": v["quarantine"] == current_q}})
    return feats


def latest_decisions() -> dict[str, dict]:
    out = {}
    for d in db.decisions_for():
        out[d.shipment_id] = {"decision": d.decision, "note": d.note, "notice_id": d.notice_id,
                              "created_at": d.created_at.isoformat()}
    return out


def state_for(notice_id: str) -> dict:
    res = result_for(notice_id)
    if not res:
        return {"notice_id": notice_id, "processed": False}
    notice = res["notice"]
    eff = date.fromisoformat(notice["effective_date"])
    prev_id = previous_notice_id(notice_id)
    prev = result_for(prev_id) if prev_id else {}
    zones_now = _features(res, eff, "current", notice["quarantine"])
    zones_prev = _features(prev, date.fromisoformat(prev["notice"]["effective_date"]), "previous", None) if prev else []
    decisions = latest_decisions()
    ships = []
    for s in load_shipments():
        st = res["statuses"].get(s["id"], {})
        n = res["normalized"].get(s["id"], {})
        ships.append({**s, "status": st.get("status"), "previous_status": st.get("previous_status"),
                      "changed": st.get("changed_since_previous_notice", False),
                      "reasons": st.get("reasons", []), "distance_mi": st.get("distance_mi"),
                      "canonical_commodity": n.get("canonical_commodity"), "form": n.get("form"),
                      "confidence": n.get("confidence"), "host_status": n.get("host_status"),
                      "has_pack": s["id"] in (res.get("packs") or {}), "decision": decisions.get(s["id"])})
    return {
        "notice_id": notice_id, "processed": True, "run_id": res["run_id"], "notice": notice,
        "zones": {"type": "FeatureCollection", "features": zones_now},
        "previous_zones": {"type": "FeatureCollection", "features": zones_prev},
        "zone": {k: v for k, v in res["zone"].items() if k != "geojson"},
        "radius": res.get("radius"),
        "detections": res.get("detections", []),
        "shipments": ships, "counts": res.get("counts"), "summary": res.get("summary"),
        "grounding": res.get("grounding"), "warnings": res.get("warnings", []),
        "provider_mode": res.get("provider_mode"),
    }


def labels() -> tuple[dict[str, dict], bool]:
    path = DATA / "labels.csv"
    reviewed = False
    rows = {}
    with open(path, encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if line.startswith("#"):
                if i == 0 and line.lower().startswith("# reviewed_by_human:"):  # only the first line counts
                    reviewed = line.split(":", 1)[1].strip().lower() == "true"
                continue
            lines.append(line)
    for r in csv.DictReader(lines):
        rows[r["id"]] = r
    return rows, reviewed


def gold_rules() -> list[dict]:
    p = DATA / "gold_rules.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text("utf-8"))
    return [g for g in data.get("rules", []) if g.get("keywords")]
