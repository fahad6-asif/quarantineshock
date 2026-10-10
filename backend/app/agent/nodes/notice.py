"""Nodes 1-2: classify the notice, extract structured facts."""
from __future__ import annotations

from ... import prompts
from ...llm import generate_json
from ...schemas import NoticeClass, NoticeExtract
from ..context import RunContext


async def classify_notice(state: dict, ctx: RunContext) -> dict:
    p = prompts.render("classify_notice", notice_text=ctx.notice_text)
    cls, _ = await generate_json("classify_notice", p, NoticeClass, "fast", scope=ctx.notice_id)
    verdict = "quarantine change" if cls.is_quarantine_change else "not a quarantine change"
    return {"classification": cls.model_dump(mode="json"),
            "_message": f"{cls.pest}: {verdict} ({cls.action}) · {cls.county}",
            "_output": cls.model_dump(mode="json")}


async def extract_notice(state: dict, ctx: RunContext) -> dict:
    p = prompts.render("extract_notice", notice_text=ctx.notice_text, quarantine=ctx.notice["quarantine"],
                       effective_date=ctx.notice["effective_date"])
    ex, _ = await generate_json("extract_notice", p, NoticeExtract, "strong", scope=ctx.notice_id)
    dets = ex.detections
    if dets:
        parts = [f"{d.place}{' (inferred)' if d.place_is_inferred else ''}, {d.date.strftime('%b %d') if d.date else 'date n/a'}" for d in dets]
        msg = f"Found {len(dets)} detection{'s' if len(dets) != 1 else ''}: " + "; ".join(parts)
    else:
        msg = "No detections stated in this notice"
    if ex.stated_area_sq_mi:
        msg += f" · official area {ex.stated_area_sq_mi:g} sq mi"
    if ex.stated_commercial_acres is not None:
        msg += f" · {ex.stated_commercial_acres:g} commercial acres"
    return {"extract": ex.model_dump(mode="json"), "_message": msg, "_output": ex.model_dump(mode="json")}
