"""FastAPI entry point: uvicorn app.main:app --port 8000 (run from backend/).

In the deployed container it also serves the statically exported website (STATIC_DIR) from the same
address, and can prepare the demo on startup (DEMO_AUTOSTART=<notice id>).
"""
from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .routes import router

log = logging.getLogger("uvicorn.error")
mimetypes.add_type("text/javascript", ".mjs")  # MapLibre's module worker must be served as JavaScript


def _warm_retrieval() -> None:
    """Load the local embedding model and pre-run the agent's fixed retrieval queries, so the first
    notice processed in a demo is as fast as the rest."""
    try:
        from .agent.nodes.rules import EXEMPTION_PHRASES, QUERIES
        from .agent.nodes.shipments import load_shipments
        from .rag import retrieve

        retrieve.multi_search(QUERIES, k=4, types=["regulation", "host_list"], limit=16)
        retrieve.keyword_search(EXEMPTION_PHRASES, types=["regulation", "host_list"], limit=4)
        retrieve.multi_search(["quarantine area radius miles around detections", "4.5 mile radius quarantine Mexican fruit fly",
                               "initial area under quarantine minimum radius"], k=3, types=["regulation"], limit=6)
        retrieve.commodity_candidates_batch([s["product_raw"] for s in load_shipments()], k=5)
        log.info("retrieval warm-up done")
    except Exception as e:  # noqa: BLE001  (e.g. index not built yet: scripts/ingest.py)
        log.warning("retrieval warm-up skipped: %s", e)


async def _autostart(target: str, warm: asyncio.Task) -> None:
    """Fresh deployment: process the notices up to `target` (from the committed LLM cache) so visitors
    land on a ready demo."""
    from .routes import _fast_forward

    await warm  # share the warmed search index instead of racing it
    if not db.latest_done_runs():
        log.info("demo autostart: preparing notices up to %s", target)
        await _fast_forward(target)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    warm = asyncio.create_task(asyncio.to_thread(_warm_retrieval))
    auto = None
    if os.getenv("DEMO_AUTOSTART"):
        auto = asyncio.create_task(_autostart(os.environ["DEMO_AUTOSTART"], warm))
    yield
    warm.cancel()
    if auto:
        auto.cancel()


app = FastAPI(title="QuarantineShock API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

# The website (static export). Mounted last so /api/* always wins.
_static = os.getenv("STATIC_DIR")
if _static and Path(_static).is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="site")
