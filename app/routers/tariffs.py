"""Tariff query endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tariff import (
    DemandChargeResponse,
    TariffDemandResponse,
    TariffDetailResponse,
    TariffExportResponse,
    TariffRateResponse,
    TariffSummaryResponse,
)
from app.services.rate_calculator import demand_charge_order
from app.services.tariff_service import get_tariff_detail, get_tariff_history, get_tariffs_for_dnsp

router = APIRouter(prefix="/api/v1/tariffs", tags=["Tariffs"])


def _parse_season_months(raw: str | None) -> list[int] | None:
    if raw is None:
        return None
    return json.loads(raw)


def _build_detail_response(tariff) -> TariffDetailResponse:
    """Build a full tariff detail response from ORM object."""
    demand_resp = None
    demand = tariff.demand
    if demand:
        demand_resp = TariffDemandResponse(
            rate=demand.rate,
            window_start=demand.start,
            window_end=demand.end,
            measurement_method=demand.measurement_method,
            days=demand.days,
            season_months=_parse_season_months(demand.months),
        )

    rates_resp = [
        TariffRateResponse(
            period=r.period_name,
            rate=r.rate,
            start_time=r.start_time,
            end_time=r.end_time,
            days=r.days,
            season=r.season,
            season_months=_parse_season_months(r.season_months),
            public_holidays=r.public_holidays,
        )
        for r in tariff.rates
    ]

    export_resp = [
        TariffExportResponse(
            credit_rate=e.credit_rate,
            credit_window_start=e.credit_window_start,
            credit_window_end=e.credit_window_end,
            credit_season_months=_parse_season_months(e.credit_season_months),
            charge_rate=e.charge_rate,
            charge_window_start=e.charge_window_start,
            charge_window_end=e.charge_window_end,
            free_threshold_kwh=e.free_threshold_kwh,
            days=e.days,
            free_threshold_period=e.free_threshold_period,
            free_threshold_rollover=e.free_threshold_rollover,
            public_holidays=e.public_holidays,
        )
        for e in tariff.exports
    ]

    charges_resp = [
        DemandChargeResponse(
            period=c.period,
            rate=c.rate,
            unit=c.unit,
            start=c.start,
            end=c.end,
            days=c.days,
            public_holidays=c.public_holidays,
            months=_parse_season_months(c.months),
            measurement_method=c.measurement_method,
            peak_period=c.peak_period,
        )
        for c in sorted(tariff.demand_charges, key=demand_charge_order)
    ]

    return TariffDetailResponse(
        dnsp=tariff.dnsp.code,
        code=tariff.code,
        name=tariff.name,
        tariff_type=tariff.tariff_type,
        effective_from=tariff.effective_from,
        effective_to=tariff.effective_to,
        daily_supply_charge=tariff.daily_supply_charge,
        demand=demand_resp,
        demand_charges=charges_resp,
        time_basis=tariff.time_basis,
        prices_expected_until=tariff.prices_expected_until,
        rates=rates_resp,
        export=export_resp,
        source_url=tariff.source_url,
        last_verified=tariff.last_verified,
    )


@router.get("/{dnsp_code}", response_model=list[TariffSummaryResponse])
def list_tariffs(
    dnsp_code: str = Path(..., json_schema_extra={"example": "energex"}),
    db: Session = Depends(get_db),
) -> list[TariffSummaryResponse]:
    """List all active tariffs for a DNSP."""
    tariffs = get_tariffs_for_dnsp(db, dnsp_code)
    if not tariffs:
        raise HTTPException(status_code=404, detail=f"No tariffs found for DNSP '{dnsp_code}'")
    return [
        TariffSummaryResponse(
            code=t.code,
            name=t.name,
            tariff_type=t.tariff_type,
            effective_from=t.effective_from,
            effective_to=t.effective_to,
        )
        for t in tariffs
    ]


@router.get("/{dnsp_code}/{tariff_code}", response_model=TariffDetailResponse)
def get_tariff(
    dnsp_code: str = Path(..., json_schema_extra={"example": "energex"}),
    tariff_code: str = Path(..., json_schema_extra={"example": "3900"}),
    db: Session = Depends(get_db),
) -> TariffDetailResponse:
    """Get full tariff detail (current active version)."""
    tariff = get_tariff_detail(db, dnsp_code, tariff_code)
    if not tariff:
        raise HTTPException(
            status_code=404,
            detail=f"Tariff '{tariff_code}' not found for DNSP '{dnsp_code}'",
        )
    return _build_detail_response(tariff)


@router.get("/{dnsp_code}/{tariff_code}/history", response_model=list[TariffDetailResponse])
def get_tariff_versions(
    dnsp_code: str = Path(..., json_schema_extra={"example": "energex"}),
    tariff_code: str = Path(..., json_schema_extra={"example": "3900"}),
    db: Session = Depends(get_db),
) -> list[TariffDetailResponse]:
    """Get all versions of a tariff (newest first)."""
    tariffs = get_tariff_history(db, dnsp_code, tariff_code)
    if not tariffs:
        raise HTTPException(
            status_code=404,
            detail=f"Tariff '{tariff_code}' not found for DNSP '{dnsp_code}'",
        )
    return [_build_detail_response(t) for t in tariffs]
