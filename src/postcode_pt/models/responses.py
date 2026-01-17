"""Pydantic models for API responses.

Keep these separate from the SQLModel ORM classes — DB shape and API shape
should evolve independently.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DistrictBrief(BaseModel):
    code: str = Field(examples=["11"], description="2-digit district code")
    name: str = Field(examples=["Lisboa"])


class MunicipalityBrief(BaseModel):
    code: str = Field(examples=["1106"], description="4-digit municipality code")
    name: str = Field(examples=["Lisboa"])


class LocalityBrief(BaseModel):
    code: str = Field(examples=["10123"])
    name: str = Field(examples=["Lisboa"])


class Street(BaseModel):
    type: str | None = Field(default=None, examples=["Rua"])
    name: str | None = Field(default=None, examples=["do Arsenal"])


class PostalCodeEntry(BaseModel):
    """A single postal-code record. The same CP4-CP3 may have multiple entries
    (different street segments, CTT customers, etc) — clients receive a list.
    """

    code: str = Field(examples=["1100-038"], description="CP4-CP3 combined")
    designation: str = Field(examples=["LISBOA"], description="Official postal designation")
    street: Street
    locality: LocalityBrief
    municipality: MunicipalityBrief
    district: DistrictBrief


class MunicipalityWithDistrict(MunicipalityBrief):
    district: DistrictBrief
