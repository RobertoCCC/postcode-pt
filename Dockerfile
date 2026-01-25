# syntax=docker/dockerfile:1.7

# ─── Builder stage ────────────────────────────────────────────
# Installs deps, downloads CSVs, runs ingestion so the runtime
# image ships with a pre-populated SQLite — no cold-start cost.
FROM python:3.14-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Cache deps independently of source so source-only edits don't bust this layer.
# Include dev deps here — the ingestion script needs httpx (dev-only dependency).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Install the project itself. README is metadata (pyproject.toml: readme = ...).
COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen

# Download the open dataset and bake the populated SQLite into the image.
COPY scripts/ ./scripts/
RUN .venv/bin/python scripts/download_data.py \
    && .venv/bin/python scripts/ingest.py \
    && rm -rf data/

# Strip dev deps from the venv so the runtime image stays lean.
RUN uv sync --frozen --no-dev


# ─── Runtime stage ────────────────────────────────────────────
FROM python:3.14-slim-bookworm AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/postcode_pt.db /app/postcode_pt.db

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Render injects $PORT; fall back to 8000 for local docker run.
CMD ["sh", "-c", "uvicorn postcode_pt.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
