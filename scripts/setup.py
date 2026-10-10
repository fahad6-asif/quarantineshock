"""One-time setup: venv + pip install, npm install (root + frontend), .env from .env.example.

Usage: python scripts/setup.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV = BACKEND / ".venv"
WIN = os.name == "nt"


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"\n> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True, shell=WIN and cmd[0] in ("npm", "npx"))


def main() -> None:
    if sys.version_info < (3, 11):
        sys.exit("Python 3.11+ is required.")
    if not VENV.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    py = VENV / ("Scripts/python.exe" if WIN else "bin/python")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(py), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
    if shutil.which("npm") is None:
        sys.exit("npm not found. Install Node.js LTS from https://nodejs.org and re-run.")
    run(["npm", "install"])
    run(["npm", "install"], cwd=ROOT / "frontend")
    env, example = ROOT / ".env", ROOT / ".env.example"
    if not env.exists():
        shutil.copy(example, env)
        print("\nCreated .env from .env.example. Paste your GEMINI_API_KEY into it.")
    print("\nSetup done. Next: python scripts/ingest.py")


if __name__ == "__main__":
    main()
