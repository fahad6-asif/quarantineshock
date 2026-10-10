"""SQLite persistence: runs, human decisions, audit log."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from sqlmodel import Field, Session, SQLModel, create_engine, select

from .config import STATE_DIR

STATE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("QS_DB_PATH") or str(STATE_DIR / "quarantineshock.db")  # tests point this at a temp file
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def now() -> datetime:
    return datetime.now(timezone.utc)


class RunRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    notice_id: str = Field(index=True)
    status: str = "running"  # running | done | error
    provider_mode: str = "auto"
    created_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    error: str | None = None
    result_json: str = "{}"
    events_json: str = "[]"


class DecisionRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    shipment_id: str = Field(index=True)
    notice_id: str
    decision: str  # approve | hold | escalate
    note: str = ""
    created_at: datetime = Field(default_factory=now)


class AuditRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now)
    actor: str = "system"
    action: str
    detail: str = ""


def init() -> None:
    SQLModel.metadata.create_all(engine)


def audit(action: str, detail: str = "", actor: str = "system") -> None:
    with Session(engine) as s:
        s.add(AuditRow(action=action, detail=detail, actor=actor))
        s.commit()


def save_run(row: RunRow) -> None:
    with Session(engine) as s:
        s.merge(row)
        s.commit()


def get_run(run_id: str) -> RunRow | None:
    with Session(engine) as s:
        return s.get(RunRow, run_id)


def latest_done_runs() -> dict[str, RunRow]:
    """notice_id -> most recent successful run."""
    with Session(engine) as s:
        rows = s.exec(select(RunRow).where(RunRow.status == "done").order_by(RunRow.created_at)).all()
    out: dict[str, RunRow] = {}
    for r in rows:
        out[r.notice_id] = r
    return out


def run_result(row: RunRow | None) -> dict:
    return json.loads(row.result_json) if row else {}


def decisions_for(shipment_id: str | None = None) -> list[DecisionRow]:
    with Session(engine) as s:
        q = select(DecisionRow).order_by(DecisionRow.created_at)
        if shipment_id:
            q = q.where(DecisionRow.shipment_id == shipment_id)
        return list(s.exec(q).all())


def add_decision(d: DecisionRow) -> DecisionRow:
    with Session(engine) as s:
        s.add(d)
        s.commit()
        s.refresh(d)
        return d


def all_audit() -> list[AuditRow]:
    with Session(engine) as s:
        return list(s.exec(select(AuditRow).order_by(AuditRow.created_at)).all())


def reset_demo() -> None:
    with Session(engine) as s:
        for model in (RunRow, DecisionRow):
            for row in s.exec(select(model)).all():
                s.delete(row)
        s.commit()
