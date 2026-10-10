"""Pydantic schemas for every LLM output plus shared API shapes."""
from __future__ import annotations

import datetime as dt
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["REVIEW", "UNCLEAR", "NOT_HOST", "OUTSIDE"]
HostStatus = Literal["host", "not_host", "unclear"]
Form = Literal["fresh", "frozen", "processed", "dried", "mixed", "unknown"]


# ---------------------------------------------------------------- LLM outputs
class NoticeClass(BaseModel):
    is_quarantine_change: bool
    pest: str
    county: str
    action: Literal["establish", "expand", "merge", "release", "other"]
    confidence: float = Field(ge=0, le=1)


class Detection(BaseModel):
    place: str = Field(description="City/community of the detection, e.g. 'El Cajon'")
    detail: str = Field(description="e.g. 'grapefruit tree, residential property'")
    date: dt.date | None = None
    sex_status: str | None = None
    quote: str = Field(description="verbatim span from the notice")
    place_is_inferred: bool = Field(False, description="true if the notice does not name the city and it was inferred from the quarantine name")


class NoticeExtract(BaseModel):
    notice_date: date
    effective_date: date | None = None
    quarantine_name: str
    action: str
    detections: list[Detection]
    stated_area_sq_mi: float | None = None
    stated_commercial_acres: float | None = None
    crops_mentioned: list[str] = []
    ambiguities: list[str] = []


class Rule(BaseModel):
    id: str
    applies_to: list[str]
    requirement: str
    conditions: list[str] = []
    exemptions: list[str] = []
    quote: str
    source_chunk_id: str


class Ambiguity(BaseModel):
    topic: str
    explanation: str
    affected_forms: list[str] = []
    quote: str | None = None
    source_chunk_id: str | None = None


class RuleSet(BaseModel):
    rules: list[Rule]
    host_commodities: list[str] = []
    ambiguities: list[Ambiguity] = []


class RadiusFinding(BaseModel):
    found: bool
    radius_miles: float | None = None
    quote: str | None = None
    source_chunk_id: str | None = None


class NormalizedItem(BaseModel):
    id: str
    canonical_commodity: str
    form: Form
    host_status: HostStatus
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class NormalizedBatch(BaseModel):
    items: list[NormalizedItem]


class ActionPack(BaseModel):
    shipment_id: str
    explanation: str
    rule_ids: list[str] = []
    checklist: list[str] = []
    email_subject: str
    email_body: str
    driver_hold_note: str


class ActionBatch(BaseModel):
    packs: list[ActionPack]


class JudgeVerdict(BaseModel):
    id: str
    verdict: Literal["supports", "partial", "no"]


class JudgeBatch(BaseModel):
    verdicts: list[JudgeVerdict]


class RunSummary(BaseModel):
    summary: str


# ---------------------------------------------------------------- non-LLM shapes
class CallMeta(BaseModel):
    provider: str  # gemini | openrouter | cache | replay | none
    model: str | None = None
    cached: bool = False
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    attempts: int = 1
    task: str | None = None
    note: str | None = None


class Shipment(BaseModel):
    id: str
    pickup_date: date
    origin_name: str
    lat: float | None = None
    lon: float | None = None
    product_raw: str
    quantity: str
    destination: str
    carrier: str
    notes: str = ""
