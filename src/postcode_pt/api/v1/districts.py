from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from postcode_pt.db.session import get_session
from postcode_pt.models.responses import DistrictBrief, MunicipalityWithDistrict
from postcode_pt.services import districts as districts_service

router = APIRouter(prefix="/districts", tags=["districts"])

DistrictCode = Annotated[
    str, Path(pattern=r"^\d{2}$", description="2-digit district code", examples=["11"])
]


@router.get(
    "",
    response_model=list[DistrictBrief],
    summary="List all districts",
)
async def list_districts(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[DistrictBrief]:
    """Return the 29 Portuguese districts (18 mainland + 11 islands)."""
    return await districts_service.list_all(session)


@router.get(
    "/{code}/municipalities",
    response_model=list[MunicipalityWithDistrict],
    summary="List municipalities in a district",
    responses={404: {"description": "District not found"}},
)
async def list_municipalities(
    code: DistrictCode,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[MunicipalityWithDistrict]:
    municipalities = await districts_service.list_municipalities(session, code)
    if municipalities is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District {code} not found",
        )
    return municipalities
