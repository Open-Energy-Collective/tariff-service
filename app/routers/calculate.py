"""Calculation endpoints for rate lookup and demand surcharge."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tariff import CurrentRateResponse, DemandSurchargeResponse
from app.services.rate_calculator import (
    calculate_demand_surcharge,
    get_current_rate,
    is_in_demand_window,
)
from app.services.tariff_service import get_tariff_detail

router = APIRouter(prefix="/api/v1/calculate", tags=["Calculate"])


@router.get("/current-rate", response_model=CurrentRateResponse)
def current_rate(
    dnsp: str = Query(..., description="DNSP code, e.g. 'energex'"),
    tariff: str = Query(..., description="Tariff code, e.g. 'T12A'"),
    dt: str = Query(
        ..., alias="datetime", description="ISO 8601 datetime, e.g. '2026-07-20T17:30:00+10:00'"
    ),
    db: Session = Depends(get_db),
) -> CurrentRateResponse:
    """Get the active rate for a given DNSP, tariff, and datetime."""
    tariff_obj = get_tariff_detail(db, dnsp, tariff)
    if not tariff_obj:
        raise HTTPException(status_code=404, detail=f"Tariff '{tariff}' not found for DNSP '{dnsp}'")

    parsed_dt = datetime.fromisoformat(dt)
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


@router.get("/demand-surcharge", response_model=DemandSurchargeResponse)
def demand_surcharge(
    dnsp: str = Query(..., description="DNSP code"),
    tariff: str = Query(..., description="Tariff code"),
    peak_demand_kw: float = Query(..., description="Peak demand in kW"),
    db: Session = Depends(get_db),
) -> DemandSurchargeResponse:
    """Calculate demand surcharge for given peak demand."""
    tariff_obj = get_tariff_detail(db, dnsp, tariff)
    if not tariff_obj:
        raise HTTPException(status_code=404, detail=f"Tariff '{tariff}' not found for DNSP '{dnsp}'")

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
