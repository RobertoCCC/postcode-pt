# postcode-pt

[![CI](https://github.com/RobertoCCC/postcode-pt/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoCCC/postcode-pt/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/live%20demo-postcode--pt.onrender.com-2ecc71?logo=render&logoColor=white)](https://postcode-pt.onrender.com/docs)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-1F5082)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A public REST API for **Portuguese postal codes (CP4-CP3)** — lookup the locality, municipality and district behind any address.

**Try it live:** [Swagger UI](https://postcode-pt.onrender.com/docs) · [`GET /v1/postal-codes/1100-038`](https://postcode-pt.onrender.com/v1/postal-codes/1100-038) · [`GET /v1/districts`](https://postcode-pt.onrender.com/v1/districts)
*(Free Render instance — first request after idle may take ~50s to wake up.)*

Built around the open [`centraldedados/codigos_postais`](https://github.com/centraldedados/codigos_postais) dataset (~326k postal codes, 35k localities, 308 municipalities, 29 districts).

## Features

- Async FastAPI app with auto-generated OpenAPI / Swagger UI at `/docs`
- Clean three-layer architecture: `api → services → db`
- Async SQLAlchemy 2.0 + SQLModel, eager loading via `selectinload` (no N+1)
- Path-level validation: regex-checked `CP4` / `CP3` → automatic `422` + documented in OpenAPI
- API versioned from day one under `/v1/`
- Decoupled response models (Pydantic) from ORM models (SQLModel) so DB and API shapes evolve independently
- Two-pass bulk ingestion of the full dataset in ~3s on a laptop
- Pytest suite with `httpx.AsyncClient` + `ASGITransport` (no live server needed)
- Drop-in Postgres support via `DATABASE_URL` (just swap the driver)

## Quick start

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clone and install
git clone https://github.com/RobertoCCC/postcode-pt.git
cd postcode-pt
uv sync

# 2. Fetch the open dataset
uv run python scripts/download_data.py

# 3. Ingest into SQLite (~3s)
uv run python scripts/ingest.py

# 4. Run the API
uv run uvicorn postcode_pt.main:app --reload
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

## API

Base URL: `/v1`

### `GET /v1/postal-codes/{cp4}-{cp3}`

Look up a postal code. Returns a list — the same code can have multiple entries (different street segments, CTT customer records).

```bash
$ curl -s http://localhost:8000/v1/postal-codes/1100-038
```

```json
[
  {
    "code": "1100-038",
    "designation": "LISBOA",
    "street": { "type": "Rua", "name": "do Arsenal" },
    "locality":     { "code": "21696", "name": "Lisboa" },
    "municipality": { "code": "1106",  "name": "Lisboa" },
    "district":     { "code": "11",    "name": "Lisboa" }
  }
]
```

| Status | Meaning                            |
| ------ | ---------------------------------- |
| `200`  | One or more entries found          |
| `404`  | No entries for this `CP4-CP3`      |
| `422`  | `CP4` not 4 digits or `CP3` not 3  |

### `GET /v1/districts`

List all 29 Portuguese districts (18 mainland + 11 islands).

```bash
$ curl -s http://localhost:8000/v1/districts
```

```json
[
  { "code": "01", "name": "Aveiro" },
  { "code": "02", "name": "Beja" },
  { "code": "03", "name": "Braga" },
  "..."
]
```

### `GET /v1/districts/{code}/municipalities`

List the municipalities in a given district, ordered by name.

```bash
$ curl -s http://localhost:8000/v1/districts/11/municipalities
```

```json
[
  {
    "code": "1101",
    "name": "Alenquer",
    "district": { "code": "11", "name": "Lisboa" }
  },
  "..."
]
```

### `GET /v1/health`

Liveness probe — returns `{"status": "ok"}`.

## Tech stack

| Choice                 | Why                                                                  |
| ---------------------- | -------------------------------------------------------------------- |
| **Python 3.14**        | Latest stable; modern typing syntax (`str \| None`, `list[T]`)       |
| **FastAPI**            | Async, type-driven, auto OpenAPI; battle-tested for public APIs      |
| **SQLModel + SQLAlchemy 2.0** | Single class for ORM + Pydantic-style validation; async-ready |
| **aiosqlite**          | Async SQLite for dev; one-line swap to `asyncpg` for Postgres        |
| **uv**                 | Fast (Rust) dep resolution + virtualenv + script runner              |
| **pytest + httpx**     | Async tests against the ASGI app in-process — no real server         |
| **ruff + mypy**        | Lint and type-check in CI-ready milliseconds                         |

## Project structure

```
src/postcode_pt/
├── main.py              # FastAPI app entrypoint
├── core/config.py       # pydantic-settings, reads .env
├── api/v1/              # Routers (HTTP layer)
│   ├── postal_codes.py
│   ├── districts.py
│   └── router.py        # mounts /v1 + /v1/health
├── services/            # Business logic — pure functions over a session
├── models/responses.py  # Pydantic response schemas
└── db/
    ├── models.py        # SQLModel tables
    └── session.py       # Async engine + get_session dependency

scripts/
├── download_data.py     # Pull CSVs from centraldedados
└── ingest.py            # Two-pass bulk insert (~3s for 326k rows)

tests/                   # pytest + httpx.AsyncClient + in-memory SQLite
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src tests
```

## Configuration

Copy `.env.example` to `.env` and adjust. Supported variables:

| Variable        | Default                                    | Notes                                       |
| --------------- | ------------------------------------------ | ------------------------------------------- |
| `DATABASE_URL`  | `sqlite+aiosqlite:///./postcode_pt.db`     | Use `postgresql+asyncpg://...` for Postgres |
| `APP_NAME`      | `Postcode PT`                              | Shown in Swagger UI                         |
| `APP_VERSION`   | `0.1.0`                                    | Shown in Swagger UI                         |

## Data source

Postal codes come from [`centraldedados/codigos_postais`](https://github.com/centraldedados/codigos_postais), an open dataset derived from CTT publications and released under [PDDL](https://opendatacommons.org/licenses/pddl/) (Public Domain Dedication License).

This repository's *code* is MIT-licensed; the *data* (once ingested) is PDDL — credit Central de Dados / CTT where appropriate.

## Roadmap

- [x] Dockerfile (multi-stage, with pre-built DB baked in)
- [x] Live deployment on [Render](https://postcode-pt.onrender.com/docs)
- [x] CI on GitHub Actions (ruff, mypy, pytest)
- [ ] Alembic migrations (replace `create_all`)
- [ ] Rate limiting + caching headers
- [ ] docker-compose for local Postgres
- [ ] Custom domain

## License

[MIT](LICENSE) — see file for details.
