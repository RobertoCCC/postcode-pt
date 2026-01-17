from fastapi import FastAPI

from postcode_pt.api.v1.router import router as v1_router
from postcode_pt.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Public REST API for Portuguese postal codes (CP4-CP3): "
    "lookup localities, municipalities and districts.",
    version=settings.app_version,
)

app.include_router(v1_router)
