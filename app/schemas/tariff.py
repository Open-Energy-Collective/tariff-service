"""Pydantic schemas for API request/response serialization."""

from pydantic import BaseModel, Field


class DnspResponse(BaseModel):
    code: str = Field(description="Unique DNSP identifier, e.g. 'energex', 'ausgrid'")
    name: str = Field(description="Full DNSP name, e.g. 'Energex', 'Ausgrid'")
    state: str = Field(description="Australian state abbreviation, e.g. 'QLD', 'NSW'")
    timezone: str = Field(
        description="IANA timezone for the DNSP's service area, e.g. 'Australia/Brisbane'"
    )
    tariff_count: int = Field(description="Number of active tariffs for this DNSP")

    model_config = {"from_attributes": True}


class TariffDemandResponse(BaseModel):
    rate: float = Field(
        description=(
            "Demand charge rate in $/kW/month. This is the monthly cost per kW "
            "of peak demand measured during the demand window."
        )
    )
    window_start: str = Field(
        description="Start of the demand measurement window (HH:MM, local time)"
    )
    window_end: str = Field(
        description="End of the demand measurement window (HH:MM, local time)"
    )
    measurement_method: str = Field(
        description=(
            "How peak demand is measured within the window. Values: "
            "'30min_avg' = average demand over the highest 30-minute interval "
            "(used by Energex); "
            "'30min_max' = maximum demand in any 30-minute interval "
            "(used by Ausgrid). "
            "The measured value (in kW) is multiplied by the rate to produce "
            "the monthly demand charge."
        )
    )
    days: str = Field(
        description=(
            "Which days the demand window applies. Values: "
            "'all' = every day including weekends; "
            "'weekdays' = Monday to Friday only (excludes public holidays)"
        )
    )
    season_months: list[int] | None = Field(
        default=None,
        description=(
            "Months (1-12) when demand charges apply. "
            "null = all months (year-round). "
            "e.g. [1,2,3,6,7,8,11,12] = high season only (Ausgrid). "
            "Outside these months, no demand charge is levied."
        ),
    )

    model_config = {"from_attributes": True}


class TariffRateResponse(BaseModel):
    period: str = Field(
        description=(
            "Rate period name. Common values: 'peak', 'off_peak', 'shoulder', "
            "'anytime' (flat tariffs). Determines when this rate applies."
        )
    )
    rate: float = Field(description="Energy rate in $/kWh (excluding GST)")
    start_time: str = Field(
        description=(
            "Start of the time window (HH:MM, local time). "
            "'00:00' with end_time '00:00' means applies at all times."
        )
    )
    end_time: str = Field(
        description=(
            "End of the time window (HH:MM, local time). "
            "'00:00' with start_time '00:00' means applies at all times."
        )
    )
    days: str = Field(
        description="Days this rate applies: 'all', 'weekdays', or 'weekends'"
    )
    season: str = Field(
        description=(
            "Season label: 'all' = year-round, 'high' = peak season only. "
            "When 'high', see season_months for which months apply."
        )
    )
    season_months: list[int] | None = Field(
        default=None,
        description=(
            "Months (1-12) when this rate applies. "
            "null = all months. Used with seasonal tariffs like Ausgrid "
            "where peak rates only apply Jun-Aug & Nov-Mar."
        ),
    )

    model_config = {"from_attributes": True}


class TariffExportResponse(BaseModel):
    credit_rate: float | None = Field(
        default=None, description="Export credit rate in $/kWh (paid to customer)"
    )
    credit_window_start: str | None = Field(
        default=None, description="Start of export credit window (HH:MM)"
    )
    credit_window_end: str | None = Field(
        default=None, description="End of export credit window (HH:MM)"
    )
    credit_season_months: list[int] | None = Field(
        default=None, description="Months when export credits apply"
    )
    charge_rate: float | None = Field(
        default=None,
        description="Export charge rate in $/kWh (charged to customer for exporting)",
    )
    charge_window_start: str | None = Field(
        default=None, description="Start of export charge window (HH:MM)"
    )
    charge_window_end: str | None = Field(
        default=None, description="End of export charge window (HH:MM)"
    )
    free_threshold_kwh: float | None = Field(
        default=None, description="Export threshold below which no charge applies"
    )
    days: str = Field(description="Days this export pricing applies")

    model_config = {"from_attributes": True}


