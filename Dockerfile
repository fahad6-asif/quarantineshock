# QuarantineShock: one container = website (static Next.js export) + API (FastAPI) on port 7860.
# Deployed on Render (render.yaml); also works on Hugging Face Spaces or any Docker host.

# ---------- 1. build the website ----------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/scripts ./scripts
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=same-origin NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- 2. API + data ----------
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user backend backend
COPY --chown=user data data
COPY --chown=user sources sources
COPY --chown=user scripts scripts
COPY --from=web --chown=user /web/out frontend/out
# runtime state (sqlite + search index) lives in backend/data; the app user must own the whole tree
RUN mkdir -p /app/backend/data /app/backend/.cache && chown -R user:user /app

USER user
# MALLOC_ARENA_MAX / *_NUM_THREADS keep memory low enough for 512 MB free hosting tiers (e.g. Render free)
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    ORT_NUM_THREADS=1 \
    LLM_PROVIDER=auto \
    STATIC_DIR=/app/frontend/out \
    DEMO_AUTOSTART=2026-06-16_spring-valley-established \
    ANONYMIZED_TELEMETRY=False

# Build the local search index (downloads Chroma's small ONNX embedding model once, at build time).
RUN python scripts/ingest.py

EXPOSE 7860
# $PORT is set by Render (and most hosts); 7860 otherwise (Hugging Face Spaces)
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860}"]
