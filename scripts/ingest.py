"""Ingest the downloaded CSVs into the DB.

Run with:
    uv run python scripts/ingest.py

Strategy:
    1. Drop + recreate all tables.
    2. Insert districts (~24).
    3. Insert municipalities (~308).
    4. First pass over postal_codes.csv → collect unique localities, insert them.
    5. Second pass over postal_codes.csv → insert all postal codes with FK to locality.
"""

from __future__ import annotations

import asyncio
import csv
import sys
import time
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from postcode_pt.db.models import District, Locality, Municipality, PostalCode
from postcode_pt.db.session import async_session_factory, engine

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BATCH_SIZE = 5000


async def reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


async def apply_sqlite_pragmas(session: AsyncSession) -> None:
    """Speed up bulk insert. Dev-only — would not use in production."""
    await session.execute(text("PRAGMA journal_mode = MEMORY"))
    await session.execute(text("PRAGMA synchronous = OFF"))


def read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        yield from csv.DictReader(f)


def compose_street_name(row: dict[str, str]) -> str | None:
    """Join prep1 + titulo + prep2 + nome → 'de Nossa Senhora do Alívio'."""
    parts = [row["prep1"], row["titulo_arteria"], row["prep2"], row["nome_arteria"]]
    full = " ".join(p for p in parts if p).strip()
    return full or None


async def ingest_districts(session: AsyncSession) -> dict[str, int]:
    rows = [
        {"code": r["cod_distrito"], "name": r["nome_distrito"]}
        for r in read_csv(DATA_DIR / "distritos.csv")
    ]
    await session.execute(insert(District), rows)
    await session.commit()

    result = await session.execute(text("SELECT code, id FROM districts"))
    lookup = {row[0]: row[1] for row in result.fetchall()}
    print(f"  districts:      {len(lookup):>7,} rows")
    return lookup


async def ingest_municipalities(
    session: AsyncSession, district_id_by_code: dict[str, int]
) -> dict[str, int]:
    rows = []
    for r in read_csv(DATA_DIR / "concelhos.csv"):
        rows.append(
            {
                "code": f"{r['cod_distrito']}{r['cod_concelho']}",
                "name": r["nome_concelho"],
                "district_id": district_id_by_code[r["cod_distrito"]],
            }
        )
    await session.execute(insert(Municipality), rows)
    await session.commit()

    result = await session.execute(text("SELECT code, id FROM municipalities"))
    lookup = {row[0]: row[1] for row in result.fetchall()}
    print(f"  municipalities: {len(lookup):>7,} rows")
    return lookup


async def ingest_localities(
    session: AsyncSession, municipality_id_by_code: dict[str, int]
) -> dict[tuple[str, str, str], int]:
    """First pass: collect unique localities from the postal codes CSV."""
    unique: dict[tuple[str, str, str], tuple[str, int]] = {}
    skipped = 0
    for r in read_csv(DATA_DIR / "codigos_postais.csv"):
        cd, cc, cl = r["cod_distrito"], r["cod_concelho"], r["cod_localidade"]
        if not cl:
            continue
        mun_code = f"{cd}{cc}"
        mun_id = municipality_id_by_code.get(mun_code)
        if mun_id is None:
            skipped += 1
            continue
        key = (cd, cc, cl)
        if key not in unique:
            unique[key] = (r["nome_localidade"], mun_id)

    rows = [
        {"code": cl, "name": name, "municipality_id": mun_id}
        for (_cd, _cc, cl), (name, mun_id) in unique.items()
    ]
    for i in range(0, len(rows), BATCH_SIZE):
        await session.execute(insert(Locality), rows[i : i + BATCH_SIZE])
    await session.commit()

    # Build (cd, cc, cl) → locality.id lookup for pass 2.
    municipality_code_by_id = {v: k for k, v in municipality_id_by_code.items()}
    result = await session.execute(
        text("SELECT municipality_id, code, id FROM localities")
    )
    locality_id_lookup: dict[tuple[str, str, str], int] = {}
    for mun_id, cl, loc_id in result.fetchall():
        mun_code = municipality_code_by_id[mun_id]
        cd, cc = mun_code[:2], mun_code[2:]
        locality_id_lookup[(cd, cc, cl)] = loc_id

    print(f"  localities:     {len(locality_id_lookup):>7,} rows (skipped {skipped} unmatched)")
    return locality_id_lookup


async def ingest_postal_codes(
    session: AsyncSession, locality_id_lookup: dict[tuple[str, str, str], int]
) -> None:
    """Second pass: stream the CSV and bulk-insert postal codes."""
    batch: list[dict] = []
    inserted = 0
    skipped_no_locality = 0

    for r in read_csv(DATA_DIR / "codigos_postais.csv"):
        cd, cc, cl = r["cod_distrito"], r["cod_concelho"], r["cod_localidade"]
        if not cl:
            skipped_no_locality += 1
            continue
        loc_id = locality_id_lookup.get((cd, cc, cl))
        if loc_id is None:
            skipped_no_locality += 1
            continue

        batch.append(
            {
                "cp4": r["num_cod_postal"],
                "cp3": r["ext_cod_postal"],
                "designation": r["desig_postal"],
                "street_type": r["tipo_arteria"] or None,
                "street_name": compose_street_name(r),
                "locality_id": loc_id,
            }
        )

        if len(batch) >= BATCH_SIZE:
            await session.execute(insert(PostalCode), batch)
            inserted += len(batch)
            batch.clear()

    if batch:
        await session.execute(insert(PostalCode), batch)
        inserted += len(batch)

    await session.commit()
    print(f"  postal_codes:   {inserted:>7,} rows (skipped {skipped_no_locality} without locality)")


async def main() -> int:
    if not (DATA_DIR / "codigos_postais.csv").exists():
        print(f"ERROR: dataset not found in {DATA_DIR}. Run scripts/download_data.py first.")
        return 1

    print("Resetting schema...")
    await reset_schema()

    print("Ingesting:")
    t0 = time.perf_counter()
    async with async_session_factory() as session:
        await apply_sqlite_pragmas(session)
        district_ids = await ingest_districts(session)
        municipality_ids = await ingest_municipalities(session, district_ids)
        locality_ids = await ingest_localities(session, municipality_ids)
        await ingest_postal_codes(session, locality_ids)

    print(f"\nDone in {time.perf_counter() - t0:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
