"""OEC Tariff Data Service — FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import RATE_LIMIT_PER_MINUTE
from app.middleware import limiter
from app.routers import calculate, dnsps, docs, tariffs

_VERSION = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()

app = FastAPI(
    title="Tariff Data Service",
    description=(
        "Public REST API serving curated Australian DNSP network tariff data — "
        "time-of-use rates, demand charges, and export tariffs sourced from "
        "official AER-approved Network Price Lists. Free and unauthenticated. "
        "Part of the Open Energy Collective platform.\n\n"
        "### Rate limiting\n"
        f"Requests are limited to **{RATE_LIMIT_PER_MINUTE} per minute, per IP "
        "address**, enforced across all endpoints. Exceeding the limit returns "
        "`429 Too Many Requests` with a `Retry-After` header indicating how "
        "many seconds to wait before retrying."
    ),
    version=_VERSION,
    contact={
        "name": "Open Energy Collective",
        "url": "https://openenergy.org.au",
        "email": "info@openenergy.org.au",
    },
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
