from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from postcode_pt.db.models import District, Municipality
from postcode_pt.models.responses import (
    DistrictBrief,
    MunicipalityBrief,
    MunicipalityWithDistrict,
)


async def list_all(session: AsyncSession) -> list[DistrictBrief]:
    stmt = select(District).order_by(District.code)
    result = await session.execute(stmt)
    return [DistrictBrief(code=d.code, name=d.name) for d in result.scalars().all()]


async def get_by_code(session: AsyncSession, code: str) -> District | None:
    stmt = select(District).where(District.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_municipalities(
    session: AsyncSession, district_code: str
) -> list[MunicipalityWithDistrict] | None:
    """Returns None if the district code is unknown."""
    district = await get_by_code(session, district_code)
    if district is None:
        return None

    stmt = (
        select(Municipality)
        .options(selectinload(Municipality.district))
        .where(Municipality.district_id == district.id)
        .order_by(Municipality.name)
    )
    result = await session.execute(stmt)
    return [
        MunicipalityWithDistrict(
            code=m.code,
            name=m.name,
            district=DistrictBrief(code=m.district.code, name=m.district.name),
        )
        for m in result.scalars().all()
    ]
