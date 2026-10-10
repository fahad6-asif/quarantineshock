"""sources/ -> text -> chunks -> Chroma. Also builds data/host_table.json from the real host lists.

Usage: python scripts/ingest.py
(Rebuilds sources/notices + sources/regs from sources/raw first if build_sources.py is present.)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if (ROOT / "sources" / "raw" / "index.json").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_sources.py")], check=True)
    from app.rag import ingest, retrieve

    print("Embedding chunks locally (first run downloads Chroma's small ONNX model, ~80 MB)...")
    info = ingest.run()
    print(f"Rulebook chunks: {info['chunks']}  |  commodity labels: {info['commodity_labels']}")
    print(f"Hosts per the real lists ({len(info['hosts'])}): {', '.join(info['hosts'])}")
    print(f"Not on either Mexfly list ({len(info['non_hosts'])}): {', '.join(info['non_hosts'])}")
    print("\nSample retrieval for 'avocado regulated articles':")
    for h in retrieve.search("avocado regulated articles", k=3):
        print(f"  [{h['chunk_id']}] score={h['score']:.2f}  {h['text'][:160]}...")


if __name__ == "__main__":
    main()
