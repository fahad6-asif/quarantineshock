"""Turn a raw HTML/PDF file into clean text (shared by build_sources.py).

Usage: python scripts/extract_text.py <raw-file>   -> prints extracted text
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def html_to_text(raw: bytes) -> str:
    import warnings

    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]):
        tag.decompose()
    root = (soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"})
            or soup.find(id=re.compile("content", re.I)) or soup.body or soup)
    blocks = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "blockquote"]):
        if el.find(["p", "li", "td"]):  # skip containers, keep leaves
            continue
        t = " ".join(el.get_text(" ", strip=True).split())
        if t:
            blocks.append(t)
    out, seen = [], set()
    for b in blocks:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return "\n\n".join(out)


def pdf_to_text(path: Path) -> str:
    from pypdf import PdfReader

    pages = [p.extract_text() or "" for p in PdfReader(str(path)).pages]
    text = "\n\n".join(pages)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return pdf_to_text(path)
    return html_to_text(path.read_bytes())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(extract(Path(sys.argv[1])))
