"""sources/ -> chunks -> Chroma 'rulebook'; commodity vocabulary -> Chroma 'commodities' + host table."""
from __future__ import annotations

import hashlib
import json
import re

from ..config import DATA
from . import sources, store

MAX_CHARS = 900


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_SENT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"“•§0-9])")


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Sentence-packed chunks with a one-sentence overlap. Each chunk is a verbatim span of norm(text)."""
    t = norm(text)
    sents = [s for s in _SENT.split(t) if s]
    chunks, cur = [], []
    for s in sents:
        while len(s) > max_chars * 1.5:  # very long run-on (tables): hard split on spaces
            cut = s.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if cur:
                chunks.append(" ".join(cur))
                cur = []
            chunks.append(s[:cut])
            s = s[cut:].lstrip()
        if cur and len(" ".join(cur)) + len(s) + 1 > max_chars:
            chunks.append(" ".join(cur))
            cur = [cur[-1]] if len(cur[-1]) < max_chars / 3 else []
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def source_set_hash() -> str:
    h = hashlib.sha256()
    for d in sources.manifest():
        h.update(d["id"].encode())
        h.update(sources.body(d["id"]).encode("utf-8"))
    return h.hexdigest()[:16]


def ingest_rulebook() -> int:
    col = store.reset_collection(store.RULEBOOK)
    ids, docs, metas = [], [], []
    for d in sources.manifest():
        for i, c in enumerate(chunk_text(sources.body(d["id"]))):
            ids.append(f"{d['id']}#{i:03d}")
            docs.append(c)
            metas.append({"doc_id": d["id"], "title": d["title"], "type": d["type"], "url": d.get("url") or "",
                          "publisher": d.get("publisher") or "", "seq": i})
    for k in range(0, len(ids), 64):
        col.add(ids=ids[k:k + 64], documents=docs[k:k + 64], metadatas=metas[k:k + 64])
    return len(ids)


def _evidence(text: str, term: str) -> str | None:
    t = norm(text)
    i = t.lower().find(term.lower())
    if i < 0:
        return None
    a = max(0, t.rfind(" ", 0, max(0, i - 60)) + 1)
    b = t.find(" ", min(len(t), i + len(term) + 60))
    return t[a: b if b > 0 else len(t)].strip()


def build_host_table() -> dict:
    vocab = json.loads((DATA / "commodity_vocab.json").read_text("utf-8"))["items"]
    fed = sources.body("mexfly_hosts")
    state = sources.body("cdfa_3417")
    table = {}
    for it in vocab:
        fed_ev = next((e for term in it["federal_terms"] if (e := _evidence(fed, term))), None)
        st_ev = next((e for term in it["state_terms"] if (e := _evidence(state, term))), None)
        table[it["name"]] = {
            "host": bool(fed_ev or st_ev),
            "federal": bool(fed_ev), "state": bool(st_ev),
            "federal_evidence": fed_ev, "state_evidence": st_ev,
            "aliases": it["aliases"],
        }
    (DATA / "host_table.json").write_text(json.dumps(table, indent=2, ensure_ascii=False), "utf-8")
    return table


def ingest_commodities(table: dict) -> int:
    col = store.reset_collection(store.COMMODITIES)
    ids, docs, metas = [], [], []
    for name, row in table.items():
        for j, label in enumerate([name, *row["aliases"]]):
            ids.append(f"{name}|{j}")
            docs.append(label)
            metas.append({"canonical": name, "host": row["host"]})
    col.add(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def run() -> dict:
    from .retrieve import clear_caches

    clear_caches()
    n_chunks = ingest_rulebook()
    table = build_host_table()
    n_comm = ingest_commodities(table)
    return {"chunks": n_chunks, "commodity_labels": n_comm, "hosts": sorted(k for k, v in table.items() if v["host"]),
            "non_hosts": sorted(k for k, v in table.items() if not v["host"]), "source_set_hash": source_set_hash()}
