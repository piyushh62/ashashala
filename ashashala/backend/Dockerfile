# AshaShala backend — multi-stage image.
#
# IMPORTANT: build with the repo's `ashashala/` dir as context (NOT backend/),
# because app/services/model_registry.py loads ../config/model_registry.yaml:
#
#   docker build -f backend/Dockerfile -t ashashala-backend .
#
# Final layout in the image:
#   /app/backend/...            (application code, WORKDIR)
#   /app/config/model_registry.yaml

# ---- builder: install deps into an isolated venv ----
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# ---- runtime: slim image, non-root ----
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# libpq for psycopg/asyncpg runtime; curl for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY backend/ /app/backend/
COPY config/ /app/config/

WORKDIR /app/backend
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1

# Shell form so ${PORT} (Render injects it) is expanded at runtime.
# Migrations run first so the schema is current before seed/app code touches
# it. Both migration and seed steps are idempotent (safe to re-run on every
# restart) and must never block the API from coming up, so failures there are
# logged but don't stop uvicorn.
CMD alembic upgrade head; python scripts/seed.py; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
