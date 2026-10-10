"""Generate the FICTIONAL Sunridge Produce pickup schedule (data/shipments.json) and draft answer key
(data/labels.csv). Origins are fictional; each coordinate is checked against the zones built from the
real detection towns so the demo geometry holds (e.g. SR-1007 is outside the Jun 16 zone and inside
the Jun 18 zone).

Usage: python scripts/make_shipments.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.geo import zones as Z  # noqa: E402
from app.geo.geocode import geocode_sync  # noqa: E402

R = 4.5
DATA = ROOT / "data"

# region codes: LM = inside La Mesa zone; SV16 = inside Jun-16 Spring Valley zone but outside La Mesa;
# NEW18 = inside Jun-18 zone but outside Jun-16 zone and La Mesa; OUT = outside every zone; NONE = no coords
SHIPMENTS = [
    # id, pickup, origin (fictional), anchor lat, lon, region, product_raw, qty, destination, carrier, notes
    ("SR-1001", "2026-06-15", "Mt. Helix hillside grove (fictional)", 32.7665, -116.9890, "LM", "meyer lemons 38lb", "60 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", ""),
    ("SR-1002", "2026-06-16", "Fallbrook ridge ranch (fictional)", 33.3764, -117.2511, "OUT", "hass avocados 48ct", "200 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", ""),
    ("SR-1003", "2026-06-22", "Bostonia family orchard (fictional)", 32.8075, -116.9360, "NEW18", "navels bin", "4 bins", "Ontario distribution center", "Mesa Haul Co. (fictional)", ""),
    ("SR-1004", "2026-06-17", "Lemon Grove packing shed (fictional)", 32.7420, -117.0310, "LM", "yellow onions 50lb", "80 sacks", "San Diego restaurant supply", "Mesa Haul Co. (fictional)", ""),
    ("SR-1005", "2026-06-15", "Rancho San Diego small farm (fictional)", 32.7400, -116.9400, "SV16", "fuyu persimmons 25lb", "40 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", "pickup is one day before the Spring Valley quarantine"),
    ("SR-1006", "2026-07-02", "Mt. Helix terrace citrus (fictional)", 32.7700, -116.9950, "LM", "cara cara 4/5 bu", "120 cartons", "Phoenix grocery DC", "Desert Line Freight (fictional)", ""),
    ("SR-1007", "2026-06-19", "Granite Hills avocado grove (fictional)", 32.8031, -116.9047, "NEW18", "Hass avos 40lb x 120", "120 x 40 lb", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", "hero case: the avocado truck"),
    ("SR-1008", "2026-07-15", "Valley Center citrus block (fictional)", 33.2184, -117.0342, "OUT", "valencias 7/10 bu", "300 cartons", "Fresno packing partner", "Central Valley Express (fictional)", ""),
    ("SR-1009", "2026-06-24", "Sweetwater bottomland farm (fictional)", 32.7050, -116.9450, "SV16", "heirloom toms 25lb", "90 flats", "San Diego restaurant supply", "Mesa Haul Co. (fictional)", ""),
    ("SR-1010", "2026-06-26", "Rancho San Diego grove (fictional)", 32.7470, -116.9350, "SV16", "avacodo hass", "150 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", "label typed by hand at the gate"),
    ("SR-1011", "2026-06-20", "East El Cajon greens farm (fictional)", 32.7900, -116.9200, "NEW18", "romaine hearts 24ct", "300 cases", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", "supporting case: not everything is flagged"),
    ("SR-1012", "2026-07-08", "Winter Gardens stone fruit (fictional)", 32.8310, -116.9330, "NEW18", "yellow peaches 2L", "140 flats", "Ontario distribution center", "Mesa Haul Co. (fictional)", ""),
    ("SR-1013", "2026-07-10", "Rancho San Diego herb plot (fictional)", 32.7350, -116.9200, "SV16", "cilantro 30ct", "70 cases", "San Diego restaurant supply", "Mesa Haul Co. (fictional)", ""),
    ("SR-1014", "2026-06-29", "Casa de Oro farm stand (fictional)", 32.7600, -116.9700, "LM", "mixed fruit box - assorted", "50 boxes", "Escondido retail co-op", "Mesa Haul Co. (fictional)", ""),
    ("SR-1015", "2026-06-23", "El Cajon cold storage (fictional)", 32.8260, -116.9700, "NEW18", "avocado pulp, frozen, 30lb pails", "60 pails", "Los Angeles food processor", "Coastline Reefer (fictional)", "hero case: the tricky one"),
    ("SR-1016", "2026-07-21", "Jamacha juice grove (fictional)", 32.7150, -116.9300, "SV16", "juice oranges for processing", "6 bins", "Riverside juice plant", "Central Valley Express (fictional)", ""),
    ("SR-1017", "2026-08-03", "La Mesa dry goods co-packer (fictional)", 32.7700, -117.0200, "LM", "dried mango slices", "40 cases", "Los Angeles specialty foods", "Coastline Reefer (fictional)", ""),
    ("SR-1018", "2026-07-28", "Lemon Grove stone fruit (fictional)", None, None, "NONE", "plums 28lb", "75 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", "origin coordinates missing in the TMS export"),
    ("SR-1019", "2026-08-05", "Pauma Valley grapefruit (fictional)", 33.3031, -116.9781, "OUT", "grapefruit ruby 40lb", "180 cartons", "Phoenix grocery DC", "Desert Line Freight (fictional)", ""),
    ("SR-1020", "2026-08-12", "Lemon Grove berry patch (fictional)", 32.7450, -117.0250, "LM", "strawberries 8x1lb", "100 flats", "San Diego retail co-op", "Mesa Haul Co. (fictional)", ""),
    ("SR-1021", "2026-08-17", "Ramona orchard (fictional)", 33.0417, -116.8681, "OUT", "pomegranates 22lb", "90 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", ""),
    ("SR-1022", "2026-08-18", "Mt. Helix tangelo block (fictional)", 32.7630, -116.9980, "LM", "tangelos minneola", "110 cartons", "Ontario distribution center", "Mesa Haul Co. (fictional)", ""),
    ("SR-1023", "2026-08-19", "Rancho San Diego stone fruit (fictional)", 32.7550, -116.9250, "SV16", "white nectarines 2L", "130 flats", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", ""),
    ("SR-1024", "2026-08-20", "Lakeside citrus (fictional)", 32.8570, -116.9220, "OUT", "mandarins 5lb bags", "200 bags", "Escondido retail co-op", "Mesa Haul Co. (fictional)", "close to, but outside, the zone edge"),
    ("SR-1025", "2026-08-20", "Jamul avocado hill (fictional)", 32.7170, -116.8760, "OUT", "hass avocados 60ct", "160 cartons", "Los Angeles Wholesale Produce Market", "Coastline Reefer (fictional)", ""),
]

# drafted answer key: id -> (canonical, host_status). host_status for non-fresh forms is 'unclear' by design.
LABELS = {
    "SR-1001": "meyer lemon", "SR-1002": "avocado", "SR-1003": "orange", "SR-1004": "onion", "SR-1005": "persimmon",
    "SR-1006": "orange", "SR-1007": "avocado", "SR-1008": "orange", "SR-1009": "tomato", "SR-1010": "avocado",
    "SR-1011": "romaine lettuce", "SR-1012": "peach", "SR-1013": "cilantro", "SR-1014": "mixed fruit",
    "SR-1015": "avocado", "SR-1016": "orange", "SR-1017": "mango", "SR-1018": "plum", "SR-1019": "grapefruit",
    "SR-1020": "strawberry", "SR-1021": "pomegranate", "SR-1022": "tangelo", "SR-1023": "nectarine",
    "SR-1024": "mandarin", "SR-1025": "avocado",
}
NON_FRESH = {"SR-1014", "SR-1015", "SR-1016", "SR-1017"}


def main() -> None:
    pt = {p: (g["lat"], g["lon"]) for p in ["La Mesa", "Spring Valley", "El Cajon"] if (g := geocode_sync(p))}
    lm = Z.build_zone_utm([pt["La Mesa"]], R)
    sv16 = Z.build_zone_utm([pt["Spring Valley"]], R)
    sv18 = Z.build_zone_utm([pt["Spring Valley"], pt["El Cajon"]], R)

    def region(lat, lon):
        if Z.contains(lm, lat, lon):
            return "LM"
        if Z.contains(sv16, lat, lon):
            return "SV16"
        if Z.contains(sv18, lat, lon):
            return "NEW18"
        return "OUT"

    out = []
    for sid, pickup, origin, lat, lon, want, raw, qty, dest, carrier, notes in SHIPMENTS:
        if want != "NONE":
            got = region(lat, lon)
            if got != want:
                raise SystemExit(f"{sid}: anchor ({lat},{lon}) is in {got}, expected {want}; adjust the anchor")
        out.append({"id": sid, "pickup_date": pickup, "origin_name": origin, "lat": lat, "lon": lon,
                    "product_raw": raw, "quantity": qty, "destination": dest, "carrier": carrier, "notes": notes,
                    "fictional": True})
    (DATA / "shipments.json").write_text(json.dumps({"_note": "FICTIONAL demo data for 'Sunridge Produce' (a fictional distributor). Origins, carriers and loads are invented. Coordinates were chosen relative to zones generated from the real 2026 detection towns.", "shipments": out}, indent=2), "utf-8")

    table = json.loads((DATA / "host_table.json").read_text("utf-8"))
    with open(DATA / "labels.csv", "w", newline="", encoding="utf-8") as f:
        f.write("# reviewed_by_human: false\n")
        f.write("# Drafted by Claude Code from data/host_table.json (APHIS DA-2026-20 federal list + CCR 3417 state list).\n")
        f.write("# Fahad: check every row, fix anything wrong, then change 'false' to 'true' on the first line.\n")
        f.write("# host_status is 'unclear' for frozen/processed/dried/mixed products by design.\n")
        w = csv.writer(f)
        w.writerow(["id", "canonical_commodity", "host_status"])
        for s in out:
            c = LABELS[s["id"]]
            hs = "unclear" if s["id"] in NON_FRESH or c not in table else ("host" if table[c]["host"] else "not_host")
            w.writerow([s["id"], c, hs])
    print(f"wrote {len(out)} fictional shipments and a draft labels.csv")
    s7 = next(s for s in out if s["id"] == "SR-1007")
    print(f"SR-1007 at ({s7['lat']}, {s7['lon']}): in Jun16 zone={Z.contains(sv16, s7['lat'], s7['lon'])}, "
          f"in Jun18 zone={Z.contains(sv18, s7['lat'], s7['lon'])}, in La Mesa={Z.contains(lm, s7['lat'], s7['lon'])}")


if __name__ == "__main__":
    main()
