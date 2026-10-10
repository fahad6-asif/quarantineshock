"""Deterministic shipment status logic. No LLM decides whether a shipment is flagged.

Inputs are plain data: shipments, normalized commodities (host status already looked up in the
real host lists by code), zone versions, and the rule set's ambiguities/exemptions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .geo import zones as Z

CONFIDENCE_MIN = 0.7
NON_FRESH = {"frozen", "dried", "processed", "canned"}


@dataclass
class ZoneVersion:
    notice_id: str
    quarantine: str
    effective_date: date
    geom_utm: object
    supersedes: list[str] = field(default_factory=list)


@dataclass
class Normalized:
    canonical_commodity: str
    form: str
    host_status: str  # host | not_host | unclear
    confidence: float


def active_zones(versions: list[ZoneVersion], on: date) -> list[ZoneVersion]:
    """Latest version per quarantine with effective_date <= on, minus quarantines merged away."""
    latest: dict[str, ZoneVersion] = {}
    for v in sorted(versions, key=lambda v: (v.effective_date, v.notice_id)):
        if v.effective_date <= on:
            latest[v.quarantine] = v
    merged_away = {q for v in latest.values() for q in v.supersedes if q != v.quarantine}
    return [v for q, v in latest.items() if q not in merged_away]


def _valid_coords(lat, lon) -> bool:
    return (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
            and -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0))


def _tokens(*texts: str) -> set[str]:
    return {t for s in texts for t in re.findall(r"[a-z]{4,}", (s or "").lower())}


def match_one(shipment: dict, norm: Normalized | None, versions: list[ZoneVersion],
              ambiguous_forms: set[str], exemptions: list[dict]) -> dict:
    """Return {status, reasons[], zone_notice_ids[], distance_mi}. reasons = [{code, text}]."""
    reasons: list[dict] = []
    pickup = shipment["pickup_date"]
    if isinstance(pickup, str):
        pickup = date.fromisoformat(pickup)
    lat, lon = shipment.get("lat"), shipment.get("lon")

    if not _valid_coords(lat, lon):
        reasons.append({"code": "BAD_COORDS", "text": "Origin coordinates are missing or invalid, so the zone check cannot run."})
        return {"status": "UNCLEAR", "reasons": reasons, "zone_notice_ids": [], "distance_mi": None}

    act = active_zones(versions, pickup)
    inside = [v for v in act if Z.contains(v.geom_utm, lat, lon)]
    dist = None
    if act:
        dist = max(Z.distance_to_edge_mi(v.geom_utm, lat, lon) for v in act)
        dist = round(dist, 2)
    if not inside:
        if act:
            reasons.append({"code": "OUTSIDE_ZONE", "text": f"Origin is {abs(dist):.1f} mi outside the active quarantine zone(s) on the pickup date {pickup.isoformat()}."})
        else:
            reasons.append({"code": "NO_ACTIVE_ZONE", "text": f"No quarantine was in effect on the pickup date {pickup.isoformat()}."})
        return {"status": "OUTSIDE", "reasons": reasons, "zone_notice_ids": [], "distance_mi": dist}

    names = ", ".join(sorted({v.quarantine for v in inside}))
    reasons.append({"code": "INSIDE_ZONE", "text": f"Origin is {dist:.1f} mi inside the {names} quarantine zone on the pickup date {pickup.isoformat()}."})
    ids = [v.notice_id for v in inside]

    if norm is None:
        reasons.append({"code": "NOT_NORMALIZED", "text": "The product label could not be matched to a commodity."})
        return {"status": "UNCLEAR", "reasons": reasons, "zone_notice_ids": ids, "distance_mi": dist}

    low_conf = norm.confidence < CONFIDENCE_MIN
    form = norm.form.lower()
    form_ambiguous = form in ambiguous_forms
    # a non-fresh product whose form is named in an exemption (e.g. "canned, dried, or frozen below 0 F")
    # may or may not qualify: the conditions can't be read off a label, so a human must check
    form_exemptions = [ex for ex in exemptions if form in NON_FRESH and form in _tokens(ex["text"])]
    if norm.host_status == "not_host" and not low_conf:
        reasons.append({"code": "NOT_HOST", "text": f"'{norm.canonical_commodity}' is not on the Mexfly host lists in the sources."})
        return {"status": "NOT_HOST", "reasons": reasons, "zone_notice_ids": ids, "distance_mi": dist}
    if norm.host_status == "unclear" or low_conf or form_ambiguous or form_exemptions:
        if norm.host_status == "unclear":
            reasons.append({"code": "HOST_UNCLEAR", "text": f"Could not confirm whether '{norm.canonical_commodity}' is a regulated host."})
        if low_conf:
            reasons.append({"code": "LOW_CONFIDENCE", "text": f"Commodity match confidence is {norm.confidence:.2f} (below {CONFIDENCE_MIN})."})
        if form_ambiguous:
            reasons.append({"code": "FORM_AMBIGUOUS", "text": f"The sources do not settle whether '{norm.form}' product is regulated (ambiguity flagged during rule extraction)."})
        for ex in form_exemptions[:1]:
            reasons.append({"code": "FORM_EXEMPTION_CONDITIONAL", "rule_id": ex.get("rule_id"),
                            "text": f"An exemption covers some {norm.form} products (rule {ex.get('rule_id')}): \"{ex['text']}\". Whether this load qualifies can't be read from the label."})
        return {"status": "UNCLEAR", "reasons": reasons, "zone_notice_ids": ids, "distance_mi": dist}

    reasons.append({"code": "HOST", "text": f"'{norm.canonical_commodity}' ({norm.form}) is on the Mexfly host list in the sources."})
    toks = _tokens(shipment.get("product_raw", ""), norm.canonical_commodity)
    for ex in exemptions:
        if toks & _tokens(ex["text"]) - {"fruit", "fruits", "fresh", "regulated", "articles", "article"}:
            reasons.append({"code": "EXEMPTION_POSSIBLE", "rule_id": ex.get("rule_id"),
                            "text": f"A conditional exemption may apply (rule {ex.get('rule_id')}): \"{ex['text']}\". Confirm the conditions before relying on it."})
    return {"status": "REVIEW", "reasons": reasons, "zone_notice_ids": ids, "distance_mi": dist}


def match_all(shipments: list[dict], normalized: dict[str, Normalized], versions: list[ZoneVersion],
              ambiguous_forms: set[str], exemptions: list[dict], previous: dict[str, str] | None = None) -> dict[str, dict]:
    out = {}
    for s in shipments:
        r = match_one(s, normalized.get(s["id"]), versions, ambiguous_forms, exemptions)
        prev = (previous or {}).get(s["id"])
        r["previous_status"] = prev
        r["changed_since_previous_notice"] = prev is not None and prev != r["status"]
        out[s["id"]] = r
    return out
