"""Place name -> (lat, lon). Order: persistent cache -> Nominatim (1 req/s) -> fallback table.

The cache lives in data/geocode_cache.json (committed) so zones are reproducible offline.
"""
from __future__ import annotations

import asyncio
import json
import time

from ..config import DATA

CACHE_FILE = DATA / "geocode_cache.json"
FALLBACK_FILE = DATA / "fallback_geocodes.json"
USER_AGENT = "QuarantineShock/0.1 (hackathon demo; contact via project README)"
_last_call = 0.0


def _key(place: str) -> str:
    return " ".join(place.lower().replace("city of", "").split()).strip(" ,.")


def _load(path) -> dict:
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _nominatim(place: str) -> dict | None:
    global _last_call
    from geopy.geocoders import Nominatim

    wait = 1.05 - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()
    try:
        loc = Nominatim(user_agent=USER_AGENT, timeout=10).geocode(
            f"{place}, San Diego County, California, USA", country_codes="us")
    except Exception:  # noqa: BLE001  (network down, rate limited...)
        return None
    if not loc:
        return None
    return {"lat": round(loc.latitude, 5), "lon": round(loc.longitude, 5), "label": loc.address, "source": "nominatim"}


def geocode_sync(place: str, allow_network: bool = True) -> dict | None:
    k = _key(place)
    cache = _load(CACHE_FILE)
    if k in cache:
        return {**cache[k], "cached": True}
    hit = _nominatim(place) if allow_network else None
    if hit is None:
        fb = _load(FALLBACK_FILE).get(k)
        if fb:
            hit = {**fb, "source": "fallback_table"}
    if hit:
        cache[k] = hit
        CACHE_FILE.write_text(json.dumps(cache, indent=2), "utf-8")
        return {**hit, "cached": False}
    return None


async def geocode(place: str, allow_network: bool = True) -> dict | None:
    return await asyncio.to_thread(geocode_sync, place, allow_network)
