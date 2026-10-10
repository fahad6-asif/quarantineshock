"""Ask the Rules: RAG-only streaming answers with chunk citations and verified quotes."""
from __future__ import annotations

import json
import re
from typing import AsyncIterator

from . import prompts
from .llm import LLMUnavailable, stream_text
from .rag import retrieve, sources
from .verify import verify_quote

MARKER = "QUOTES:"
CERTAINTY = re.compile(r"\b(cleared|approved for shipment|is safe|safe to ship|definitely allowed|guaranteed)\b", re.I)
SCRIPTED = [
    "Can I ship frozen avocado pulp from El Cajon?",
    "Is romaine lettuce regulated under this quarantine?",
    "What changed in the June 18 notice?",
    "What does a grower need to move host fruit out of the zone?",
    "Which crops are affected by the expansion?",
]


STOP = {"about", "after", "could", "every", "which", "where", "there", "their", "these", "those", "would", "under",
        "within", "what", "does", "need", "from", "with", "this", "that", "have", "into", "regulated", "quarantine",
        "notice", "changed", "affected", "grower", "should", "allowed", "zone", "ship", "move"}


def _retrieve(question: str) -> list[dict]:
    """Hybrid retrieval: semantic hits for the question (+ a host-list/regulation angle) and exact keyword hits."""
    hits = retrieve.multi_search([question, f"{question} regulated articles host list exemptions"], k=5, limit=7)
    seen = {h["chunk_id"] for h in hits}
    words = [w for w in re.findall(r"[a-z]{5,}", question.lower()) if w not in STOP]
    if words:
        for h in retrieve.keyword_search(words, types=["regulation", "host_list", "notice"], limit=3):
            if h["chunk_id"] not in seen:
                hits.append(h)
                seen.add(h["chunk_id"])
    hits.sort(key=lambda h: h["chunk_id"])
    return hits


def _prompt(question: str, hits: list[dict]) -> str:
    passages = "\n\n".join(f"[{h['chunk_id']}] ({h['title']})\n{h['text']}" for h in hits)
    return prompts.render("chat", passages=passages, question=question.strip())


def _parse_quotes(tail: str) -> list[dict]:
    t = tail.strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j < i:
        return []
    try:
        data = json.loads(t[i:j + 1])
        return [q for q in data if isinstance(q, dict) and q.get("quote")]
    except json.JSONDecodeError:
        return []


def _best_sentence(answer: str, chunk_id: str, chunk_text: str) -> str | None:
    """When the model gives no usable quote for a cited passage, pick the passage sentence closest to the
    answer sentence(s) that cite it. Verbatim by construction (it is cut from the passage)."""
    from rapidfuzz import fuzz

    claims = [s for s in re.split(r"(?<=[.!?])\s+", answer) if chunk_id in s]
    if not claims:
        return None
    claim = re.sub(r"\[[^\]]+\]", "", " ".join(claims))
    sents = [s.strip() for s in re.split(r"(?<=[.;])\s+", chunk_text) if 25 <= len(s.strip()) <= 400]
    if not sents:
        return None
    best = max(sents, key=lambda s: fuzz.token_set_ratio(claim, s))
    return best if fuzz.token_set_ratio(claim, best) >= 50 else None


async def answer_stream(question: str) -> AsyncIterator[dict]:
    hits = _retrieve(question)
    by_id = {h["chunk_id"]: h for h in hits}
    meta: list = []
    buf, emitted = "", 0
    try:
        async for piece in stream_text("chat", _prompt(question, hits), "strong",
                                       scope=f"chat:{question.strip().lower()}", meta_out=meta):
            buf += piece
            k = buf.find(MARKER)
            safe_end = k if k >= 0 else max(emitted, len(buf) - len(MARKER))
            if safe_end > emitted:
                yield {"type": "token", "text": buf[emitted:safe_end]}
                emitted = safe_end
    except LLMUnavailable as e:
        yield {"type": "error", "message": str(e)}
        return
    k = buf.find(MARKER)
    answer = buf[:k] if k >= 0 else buf
    if len(answer) > emitted:
        yield {"type": "token", "text": answer[emitted:]}
    quotes = _parse_quotes(buf[k + len(MARKER):]) if k >= 0 else []
    cited = [c for c in dict.fromkeys(re.findall(r"([A-Za-z0-9_.\-]+#\d{3})", answer)) if c in by_id]
    checked = []
    for q in quotes[:3]:
        cid = q.get("chunk_id")
        src = by_id[cid]["text"] if cid in by_id else ""
        if cid and not src:
            try:
                src = sources.body(cid.split("#")[0])
            except KeyError:
                src = ""
        v = verify_quote(q["quote"], src)
        checked.append({"chunk_id": cid, "quote": q["quote"], "verified": v["verified"], "score": v["score"]})
    quoted_chunks = {q["chunk_id"] for q in checked}
    for cid in cited:
        if cid in quoted_chunks or len(checked) >= 3:
            continue
        q = _best_sentence(answer, cid, by_id[cid]["text"])
        if q:
            v = verify_quote(q, by_id[cid]["text"])
            checked.append({"chunk_id": cid, "quote": q, "verified": v["verified"], "score": v["score"], "origin": "matched"})
    citations = [{"chunk_id": c, "title": by_id[c]["title"], "url": by_id[c].get("url"), "doc_id": by_id[c]["doc_id"]}
                 for c in cited]
    m = meta[-1].model_dump() if meta else None
    yield {"type": "done", "answer": answer.strip(), "citations": citations, "quotes": checked,
           "certainty_warning": bool(CERTAINTY.search(answer)), "meta": m,
           "retrieved": [h["chunk_id"] for h in hits]}
