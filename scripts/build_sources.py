"""Build sources/notices/*.txt, sources/regs/*.txt and sources/manifest.json from sources/raw/.

Every notice body is a VERBATIM excerpt of a real downloaded document: excerpts are selected
by exact start/end phrases and the script fails loudly if a phrase is not found.
No notice text is written by hand.

Usage: python scripts/build_sources.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_text import extract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
INDEX = json.loads((RAW / "index.json").read_text("utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def raw_file(prefix: str) -> Path:
    hits = sorted(RAW.glob(prefix + "*"))
    if not hits:
        raise SystemExit(f"missing raw file {prefix}* - run scripts/fetch_sources.py first")
    return hits[0]


def doc_text(prefix: str) -> tuple[str, dict]:
    p = raw_file(prefix)
    return norm(extract(p)), INDEX[p.name]


def span(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"start phrase not found: {start[:60]!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"end phrase not found: {end[:60]!r}")
    return text[i : j + len(end)]


# ---------------------------------------------------------------- documents
DOCS = {
    "nappo_1191": ("1191_", "NAPPO Official Pest Report 1191: APHIS Establishes a Quarantine Area in California (Mexfly)", "USDA APHIS via NAPPO", "2026-03-19"),
    "aphis_da_2026_16": ("aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-area-cali", "APHIS DA-2026-16: APHIS Expands the Mexican Fruit Fly Quarantine Area in California", "USDA APHIS", "2026-04-17"),
    "aphis_da_2026_36": ("aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-san-diego", "APHIS DA-2026-36: APHIS Expands Mexican Fruit Fly Quarantine in San Diego County, California", "USDA APHIS", "2026-09-23"),
    "county_news_jun": ("mexican-fruit-fly-quarantine-expanded-in-san-diego-county", "County News Center: Mexican Fruit Fly Quarantine Expanded in San Diego County", "County of San Diego", "2026-06-23"),
    "cdfa_pep_sv_amd2": ("MXFF_PEP_SpringValley", "CDFA Official Notice: Amendment to the Proclamation of Emergency Program for the Mexican Fruit Fly (Spring Valley / El Cajon)", "CDFA", "2026-06-24"),
}

NOTICES = [
    {
        "id": "2026-03-05_la-mesa-established",
        "title": "La Mesa quarantine established",
        "effective_date": "2026-03-05",
        "quarantine": "La Mesa",
        "stated_area_sq_mi": 77,
        "parts": [("nappo_1191",
                   "On March 5, 2026, the Animal and Plant Health Inspection Service",
                   "designated the La Mesa quarantine."),
                  ("nappo_1191",
                   "APHIS and CDFA established the La Mesa quarantine in response to the February 24 detection",
                   "approximately 77 square miles and contained no commercial agriculture.")],
    },
    {
        "id": "2026-03-10_la-mesa-expanded",
        "title": "La Mesa quarantine expanded",
        "effective_date": "2026-03-10",
        "quarantine": "La Mesa",
        "stated_area_sq_mi": 82,
        "parts": [("nappo_1191",
                   "On March 10, APHIS and CDFA expanded the La Mesa quarantine in response to",
                   "approximately 82 square miles and contains no commercial agriculture.")],
    },
    {
        "id": "2026-04-02_la-mesa-expanded-da-2026-16",
        "title": "La Mesa expanded twice (DA-2026-16)",
        "effective_date": "2026-04-02",
        "quarantine": "La Mesa",
        "stated_area_sq_mi": 84,
        "parts": [("aphis_da_2026_16",
                   "FOR INFORMATION AND ACTION DA-2026-16",
                   "APHIS will publish a notice of this change in the Federal Register.")],
    },
    {
        "id": "2026-06-16_spring-valley-established",
        "title": "Spring Valley quarantine established",
        "effective_date": "2026-06-16",
        "quarantine": "Spring Valley",
        "stated_area_sq_mi": 76,
        "parts": [("aphis_da_2026_36",
                   "On June 16, 2026, CDFA established a Mexfly quarantine",
                   "contained 22.5 acres of commercial agriculture.")],
    },
    {
        "id": "2026-06-18_spring-valley-expanded-el-cajon",
        "title": "Spring Valley expanded to El Cajon",
        "effective_date": "2026-06-18",
        "quarantine": "Spring Valley",
        "stated_area_sq_mi": 111,
        "parts": [("aphis_da_2026_36",
                   "On June 18, CDFA expanded the Spring Valley quarantine",
                   "avocado, citrus, stone fruit, and tomatoes."),
                  ("cdfa_pep_sv_amd2",
                   "The emergency program area is the entirety of the Mexfly quarantine area within San Diego County, which became effective on June 18, 2026.",
                   "within a 4.5-mile radius of all Mexfly detections."),
                  ("county_news_jun",
                   "The quarantine restricts movement of host fruits and plants",
                   "to prevent spreading the pest.")],
    },
    {
        "id": "2026-08-14_la-mesa-spring-valley-merged",
        "title": "La Mesa + Spring Valley merged (DA-2026-36)",
        "effective_date": "2026-08-14",
        "quarantine": "La Mesa",
        "merges": ["La Mesa", "Spring Valley"],
        "stated_area_sq_mi": 173,
        "parts": [("aphis_da_2026_36",
                   "FOR INFORMATION AND ACTION DA-2026-36",
                   "APHIS will also publish a notice about this change in the Federal Register.")],
    },
]


# ---------------------------------------------------------------- regulations
def ecfr_sections() -> str:
    from bs4 import BeautifulSoup

    out = []
    for s in ["301.32", "301.32-1", "301.32-2", "301.32-3", "301.32-4", "301.32-5", "301.32-6", "301.32-10"]:
        p = raw_file(f"title-7.xml_part_301_section_{s}_")
        soup = BeautifulSoup(p.read_bytes(), "html.parser")
        head = soup.find("head")
        out.append(norm(head.get_text(" ")) if head else f"§ {s}")
        out.append(extract(p))
    return "\n\n".join(out)


def hosts_text() -> str:
    full = extract(raw_file("da-2026-20"))
    cover = full[: full.find("Mediterranean fruit fly, Ceratitis capitata (Wiedemann), Regulated Host List, 2026 \nEffective")]
    i = full.find("Mexican fruit fly, Anastrepha ludens (Loew), Regulated Host List, 2026 \nEffective")
    m = re.compile(r"\n\s*References\s*\n").search(full, i)  # the bibliography heading, not the column header
    j = m.start() if m else -1
    if i < 0 or j < 0:
        raise SystemExit("could not locate Mexfly host list in DA-2026-20")
    return cover.strip() + "\n\n" + full[i:j].strip()


def pep_text() -> str:
    t = extract(raw_file("MXFF_PEP_SpringValley"))
    # drop the scanned map pages (OCR noise) between the signature block and the work plan
    a = t.find("Mexican Fruit Fly Eradication Project \nBostonia")
    b = t.find("ERADICATION PROJECT WORK PLAN")
    if a > 0 and b > a:
        t = t[:a] + t[b:]
    return t


def regs() -> list[dict]:
    def meta(prefix):
        return INDEX[raw_file(prefix).name]

    return [
        {"id": "7cfr301_32", "file": "regs/7cfr301_32.txt", "title": "7 CFR 301.32 through 301.32-10 (Fruit Flies), eCFR as of 2026-10-08",
         "publisher": "eCFR / National Archives", "date": "2026-10-08", "type": "regulation", "text": ecfr_sections(),
         "url": "https://www.ecfr.gov/current/title-7/subtitle-B/chapter-III/part-301/subpart-L", "retrieved": meta("title-7.xml_part_301_section_301.32-2_")["retrieved"]},
        {"id": "cdfa_3417", "file": "regs/cdfa_3417_mexfly_interior_quarantine.txt", "title": "CCR Section 3417 Mexican Fruit Fly Interior Quarantine (updated 1-14-25)",
         "publisher": "CDFA", "date": "2025-01-14", "type": "regulation", "text": extract(raw_file("3417-TXT")), **_um(meta("3417-TXT"))},
        {"id": "cdfa_processing", "file": "regs/cdfa_options_processing.txt", "title": "CDFA: Options for Host Fruit and Vegetables - Processing",
         "publisher": "CDFA", "date": None, "type": "regulation", "text": extract(raw_file("current_options")), **_um(meta("current_options"))},
        {"id": "cdfa_mexfly_page", "file": "regs/cdfa_mexfly.txt", "title": "CDFA MEXFLY Regulation and Quarantine Boundaries page",
         "publisher": "CDFA", "date": None, "type": "regulation", "text": extract(raw_file("regulation.html")), **_um(meta("regulation.html"))},
        {"id": "cdfa_quarantine_text_lamesa", "file": "regs/cdfa_quarantine_text_la_mesa_2026-08-14.txt", "title": "CDFA Section 3417(b) La Mesa area quarantine boundary text, effective 8/14/2026",
         "publisher": "CDFA", "date": "2026-08-14", "type": "regulation", "text": extract(raw_file("MexFly_Quarantine_SanDiego_County_Text")), **_um(meta("MexFly_Quarantine_SanDiego_County_Text"))},
        {"id": "cdfa_pep_sv_amd2", "file": "regs/cdfa_official_notice_spring_valley_2026-06-24.txt", "title": DOCS["cdfa_pep_sv_amd2"][1],
         "publisher": "CDFA", "date": "2026-06-24", "type": "regulation", "text": pep_text(), **_um(meta("MXFF_PEP_SpringValley"))},
        {"id": "mexfly_hosts", "file": "regs/mexfly_hosts.txt", "title": "APHIS Federal Order DA-2026-20 + Mexican fruit fly Regulated Host List, 2026",
         "publisher": "USDA APHIS", "date": "2026-07-29", "type": "host_list", "text": hosts_text(), **_um(meta("da-2026-20"))},
        {"id": "county_news_jun", "file": "regs/county_news_2026-06_expanded.txt", "title": DOCS["county_news_jun"][1],
         "publisher": "County of San Diego", "date": "2026-06-23", "type": "press_release", "text": extract(raw_file("mexican-fruit-fly-quarantine-expanded-in-san-diego-county")),
         **_um(meta("mexican-fruit-fly-quarantine-expanded-in-san-diego-county"))},
    ]


def _um(m: dict) -> dict:
    return {"url": m["url"], "retrieved": m["retrieved"]}


def write_doc(rel: str, header: dict, body: str) -> None:
    p = ROOT / "sources" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    head = "\n".join(f"# {k}: {v}" for k, v in header.items() if v is not None)
    p.write_text(f"{head}\n# ---\n{body.strip()}\n", "utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = []
    for n in NOTICES:
        bodies, sources = [], []
        for doc_id, start, end in n["parts"]:
            text, meta = doc_text(DOCS[doc_id][0])
            bodies.append(span(text, start, end))
            sources.append({"doc": doc_id, "title": DOCS[doc_id][1], "publisher": DOCS[doc_id][2],
                            "published": DOCS[doc_id][3], "url": meta["url"], "retrieved": meta["retrieved"]})
        rel = f"notices/{n['id']}.txt"
        primary = sources[0]
        write_doc(rel, {"title": n["title"], "effective_date": n["effective_date"],
                        "source": "; ".join(f"{s['title']} <{s['url']}> (retrieved {s['retrieved']})" for s in sources),
                        "note": "verbatim excerpt(s); see manifest.json"}, "\n\n".join(bodies))
        manifest.append({"id": n["id"], "file": rel, "type": "notice", "title": n["title"],
                         "effective_date": n["effective_date"], "quarantine": n["quarantine"], "merges": n.get("merges"),
                         "stated_area_sq_mi": n["stated_area_sq_mi"], "publisher": primary["publisher"],
                         "date": primary["published"], "url": primary["url"], "source_quality": "primary",
                         "excerpt_of": sources})
        print(f"notice  {rel}  ({sum(len(b) for b in bodies)} chars)")
    for r in regs():
        text = r.pop("text")
        write_doc(r["file"], {"title": r["title"], "url": r["url"], "retrieved": r["retrieved"]}, text)
        manifest.append({**r, "source_quality": "primary"})
        print(f"{r['type']:<9} {r['file']}  ({len(text)} chars)")
    (ROOT / "sources" / "manifest.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    print(f"manifest: {len(manifest)} documents")


if __name__ == "__main__":
    main()
