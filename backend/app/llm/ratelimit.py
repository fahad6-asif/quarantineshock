"""Client-side rate limiter: spaces calls so a provider never sees more than `rpm` per minute."""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, rpm_getter) -> None:
        self._rpm_getter = rpm_getter
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        rpm = max(float(self._rpm_getter() or 0), 0.0)
        if rpm <= 0:
            return
        interval = 60.0 / rpm
        async with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + interval
        if delay > 0:
            await asyncio.sleep(delay)
