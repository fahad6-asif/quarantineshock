"""Node 5: extract rules (RAG over the real regulations + host list). Cached per source set."""
from __future__ import annotations

from ... import prompts
from ...llm import generate_json
from ...rag import retrieve
from ...schemas import RuleSet
from ..context import RunContext

QUERIES = [
    "regulated articles Mexican fruit fly",
    "host list avocado citrus regulated articles",
    "exemptions canned dried frozen",
    "avocado varieties not regulated footnote host list",
    "treatment certificate movement from quarantined area",
    "Hass avocado requirements quarantined area",
    "moved for processing compliance agreement",
    "restrictions wholesale commercially produced within the area under quarantine",
]
EXEMPTION_PHRASES = ["are not regulated", "not regulated", "exempt", "unless the"]


async def extract_rules(state: dict, ctx: RunContext) -> dict:
    types = ["regulation", "host_list"]
    hits = retrieve.multi_search(QUERIES, k=4, types=types, limit=16)
    # hybrid: exemption language often sits in tables/footnotes that embeddings rank poorly
    seen = {h["chunk_id"] for h in hits}
    hits += [h for h in retrieve.keyword_search(EXEMPTION_PHRASES, types=types, limit=4) if h["chunk_id"] not in seen]
    hits.sort(key=lambda h: h["chunk_id"])  # stable order -> stable cache key
    passages = "\n\n".join(f"[{h['chunk_id']}] ({h['title']})\n{h['text']}" for h in hits)
    rs, _ = await generate_json("extract_rules", prompts.render("extract_rules", passages=passages), RuleSet,
                                "strong", scope="rules")
    data = rs.model_dump(mode="json")
    data["retrieved_chunk_ids"] = [h["chunk_id"] for h in hits]
    return {"ruleset": data,
            "_message": f"Extracted {len(rs.rules)} rules and {len(rs.ambiguities)} ambiguities from {len(hits)} source passages",
            "_output": data}
