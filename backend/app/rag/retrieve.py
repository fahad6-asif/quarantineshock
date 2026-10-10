"""Retrieval helpers over the Chroma collections.

Embedding runs locally on CPU (Chroma's ONNX MiniLM), which costs ~0.1 s per query. The agent repeats the
same fixed queries on every run, so raw query results are memoized per process (cleared on re-ingest).
"""
from __future__ import annotations

import copy
import json
import math
from functools import lru_cache

from . import store


@lru_cache(maxsize=512)
def _query(collection: str, queries: tuple[str, ...], k: int, where_json: str) -> dict:
    col = store.collection(collection)
    where = json.loads(where_json) if where_json else None
    return col.query(query_texts=list(queries), n_results=k, where=where)


@lru_cache(maxsize=16)
def _all_chunks(where_json: str) -> dict:
    col = store.collection(store.RULEBOOK)
    return col.get(where=json.loads(where_json) if where_json else None)


def clear_caches() -> None:
    _query.cache_clear()
    _all_chunks.cache_clear()


def _where(types: list[str] | None) -> str:
    return json.dumps({"type": {"$in": sorted(types)}}) if types else ""


def _hits(res: dict, qi: int) -> list[dict]:
    return [{"chunk_id": cid, "text": res["documents"][qi][i], "score": 1 - float(res["distances"][qi][i]),
             **res["metadatas"][qi][i]} for i, cid in enumerate(res["ids"][qi])]


def search(query: str, k: int = 6, types: list[str] | None = None) -> list[dict]:
    return copy.deepcopy(_hits(_query(store.RULEBOOK, (query,), k, _where(types)), 0))


def multi_search(queries: list[str], k: int = 4, types: list[str] | None = None, limit: int = 14) -> list[dict]:
    """Union of top-k per query (one batched embedding call), deduped, keeping best score, ordered by score."""
    res = _query(store.RULEBOOK, tuple(queries), k, _where(types))
    best: dict[str, dict] = {}
    for qi in range(len(queries)):
        for hit in _hits(res, qi):
            if hit["chunk_id"] not in best or hit["score"] > best[hit["chunk_id"]]["score"]:
                best[hit["chunk_id"]] = hit
    return copy.deepcopy(sorted(best.values(), key=lambda h: -h["score"])[:limit])


def keyword_search(phrases: list[str], types: list[str] | None = None, limit: int = 4) -> list[dict]:
    """Lexical complement to embeddings: chunks containing any exact phrase (case-insensitive).
    Catches table-like passages (host lists, footnotes) that embed poorly."""
    res = _all_chunks(_where(types))
    lows = [t.lower() for t in res["documents"]]
    n_docs = max(len(lows), 1)
    # IDF weighting: a rare word ("frozen") counts far more than a common one ("avocado")
    idf = {p: math.log(1 + n_docs / (1 + sum(p.lower() in t for t in lows))) for p in phrases}
    out = []
    for cid, text, low, meta in zip(res["ids"], res["documents"], lows, res["metadatas"]):
        score = sum(idf[p] for p in phrases if p.lower() in low)
        if score:
            out.append({"chunk_id": cid, "text": text, "score": round(score, 3), **meta})
    out.sort(key=lambda h: (-h["score"], h["chunk_id"]))
    return copy.deepcopy(out[:limit])


@lru_cache(maxsize=1024)
def _chunk(chunk_id: str) -> dict | None:
    res = store.collection(store.RULEBOOK).get(ids=[chunk_id])
    if not res["ids"]:
        return None
    return {"chunk_id": chunk_id, "text": res["documents"][0], **res["metadatas"][0]}


def get_chunk(chunk_id: str) -> dict | None:
    c = _chunk(chunk_id)
    return dict(c) if c else None


def commodity_candidates_batch(labels: list[str], k: int = 5) -> list[list[dict]]:
    """Top-k distinct canonical commodities per label, all labels embedded in one call."""
    res = _query(store.COMMODITIES, tuple(labels), k * 3, "")
    out_all = []
    for qi in range(len(labels)):
        seen, out = set(), []
        for i, _ in enumerate(res["ids"][qi]):
            m = res["metadatas"][qi][i]
            if m["canonical"] in seen:
                continue
            seen.add(m["canonical"])
            out.append({"canonical": m["canonical"], "matched_label": res["documents"][qi][i],
                        "score": round(1 - float(res["distances"][qi][i]), 3)})
            if len(out) == k:
                break
        out_all.append(out)
    return out_all


def commodity_candidates(label: str, k: int = 5) -> list[dict]:
    return commodity_candidates_batch([label], k)[0]
