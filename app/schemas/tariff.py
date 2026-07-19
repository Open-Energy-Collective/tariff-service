"""Pydantic schemas for API request/response serialization."""

from pydantic import BaseModel


class DnspResponse(BaseModel):
    code: str
    name: str
    state: str
    timezone: str
    tariff_count: int

    model_config = {"from_attributes": True}


class TariffDemandResponse(BaseModel):
    rate: float
    window_start: str
    window_end: str
    measurement_method: str
    days: str
    season_months: list[int] | None = None

    model_config = {"from_attributes": True}


class TariffRateResponse(BaseModel):
    period: str
    rate: float
    start_time: str
    end_time: str
    days: str
    season: str
    season_months: list[int] | None = None

    model_config = {"from_attributes": True}


class TariffExportResponse(BaseModel):
    credit_rate: float | None = None
    credit_window_start: str | None = None
    credit_window_end: str | None = None
    credit_season_months: list[int] | None = None
    charge_rate: float | None = None
    charge_window_start: str | None = None
    charge_window_end: str | None = None
    free_threshold_kwh: float | None = None
    days: str

    model_config = {"from_attributes": True}


class TariffSummaryResponse(BaseModel):
    code: str
    name: str
    tariff_type: str
    effective_from: str
    effective_to: str | None = None

    model_config = {"from_attributes": True}


class TariffDetailResponse(BaseModel):
    dnsp: str
    code: str
    name: str
    tariff_type: str
    effective_from: str
    effective_to: str | None = None
    daily_supply_charge: float | None = None
    demand: TariffDemandResponse | None = None
    rates: list[TariffRateResponse]
    export: list[TariffExportResponse]
    source_url: str | None = None
    last_verified: str | None = None

    model_config = {"from_attributes": True}


class CurrentRateRequest(BaseModel):
    dnsp: str
    tariff: str
    datetime: str  # ISO 8601


class CurrentRateResponse(BaseModel):
    dnsp: str
    tariff: str
    datetime: str
    period: str
    rate: float
    in_demand_window: bool
    unit: str = "$/kWh"


class DemandSurchargeRequest(BaseModel):
    dnsp: str
    tariff: str
    peak_demand_kw: float


class DemandSurchargeResponse(BaseModel):
    dnsp: str
    tariff: str
    peak_demand_kw: float
    demand_rate: float
    demand_window_hours_per_month: float
    surcharge_per_kwh: float
    monthly_demand_charge: float
    unit: str = "$/kWh"
