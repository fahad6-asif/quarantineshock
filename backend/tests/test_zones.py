import json
import math

from app.config import DATA
from app.geo import zones as Z
from app.geo.geocode import geocode_sync

R = 4.5


def towns():
    return {p: (g["lat"], g["lon"]) for p in ["La Mesa", "Spring Valley", "El Cajon"]
            if (g := geocode_sync(p, allow_network=False))}


def test_single_circle_is_miles():
    a = Z.area_sq_mi(Z.circle_utm(32.7678, -117.0231, R))
    expected = math.pi * R * R  # 63.62
    assert abs(a - expected) / expected < 0.02


def test_union_is_smaller_than_sum_when_overlapping():
    t = towns()
    sv, ec = Z.circle_utm(*t["Spring Valley"], R), Z.circle_utm(*t["El Cajon"], R)
    u = Z.build_zone_utm([t["Spring Valley"], t["El Cajon"]], R)
    assert Z.area_sq_mi(u) < Z.area_sq_mi(sv) + Z.area_sq_mi(ec)
    assert Z.area_sq_mi(u) > Z.area_sq_mi(sv)


def test_geojson_roundtrip_keeps_area():
    t = towns()
    g = Z.build_zone_utm([t["La Mesa"]], R)
    back = Z.from_geojson(Z.to_geojson(g))
    assert abs(Z.area_sq_mi(back) - Z.area_sq_mi(g)) < 0.5


def test_hero_sr1007_flips_between_jun16_and_jun18_zones():
    t = towns()
    jun16 = Z.build_zone_utm([t["Spring Valley"]], R)
    jun18 = Z.build_zone_utm([t["Spring Valley"], t["El Cajon"]], R)
    la_mesa = Z.build_zone_utm([t["La Mesa"]], R)
    ships = json.loads((DATA / "shipments.json").read_text("utf-8"))["shipments"]
    s = next(x for x in ships if x["id"] == "SR-1007")
    assert not Z.contains(jun16, s["lat"], s["lon"])
    assert not Z.contains(la_mesa, s["lat"], s["lon"])
    assert Z.contains(jun18, s["lat"], s["lon"])
    assert Z.distance_to_edge_mi(jun18, s["lat"], s["lon"]) > 0
