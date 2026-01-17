from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from postcode_pt.db.session import get_session
from postcode_pt.models.responses import PostalCodeEntry
from postcode_pt.services import postal_codes as postal_codes_service

router = APIRouter(prefix="/postal-codes", tags=["postal codes"])

Cp4 = Annotated[str, Path(pattern=r"^\d{4}$", description="4-digit prefix", examples=["1100"])]
Cp3 = Annotated[str, Path(pattern=r"^\d{3}$", description="3-digit suffix", examples=["038"])]


@router.get(
    "/{cp4}-{cp3}",
    response_model=list[PostalCodeEntry],
    summary="Look up a postal code",
    responses={
        404: {"description": "Postal code not found"},
        422: {"description": "Invalid CP4 or CP3 format"},
    },
)
async def get_postal_code(
    cp4: Cp4,
    cp3: Cp3,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PostalCodeEntry]:
    """Return all postal-code entries matching `CP4-CP3`.

    The same code may have multiple entries (different street segments or
    CTT customer records) — the response is always a list.
    """
    entries = await postal_codes_service.find_by_cp4_cp3(session, cp4, cp3)
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Postal code {cp4}-{cp3} not found",
        )
    return entries
