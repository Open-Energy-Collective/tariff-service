"""OEC Tariff Data Service — FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import calculate, dnsps, docs, tariffs

_VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()

app = FastAPI(
    title="OEC Tariff Data Service",
    description=(
        "Public REST API serving curated Australian DNSP tariff data. "
        "Free, unauthenticated, rate-limited. "
        "Part of the Open Energy Collective platform."
    ),
    version=_VERSION,
    contact={
        "name": "Open Energy Collective",
        "url": "https://openenergy.org.au",
        "email": "andre.zitelli@outlook.com",
    },
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(dnsps.router)
app.include_router(tariffs.router)
app.include_router(calculate.router)
app.include_router(docs.router)


@app.get("/api/v1/health", tags=["Health"])
def health() -> dict[str, str]:
    """Service health check."""
    return {"status": "ok", "service": "oec-tariff-service", "version": _VERSION}
