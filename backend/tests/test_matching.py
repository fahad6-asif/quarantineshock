from datetime import date

from app.geo import zones as Z
from app.matching import Normalized, ZoneVersion, active_zones, match_all, match_one

# synthetic zones: two quarantines near El Cajon
LM = (32.7678, -117.0231)
SV = (32.7296, -116.9669)
EC = (32.7948, -116.9625)
R = 4.5


def versions():
    return [
        ZoneVersion("n1", "La Mesa", date(2026, 3, 5), Z.build_zone_utm([LM], R)),
        ZoneVersion("n4", "Spring Valley", date(2026, 6, 16), Z.build_zone_utm([SV], R)),
        ZoneVersion("n5", "Spring Valley", date(2026, 6, 18), Z.build_zone_utm([SV, EC], R)),
        ZoneVersion("n6", "La Mesa", date(2026, 8, 14), Z.build_zone_utm([LM, SV, EC], R), ["La Mesa", "Spring Valley"]),
    ]


HERO = {"id": "SR-1007", "pickup_date": "2026-06-19", "lat": 32.8031, "lon": -116.9047, "product_raw": "Hass avos 40lb x 120"}
AVO = Normalized("avocado", "fresh", "host", 0.95)
HASS_EXEMPTION = [{"rule_id": "R3", "text": "Fresh, mature green variety 'Hass' avocadoes are not regulated"}]


def test_active_zones_date_logic_and_merge():
    v = versions()
    assert {z.notice_id for z in active_zones(v, date(2026, 6, 15))} == {"n1"}
    assert {z.notice_id for z in active_zones(v, date(2026, 6, 17))} == {"n1", "n4"}
    assert {z.notice_id for z in active_zones(v, date(2026, 6, 19))} == {"n1", "n5"}
    assert {z.notice_id for z in active_zones(v, date(2026, 8, 20))} == {"n6"}  # Spring Valley merged away


def test_hero_avocado_truck_flips_outside_to_review():
    only_jun16 = [z for z in versions() if z.notice_id in ("n1", "n4")]
    before = match_one(HERO, AVO, only_jun16, set(), HASS_EXEMPTION)
    assert before["status"] == "OUTSIDE"
    after = match_one(HERO, AVO, versions(), set(), HASS_EXEMPTION)
    assert after["status"] == "REVIEW"
    codes = [r["code"] for r in after["reasons"]]
    assert "INSIDE_ZONE" in codes and "HOST" in codes and "EXEMPTION_POSSIBLE" in codes


def test_changed_flag():
    res = match_all([HERO], {"SR-1007": AVO}, versions(), set(), [], previous={"SR-1007": "OUTSIDE"})
    assert res["SR-1007"]["changed_since_previous_notice"] is True


def test_romaine_inside_is_not_host():
    s = {**HERO, "id": "SR-1011", "product_raw": "romaine hearts 24ct"}
    r = match_one(s, Normalized("romaine lettuce", "fresh", "not_host", 0.93), versions(), set(), [])
    assert r["status"] == "NOT_HOST"


def test_frozen_pulp_is_unclear_when_form_is_ambiguous():
    s = {**HERO, "id": "SR-1015", "product_raw": "avocado pulp, frozen, 30lb pails"}
    r = match_one(s, Normalized("avocado", "frozen", "host", 0.9), versions(), {"frozen", "processed"}, [])
    assert r["status"] == "UNCLEAR"
    assert any(x["code"] == "FORM_AMBIGUOUS" for x in r["reasons"])


def test_dried_product_named_in_exemption_is_unclear():
    s = {**HERO, "id": "SR-1017", "product_raw": "dried mango slices"}
    ex = [{"rule_id": "R1", "text": "canned, dried, or frozen below −17.8 °C (0 °F)"}]
    r = match_one(s, Normalized("mango", "dried", "host", 0.95), versions(), set(), ex)
    assert r["status"] == "UNCLEAR"
    assert any(x["code"] == "FORM_EXEMPTION_CONDITIONAL" for x in r["reasons"])
    # the same exemption must not touch fresh fruit
    r2 = match_one(HERO, AVO, versions(), set(), ex)
    assert r2["status"] == "REVIEW"


def test_low_confidence_is_unclear():
    r = match_one(HERO, Normalized("avocado", "fresh", "host", 0.5), versions(), set(), [])
    assert r["status"] == "UNCLEAR"


def test_unclear_host_status_is_unclear():
    r = match_one(HERO, Normalized("mixed fruit", "mixed", "unclear", 0.9), versions(), set(), [])
    assert r["status"] == "UNCLEAR"


def test_missing_coordinates_is_unclear():
    s = {**HERO, "lat": None, "lon": None}
    assert match_one(s, AVO, versions(), set(), [])["status"] == "UNCLEAR"
    s2 = {**HERO, "lat": 0, "lon": 0}
    assert match_one(s2, AVO, versions(), set(), [])["status"] == "UNCLEAR"


def test_outside_all_zones():
    s = {**HERO, "lat": 33.3764, "lon": -117.2511}  # Fallbrook
    assert match_one(s, AVO, versions(), set(), [])["status"] == "OUTSIDE"


def test_pickup_before_effective_date_uses_previous_zone():
    # inside the Jun 16 Spring Valley zone, but picked up Jun 15: only La Mesa is active then
    s = {**HERO, "pickup_date": "2026-06-15", "lat": 32.74, "lon": -116.94}
    assert match_one(s, AVO, versions(), set(), [])["status"] == "OUTSIDE"
    s2 = {**s, "pickup_date": "2026-06-16"}
    assert match_one(s2, AVO, versions(), set(), [])["status"] == "REVIEW"


def test_no_active_zone_at_all():
    s = {**HERO, "pickup_date": "2026-01-01"}
    r = match_one(s, AVO, versions(), set(), [])
    assert r["status"] == "OUTSIDE" and r["reasons"][0]["code"] == "NO_ACTIVE_ZONE"
