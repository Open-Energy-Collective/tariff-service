"""DNSP listing endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tariff import DnspResponse
from app.services.tariff_service import get_all_dnsps

router = APIRouter(prefix="/api/v1", tags=["DNSPs"])


@router.get("/dnsps", response_model=list[DnspResponse])
def list_dnsps(db: Session = Depends(get_db)) -> list[DnspResponse]:
    """List all Australian DNSPs with tariff count."""
    dnsps = get_all_dnsps(db)
    return [
        DnspResponse(
            code=d.code,
            name=d.name,
            state=d.state,
            timezone=d.timezone,
            tariff_count=len(d.tariffs),
        )
        for d in dnsps
    ]
