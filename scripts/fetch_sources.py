"""Download real source documents into sources/raw/ (HTML/PDF, untouched).

Usage: python scripts/fetch_sources.py [url ...]
With no args, fetches the default list below. Prints status + size per URL.
Text extraction happens in scripts/build_sources.py.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
INDEX = RAW / "index.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QuarantineShock-research/0.1 (hackathon; source collection)"

DEFAULT_URLS = [
    "https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-area-california",
    "https://www.aphis.usda.gov/news/program-update/aphis-expands-mexican-fruit-fly-anastrepha-ludens-quarantine-san-diego-county",
    "https://www.countynewscenter.com/mexican-fruit-fly-quarantine-expanded-in-san-diego-county/",
    "https://calfruitandveg.com/2026/06/24/mexfly-quarantine-in-portion-of-sd-county/",
    "https://www.10news.com/news/local-news/mexican-fruit-fly-quarantine-expanded-to-el-cajon-spring-valley",
    "https://www.freshfruitportal.com/news/2026/09/29/mexfly-quarantine-ca/",
    "https://www.cdfa.ca.gov/plant/mexfly/regulation.html",
    "https://www.cdfa.ca.gov/plant/mexfly/docs/regs/3417-TXT-mexfly.pdf",
    "https://www.aphis.usda.gov/news/program-update/aphis-establishes-host-lists-regulated-articles-three-tephritid-fruit-fly",
    "https://aphis.prod.usda.gov/sites/default/files/mexfly-host-list_1.pdf",
]


def slug_for(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "index"
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{tail[:70]}_{h}"


def main(urls: list[str]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX.read_text("utf-8")) if INDEX.exists() else {}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=45) as c:
        for url in urls:
            try:
                r = c.get(url)
            except Exception as e:  # noqa: BLE001
                print(f"FAIL  {url}  {type(e).__name__}: {e}")
                continue
            ctype = r.headers.get("content-type", "")
            ext = ".pdf" if ("pdf" in ctype or url.lower().endswith(".pdf")) else ".html"
            if ext == ".html" and "xml" in ctype:
                ext = ".xml"
            name = slug_for(url) + ext
            if r.status_code != 200:
                print(f"HTTP {r.status_code}  {url}")
                continue
            (RAW / name).write_bytes(r.content)
            index[name] = {"url": url, "final_url": str(r.url), "retrieved": date.today().isoformat(),
                           "content_type": ctype, "bytes": len(r.content)}
            print(f"OK    {len(r.content):>8}  {name}")
    INDEX.write_text(json.dumps(index, indent=2), "utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_URLS)
