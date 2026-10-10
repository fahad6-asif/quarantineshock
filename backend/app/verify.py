"""Citation verifier: every quote must be a (near-)verbatim substring of its source.

Rule: normalize both sides (unicode, quotes, dashes, whitespace, case). Pass if the quote is an exact
substring, or if rapidfuzz partial_ratio >= 95 AND every word/number of the quote occurs in the
matched source window (so a changed number or word fails even when the fuzzy score is high).
Quotes with an ellipsis are checked piece by piece.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from rapidfuzz import fuzz

THRESHOLD = 95

_TRANS = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
                        "“": '"', "”": '"', "„": '"', "″": '"',
                        "–": "-", "—": "-", "−": "-", " ": " ", "×": "x"})


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").translate(_TRANS)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def _words(s: str) -> Counter:
    return Counter(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", s))


def _check_piece(q: str, src: str) -> tuple[bool, float]:
    if not q:
        return True, 100.0
    if q in src:
        return True, 100.0
    al = fuzz.partial_ratio_alignment(q, src)
    if al is None or al.score < THRESHOLD:
        return False, al.score if al else 0.0
    window = src[max(0, al.dest_start - 5): al.dest_end + 5]
    missing = _words(q) - _words(window)
    return (not missing), al.score


def verify_quote(quote: str | None, source_text: str) -> dict:
    """-> {verified: bool, score: float}"""
    if not quote or not quote.strip():
        return {"verified": False, "score": 0.0, "reason": "empty quote"}
    src = normalize(source_text)
    pieces = [p.strip(" .\"'") for p in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\])\s*", normalize(quote))]
    pieces = [p for p in pieces if len(p) >= 3]
    if not pieces:
        return {"verified": False, "score": 0.0, "reason": "quote too short"}
    results = [_check_piece(p, src) for p in pieces]
    ok = all(r[0] for r in results)
    return {"verified": ok, "score": round(min(r[1] for r in results), 1)}