class TariffSummaryResponse(BaseModel):
    code: str = Field(description="Network Tariff Code (NTC)")
    name: str = Field(description="Human-readable tariff name")
    tariff_type: str = Field(
        description=(
            "Tariff structure type: 'flat', 'tou' (time-of-use), "
            "'tou_demand' (time-of-use + demand), 'demand', "
            "'controlled_load', 'tou_export' (two-way/solar)"
        )
    )
    effective_from: str = Field(description="Date tariff became effective (YYYY-MM-DD)")
    effective_to: str | None = Field(
        default=None, description="Date tariff expires (null = currently active)"
    )

    model_config = {"from_attributes": True}


class TariffDetailResponse(BaseModel):
    dnsp: str = Field(description="DNSP code this tariff belongs to")
    code: str = Field(description="Network Tariff Code (NTC)")
    name: str = Field(description="Human-readable tariff name")
    tariff_type: str = Field(
        description=(
            "Tariff structure type: 'flat', 'tou', 'tou_demand', "
            "'demand', 'controlled_load', 'tou_export'"
        )
    )
    effective_from: str = Field(description="Date tariff became effective (YYYY-MM-DD)")
    effective_to: str | None = Field(
        default=None, description="Date tariff expires (null = currently active)"
    )
    daily_supply_charge: float | None = Field(
        default=None,
        description="Fixed daily network access charge in $/day (excluding GST)",
    )
    demand: TariffDemandResponse | None = Field(
        default=None,
        description=(
            "Demand charge component. Present only for tariff types "
            "'tou_demand' and 'demand'. See /api/v1/docs/demand-methodology "
            "for per-DNSP calculation details."
        ),
    )
    rates: list[TariffRateResponse] = Field(
        description="Energy consumption rates ($/kWh) by time period"
    )
    export: list[TariffExportResponse] = Field(
        description="Solar/battery export pricing (empty if not a two-way tariff)"
    )
    source_url: str | None = Field(
        default=None,
        description="URL of the official DNSP price list this data was sourced from",
    )
    last_verified: str | None = Field(
        default=None,
        description="ISO 8601 datetime when this data was last verified against source",
    )

    model_config = {"from_attributes": True}


class CurrentRateRequest(BaseModel):
    dnsp: str
    tariff: str
    datetime: str  # ISO 8601


class CurrentRateResponse(BaseModel):
    dnsp: str = Field(description="DNSP code")
    tariff: str = Field(description="Tariff code")
    datetime: str = Field(description="The datetime used for calculation")
    period: str = Field(
        description="Active rate period at this time: 'peak', 'off_peak', 'shoulder', 'anytime'"
    )
    rate: float = Field(description="Energy rate in $/kWh for this period")
    in_demand_window: bool = Field(
        description=(
            "Whether the given datetime falls within the demand measurement window. "
            "If true, consumption at this time contributes to the monthly peak demand "
            "calculation (which determines the demand charge). "
            "Only relevant for 'tou_demand' and 'demand' tariff types."
        )
    )
    unit: str = Field(default="$/kWh", description="Unit for the rate field")


class DemandSurchargeRequest(BaseModel):
    dnsp: str
    tariff: str
    peak_demand_kw: float


class DemandSurchargeResponse(BaseModel):
    dnsp: str = Field(description="DNSP code")
    tariff: str = Field(description="Tariff code")
    peak_demand_kw: float = Field(
        description="The peak demand value (kW) used for calculation"
    )
    demand_rate: float = Field(description="Demand charge rate in $/kW/month")
    demand_window_hours_per_month: float = Field(
        description=(
            "Total hours per month the demand window is active. "
            "Used to amortize the demand charge into a per-kWh surcharge."
        )
    )
    surcharge_per_kwh: float = Field(
        description=(
            "Demand charge amortized as $/kWh. Calculated as: "
            "monthly_demand_charge / (peak_demand_kw × demand_window_hours_per_month). "
            "Useful for comparing demand cost impact against energy rates."
        )
    )
    monthly_demand_charge: float = Field(
        description=(
            "Total monthly demand charge in $. "
            "Calculated as: peak_demand_kw × demand_rate"
        )
    )
    unit: str = Field(default="$/kWh", description="Unit for surcharge_per_kwh")
