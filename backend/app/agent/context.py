"""Per-run context shared by the agent nodes (not part of the LangGraph state proper)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..events import RunChannel


@dataclass
class RunContext:
    run_id: str
    notice: dict  # manifest entry
    notice_text: str
    prev_results: list[dict]  # results of every earlier notice, in timeline order
    channel: RunChannel
    pace: bool = True  # small delays for cached steps so the UI stepper is watchable
    warnings: list[str] = field(default_factory=list)

    @property
    def notice_id(self) -> str:
        return self.notice["id"]

    @property
    def previous(self) -> dict | None:
        return self.prev_results[-1] if self.prev_results else None

    async def progress(self, node: str, message: str, **extra) -> None:
        await self.channel.emit(node, "progress", message, **extra)
