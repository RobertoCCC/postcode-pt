from fastapi import APIRouter

from postcode_pt.api.v1 import districts, postal_codes

router = APIRouter(prefix="/v1")


@router.get("/health", tags=["meta"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(postal_codes.router)
router.include_router(districts.router)
