from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from postcode_pt.db.models import Locality, Municipality, PostalCode
from postcode_pt.models.responses import (
    DistrictBrief,
    LocalityBrief,
    MunicipalityBrief,
    PostalCodeEntry,
    Street,
)


async def find_by_cp4_cp3(
    session: AsyncSession, cp4: str, cp3: str
) -> list[PostalCodeEntry]:
    """Look up postal codes matching cp4-cp3, eagerly loading the full hierarchy."""
    stmt = (
        select(PostalCode)
        .options(
            selectinload(PostalCode.locality)
            .selectinload(Locality.municipality)
            .selectinload(Municipality.district)
        )
        .where(PostalCode.cp4 == cp4, PostalCode.cp3 == cp3)
        .order_by(PostalCode.id)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_to_entry(row) for row in rows]


def _to_entry(pc: PostalCode) -> PostalCodeEntry:
    """Map ORM PostalCode → API PostalCodeEntry."""
    locality = pc.locality
    municipality = locality.municipality
    district = municipality.district
    return PostalCodeEntry(
        code=f"{pc.cp4}-{pc.cp3}",
        designation=pc.designation,
        street=Street(type=pc.street_type, name=pc.street_name),
        locality=LocalityBrief(code=locality.code, name=locality.name),
        municipality=MunicipalityBrief(code=municipality.code, name=municipality.name),
        district=DistrictBrief(code=district.code, name=district.name),
    )
