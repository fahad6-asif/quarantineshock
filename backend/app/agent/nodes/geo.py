"""Nodes 3-4: geocode detections, build the zone (union of official-radius circles)."""
from __future__ import annotations

from ... import prompts
from ...config import settings
from ...geo import zones as Z
from ...geo.geocode import geocode
from ...llm import generate_json
from ...rag import retrieve
from ...schemas import RadiusFinding
from ...verify import verify_quote
from ..context import RunContext


def _quarantines_for(notice: dict) -> set[str]:
    return set(notice.get("merges") or []) | {notice["quarantine"]}


def _det_key(d: dict) -> tuple:
    return (d["place"].strip().lower(), d.get("date") or d.get("detail", "").lower())


async def geocode_detections(state: dict, ctx: RunContext) -> dict:
    wanted = _quarantines_for(ctx.notice)
    prior: list[dict] = []
    for r in ctx.prev_results:
        for d in r.get("detections", []):
            if d.get("new_in_notice") == r["notice_id"]:
                prior.append(d)
    merged: dict[tuple, dict] = {}
    for d in prior:
        merged.setdefault(_det_key(d), {**d})
    new_count = 0
    for d in state["extract"]["detections"]:
        k = (d["place"].strip().lower(), d.get("date") or d.get("detail", "").lower())
        if k in merged:
            continue
        merged[k] = {**d, "quarantine": ctx.notice["quarantine"], "new_in_notice": ctx.notice_id}
        new_count += 1
    out = []
    for d in merged.values():
        if "lat" not in d:
            g = await geocode(d["place"])
            if g is None:
                ctx.warnings.append(f"Could not geocode '{d['place']}'")
                await ctx.progress("geocode_detections", f"Could not locate '{d['place']}', skipped")
                continue
            d.update({"lat": g["lat"], "lon": g["lon"], "geocode_source": g.get("source", "cache"),
                      "approximate": True, "geocode_label": g.get("label")})
        d["in_current_zone"] = d.get("quarantine") in wanted
        out.append(d)
    used = [d for d in out if d["in_current_zone"]]
    places = sorted({d["place"] for d in used})
    return {"detections": out,
            "_message": f"Located {len(used)} detection site(s) for this zone ({', '.join(places)}); {new_count} new · town centroids, approximate",
            "_output": [{k: d.get(k) for k in ("place", "date", "lat", "lon", "geocode_source", "new_in_notice")} for d in out]}


async def _radius(ctx: RunContext) -> dict:
    hits = retrieve.multi_search(["quarantine area radius miles around detections",
                                  "4.5 mile radius quarantine Mexican fruit fly",
                                  "initial area under quarantine minimum radius"], k=3, types=["regulation"], limit=6)
    passages = "\n\n".join(f"[{h['chunk_id']}] {h['text']}" for h in hits)
    try:
        f, _ = await generate_json("find_radius", prompts.render("find_radius", passages=passages), RadiusFinding,
                                   "fast", scope="radius")
    except Exception as e:  # noqa: BLE001
        ctx.warnings.append(f"radius lookup failed: {e}")
        f = RadiusFinding(found=False)
    if f.found and f.radius_miles and f.quote and f.source_chunk_id:
        chunk = retrieve.get_chunk(f.source_chunk_id)
        v = verify_quote(f.quote, chunk["text"] if chunk else "")
        if v["verified"] and abs(f.radius_miles - 4.5) < 5:
            return {"miles": f.radius_miles, "source": "sources", "quote": f.quote, "chunk_id": f.source_chunk_id,
                    "verified": True}
    return {"miles": settings.radius_miles_config, "source": "config", "quote": None, "chunk_id": None, "verified": False}


async def build_zone(state: dict, ctx: RunContext) -> dict:
    radius = await _radius(ctx)
    await ctx.progress("build_zone", f"Radius {radius['miles']:g} mi " + (
        "(quoted from the sources)" if radius["source"] == "sources" else "(from config: verify)"))
    pts = [(d["lat"], d["lon"]) for d in state["detections"] if d["in_current_zone"]]
    geom = Z.build_zone_utm(pts, radius["miles"])
    area = Z.area_sq_mi(geom)
    official = state["extract"].get("stated_area_sq_mi") or ctx.notice.get("stated_area_sq_mi")
    err = (area - official) / official * 100 if official else None
    version = {"notice_id": ctx.notice_id, "quarantine": ctx.notice["quarantine"],
               "effective_date": ctx.notice["effective_date"], "supersedes": ctx.notice.get("merges") or [],
               "geojson": Z.to_geojson(geom), "area_sq_mi": round(area, 1)}
    prev_versions = (ctx.previous or {}).get("zone_versions", [])
    zone = {"quarantine": ctx.notice["quarantine"], "effective_date": ctx.notice["effective_date"],
            "geojson": version["geojson"], "area_sq_mi": round(area, 1), "official_sq_mi": official,
            "error_pct": round(err, 1) if err is not None else None, "n_detections": len(pts)}
    msg = f"Zone {area:.0f} sq mi generated"
    if official:
        msg += f" vs {official:g} sq mi official ({err:+.0f}%)"
    if err is not None and abs(err) > 25:
        ctx.warnings.append(f"Generated area differs from official by {err:+.0f}% (detections are town centroids)")
    return {"radius": radius, "zone": zone, "zone_versions": [*prev_versions, version], "_message": msg,
            "_output": {k: v for k, v in zone.items() if k != "geojson"} | {"radius": radius}}
