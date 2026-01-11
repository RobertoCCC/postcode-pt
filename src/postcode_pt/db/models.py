from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel


class District(SQLModel, table=True):
    __tablename__ = "districts"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=2)
    name: str = Field(index=True, max_length=64)

    municipalities: list["Municipality"] = Relationship(back_populates="district")


class Municipality(SQLModel, table=True):
    __tablename__ = "municipalities"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=4)
    name: str = Field(index=True, max_length=128)
    district_id: int = Field(foreign_key="districts.id", index=True)

    district: District = Relationship(back_populates="municipalities")
    localities: list["Locality"] = Relationship(back_populates="municipality")


class Locality(SQLModel, table=True):
    __tablename__ = "localities"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, max_length=16)
    name: str = Field(index=True, max_length=128)
    municipality_id: int = Field(foreign_key="municipalities.id", index=True)

    municipality: Municipality = Relationship(back_populates="localities")
    postal_codes: list["PostalCode"] = Relationship(back_populates="locality")


class PostalCode(SQLModel, table=True):
    __tablename__ = "postal_codes"
    __table_args__ = (
        Index("ix_postal_codes_cp4_cp3", "cp4", "cp3"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cp4: str = Field(max_length=4)
    cp3: str = Field(max_length=3)
    designation: str = Field(max_length=128)

    street_type: str | None = Field(default=None, max_length=32)
    street_name: str | None = Field(default=None, max_length=128)
    door_from: str | None = Field(default=None, max_length=16)
    door_to: str | None = Field(default=None, max_length=16)

    locality_id: int = Field(foreign_key="localities.id", index=True)
    locality: Locality = Relationship(back_populates="postal_codes")
