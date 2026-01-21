from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from postcode_pt.db import models  # noqa: F401 — register tables with metadata
from postcode_pt.db.models import District, Locality, Municipality, PostalCode
from postcode_pt.db.session import get_session
from postcode_pt.main import app


@pytest.fixture
async def engine() -> AsyncGenerator:
    """Fresh in-memory SQLite per test, shared across connections via StaticPool."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def seed(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Minimal hierarchy: 2 districts → 3 municipalities → 3 localities → 4 postal codes.

    1100-039 has 2 entries to exercise the "same code, multiple rows" case.
    """
    async with session_factory() as s:
        lisboa = District(code="11", name="Lisboa")
        porto = District(code="13", name="Porto")
        s.add_all([lisboa, porto])
        await s.flush()

        m_lisboa = Municipality(code="1106", name="Lisboa", district_id=lisboa.id)  # type: ignore[arg-type]
        m_sintra = Municipality(code="1111", name="Sintra", district_id=lisboa.id)  # type: ignore[arg-type]
        m_porto = Municipality(code="1312", name="Porto", district_id=porto.id)  # type: ignore[arg-type]
        s.add_all([m_lisboa, m_sintra, m_porto])
        await s.flush()

        l_lisboa = Locality(code="10123", name="LISBOA", municipality_id=m_lisboa.id)  # type: ignore[arg-type]
        l_sintra = Locality(code="10456", name="SINTRA", municipality_id=m_sintra.id)  # type: ignore[arg-type]
        l_porto = Locality(code="13001", name="PORTO", municipality_id=m_porto.id)  # type: ignore[arg-type]
        s.add_all([l_lisboa, l_sintra, l_porto])
        await s.flush()

        s.add_all(
            [
                PostalCode(
                    cp4="1100",
                    cp3="038",
                    designation="LISBOA",
                    street_type="Rua",
                    street_name="do Arsenal",
                    locality_id=l_lisboa.id,  # type: ignore[arg-type]
                ),
                PostalCode(
                    cp4="1100",
                    cp3="039",
                    designation="LISBOA",
                    street_type="Rua",
                    street_name="da Alfândega",
                    locality_id=l_lisboa.id,  # type: ignore[arg-type]
                ),
                PostalCode(
                    cp4="1100",
                    cp3="039",
                    designation="LISBOA",
                    street_type="Praça",
                    street_name="do Comércio",
                    locality_id=l_lisboa.id,  # type: ignore[arg-type]
                ),
                PostalCode(
                    cp4="2710",
                    cp3="001",
                    designation="SINTRA",
                    street_type=None,
                    street_name=None,
                    locality_id=l_sintra.id,  # type: ignore[arg-type]
                ),
                PostalCode(
                    cp4="4000",
                    cp3="001",
                    designation="PORTO",
                    street_type="Avenida",
                    street_name="da Boavista",
                    locality_id=l_porto.id,  # type: ignore[arg-type]
                ),
            ]
        )
        await s.commit()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession], seed: None
) -> AsyncGenerator[AsyncClient, None]:
    """ASGI client with get_session overridden to hit the test DB."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
