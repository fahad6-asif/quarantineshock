"""In-memory event bus per run. SSE subscribers get past events first, then live ones."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone


class RunChannel:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.events: list[dict] = []
        self.finished = False
        self._cond = asyncio.Condition()

    async def emit(self, node: str, status: str, message: str = "", meta: dict | None = None, **extra) -> dict:
        ev = {"run_id": self.run_id, "seq": len(self.events), "node": node, "status": status, "message": message,
              "meta": meta, "ts": datetime.now(timezone.utc).isoformat(), **extra}
        async with self._cond:
            self.events.append(ev)
            self._cond.notify_all()
        return ev

    async def close(self) -> None:
        async with self._cond:
            self.finished = True
            self._cond.notify_all()

    async def subscribe(self):
        i = 0
        while True:
            async with self._cond:
                while i >= len(self.events) and not self.finished:
                    await self._cond.wait()
                batch = self.events[i:]
                done = self.finished
            for ev in batch:
                yield ev
            i += len(batch)
            if done and i >= len(self.events):
                return


_channels: dict[str, RunChannel] = {}


def channel(run_id: str) -> RunChannel:
    if run_id not in _channels:
        _channels[run_id] = RunChannel(run_id)
    return _channels[run_id]


def existing(run_id: str) -> RunChannel | None:
    return _channels.get(run_id)
