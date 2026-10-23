"""Calculation endpoints for rate lookup and demand surcharge."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tariff import (
    CurrentRateResponse,
    DemandSurchargeResponse,
    DemandWindow,
    DemandWindowsResponse,
    ErrorResponse,
)
from app.services.rate_calculator import (
    calculate_demand_surcharge,
    demand_windows,
    get_current_rate,
    is_in_demand_window,
)
from app.services.tariff_service import get_tariff_detail

router = APIRouter(prefix="/api/v1/calculate", tags=["Calculate"])

OUT_OF_RANGE = "Datetime is outside the supported date range"


def _errors(bad_request: str) -> dict:
    """OpenAPI entries for a calculate route's 400 and 404 responses."""
    return {
        400: {"model": ErrorResponse, "description": bad_request},
        404: {"model": ErrorResponse, "description": "Tariff not found for the DNSP"},
    }


@router.get(
    "/current-rate",
    response_model=CurrentRateResponse,
    responses=_errors("Invalid datetime, or outside the supported date range"),
)
def current_rate(
    dnsp: str = Query(
        ..., description="DNSP code, e.g. 'energex'",
        json_schema_extra={"example": "energex"},
    ),
    tariff: str = Query(
        ..., description="Tariff code, e.g. '3900'",
        json_schema_extra={"example": "3900"},
    ),
    dt: str = Query(
        ...,
        alias="datetime",
        description=(
            "ISO 8601 datetime, e.g. '2026-07-20T17:30:00+10:00'. Resolved in the "
            "DNSP's local time; a value without an offset is taken as that local time."
        ),
        json_schema_extra={"example": "2026-07-20T17:30:00+10:00"},
    ),
    db: Session = Depends(get_db),
) -> CurrentRateResponse:
    """Get the active rate for a given DNSP, tariff, and datetime."""
    tariff_obj = get_tariff_detail(db, dnsp, tariff)
    if not tariff_obj:
        raise HTTPException(
            status_code=404, detail=f"Tariff '{tariff}' not found for DNSP '{dnsp}'"
        )

    try:
        parsed_dt = datetime.fromisoformat(dt.replace(" ", "+"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400, detail=f"Invalid datetime format: '{dt}'. Use ISO 8601."
        )
    if parsed_dt.tzinfo is not None:
        # Resolve in the DNSP's local time; a naive datetime already is (#39).
        try:
            parsed_dt = parsed_dt.astimezone(ZoneInfo(tariff_obj.dnsp.timezone))
        except OverflowError:
            raise HTTPException(status_code=400, detail=OUT_OF_RANGE)
    period_name, rate = get_current_rate(tariff_obj, parsed_dt)
    in_window = is_in_demand_window(tariff_obj.demand, parsed_dt)

    return CurrentRateResponse(
        dnsp=dnsp,
        tariff=tariff,
        datetime=dt,
        period=period_name,
        rate=rate,
        in_demand_window=in_window,
    )


@router.get(
    "/demand-surcharge",
    response_model=DemandSurchargeResponse,
    responses=_errors("The tariff has no demand charge"),
)
def demand_surcharge(
    dnsp: str = Query(
        ..., description="DNSP code",
        json_schema_extra={"example": "energex"},
    ),
    tariff: str = Query(
        ..., description="Tariff code",
        json_schema_extra={"example": "3900"},
    ),
    peak_demand_kw: float = Query(
        ..., description="Peak demand in kW",
        json_schema_extra={"example": 4.5},
    ),
    db: Session = Depends(get_db),
) -> DemandSurchargeResponse:
    """Calculate demand surcharge for given peak demand."""
    tariff_obj = get_tariff_detail(db, dnsp, tariff)
    if not tariff_obj:
        raise HTTPException(
            status_code=404, detail=f"Tariff '{tariff}' not found for DNSP '{dnsp}'"
        )

    if not tariff_obj.demand:
        raise HTTPException(
            status_code=400,
            detail=f"Tariff '{tariff}' does not have a demand charge component",
        )

    surcharge, monthly_charge, window_hours = calculate_demand_surcharge(
        tariff_obj.demand, peak_demand_kw
    )

    return DemandSurchargeResponse(
        dnsp=dnsp,
        tariff=tariff,
        peak_demand_kw=peak_demand_kw,
        demand_rate=tariff_obj.demand.rate,
        demand_window_hours_per_month=window_hours,
        surcharge_per_kwh=round(surcharge, 5),
        monthly_demand_charge=round(monthly_charge, 2),
    )


MAX_DEMAND_WINDOW_RANGE = timedelta(days=31)


def _parse_aware(name: str, value: str) -> datetime:
    """Parse an ISO 8601 query value that must carry a UTC offset; 400 otherwise."""
    try:
        parsed = datetime.fromisoformat(value.replace(" ", "+"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400, detail=f"Invalid {name}: '{value}'. Use ISO 8601."
        )
    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail=f"{name} '{value}' has no UTC offset. Use ISO 8601 with an offset.",
        )
    return parsed


@router.get(
    "/demand-windows",
    response_model=DemandWindowsResponse,
    responses=_errors(
        "Invalid or naive datetime, end not after start, range over 31 days, "
        "or outside the supported date range"
    ),
)
def demand_windows_in_range(
    dnsp: str = Query(
        ..., description="DNSP code",
        json_schema_extra={"example": "energex"},
    ),
    tariff: str = Query(
        ..., description="Tariff code",
        json_schema_extra={"example": "3800"},
    ),
    start: str = Query(
        ..., description="Range start, ISO 8601 with an offset",
        json_schema_extra={"example": "2026-10-23T00:00:00+10:00"},
    ),
    end: str = Query(
        ..., description="Range end, ISO 8601 with an offset; after start, at most 31 days on",
        json_schema_extra={"example": "2026-10-30T00:00:00+10:00"},
    ),
    db: Session = Depends(get_db),
) -> DemandWindowsResponse:
    """Demand windows of a tariff over [start, end), at most 31 days.

    Windows are resolved in the DNSP's local time by the rules of
    `/calculate/current-rate`'s `in_demand_window`: half-open, clipped to the
    range, sorted and merged, each bound in the DNSP's local offset.
    """
    tariff_obj = get_tariff_detail(db, dnsp, tariff)
    if not tariff_obj:
        raise HTTPException(
            status_code=404, detail=f"Tariff '{tariff}' not found for DNSP '{dnsp}'"
        )

    range_start = _parse_aware("start", start)
    range_end = _parse_aware("end", end)
    if range_end <= range_start:
        raise HTTPException(status_code=400, detail="end must be after start")
    if range_end - range_start > MAX_DEMAND_WINDOW_RANGE:
        raise HTTPException(
            status_code=400, detail="Range from start to end must be at most 31 days"
        )

    tz = ZoneInfo(tariff_obj.dnsp.timezone)
    try:
        spans = demand_windows(tariff_obj.demand, tz, range_start, range_end)
    except OverflowError:
        raise HTTPException(status_code=400, detail=OUT_OF_RANGE)
    return DemandWindowsResponse(
        dnsp=dnsp,
        tariff=tariff,
        start=start,
        end=end,
        windows=[DemandWindow(start=s.isoformat(), end=e.isoformat()) for s, e in spans],
    )
