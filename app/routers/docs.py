"""Documentation endpoints for tariff methodology explanations."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tariff import Dnsp, Tariff, TariffDemand

router = APIRouter(prefix="/api/v1/docs", tags=["Documentation"])


class DnspDemandMethodology(BaseModel):
    dnsp_code: str = Field(description="DNSP code")
    dnsp_name: str = Field(description="DNSP name")
    has_demand_tariffs: bool = Field(description="Whether this DNSP offers demand tariffs")
    measurement_method: str | None = Field(
        default=None, description="How peak demand is measured"
    )
    measurement_explanation: str | None = Field(
        default=None, description="Plain-English explanation of the measurement method"
    )
    window: str | None = Field(
        default=None, description="Demand window times (local time)"
    )
    days: str | None = Field(
        default=None, description="Which days the demand window applies"
    )
    seasonal_applicability: str | None = Field(
        default=None, description="When demand charges apply across the year"
    )
    rate_unit: str = Field(
        default="$/kW/month", description="Unit for the demand rate"
    )
    calculation_example: str | None = Field(
        default=None, description="Worked example of how the demand charge is calculated"
    )
    source_url: str | None = Field(
        default=None, description="Link to official DNSP pricing documentation"
    )


class DemandMethodologyResponse(BaseModel):
    title: str = Field(description="Document title")
    description: str = Field(description="Overview of demand charges")
    dnsps: list[DnspDemandMethodology] = Field(
        description="Per-DNSP demand methodology details"
    )


MEASUREMENT_EXPLANATIONS = {
    "30min_avg": (
        "The average power draw (kW) over the highest 30-minute interval within "
        "the demand window during the billing month. Your meter records consumption "
        "in 30-minute blocks; the block with the highest average is your peak demand "
        "for that month."
    ),
    "30min_max": (
        "The maximum power draw (kW) recorded in any 30-minute interval within "
        "the demand window during the billing month. This is typically the single "
        "highest 30-minute reading your meter records during peak hours."
    ),
}

SEASON_EXPLANATIONS = {
    None: "Year-round — demand charges apply every month.",
    "[1, 2, 3, 6, 7, 8, 11, 12]": (
        "High season only — demand charges apply in summer (Nov-Mar) and winter "
        "(Jun-Aug). No demand charges in the shoulder months of April, May, "
        "September, and October."
    ),
}

CALCULATION_EXAMPLES = {
    "energex": (
        "Example (Energex NTC 3900, Residential ToU Demand & Energy):\n"
        "• Your highest 30-min average demand this month was 4.5 kW\n"
        "• Demand rate: $7.00/kW/month\n"
        "• Monthly demand charge: 4.5 kW × $7.00 = $31.50\n"
        "• This is in addition to your energy charges ($/kWh) and daily supply charge"
    ),
    "ausgrid": (
        "Example (Ausgrid EA116, Residential Demand):\n"
        "• Your highest 30-min demand this month (3pm-9pm, high season) was 5.2 kW\n"
        "• Demand rate: $11.85/kW/month\n"
        "• Monthly demand charge: 5.2 kW × $11.85 = $61.59\n"
        "• Outside high season (Apr/May/Sep/Oct), no demand charge applies\n"
        "• This is in addition to your energy charges ($/kWh) and daily supply charge"
    ),
}


@router.get("/demand-methodology", response_model=DemandMethodologyResponse)
def demand_methodology(db: Session = Depends(get_db)) -> DemandMethodologyResponse:
    """Explains how demand charges are calculated for each DNSP.

    Demand charges vary significantly between DNSPs in their measurement method,
    time windows, applicable days, and seasonal applicability. This endpoint
    provides a human-readable explanation of each DNSP's methodology to help
    API consumers correctly interpret and use demand tariff data.
    """
    dnsps = db.query(Dnsp).order_by(Dnsp.name).all()
    dnsp_methods = []

    for dnsp in dnsps:
        # Find a representative demand tariff for this DNSP
        demand_tariff = (
            db.query(Tariff)
            .join(TariffDemand)
            .filter(Tariff.dnsp_id == dnsp.id)
            .first()
        )

        if not demand_tariff or not demand_tariff.demand:
            dnsp_methods.append(
                DnspDemandMethodology(
                    dnsp_code=dnsp.code,
                    dnsp_name=dnsp.name,
                    has_demand_tariffs=False,
                )
            )
            continue

        demand = demand_tariff.demand
        season_key = demand.season_months if demand.season_months else None

        dnsp_methods.append(
            DnspDemandMethodology(
                dnsp_code=dnsp.code,
                dnsp_name=dnsp.name,
                has_demand_tariffs=True,
                measurement_method=demand.measurement_method,
                measurement_explanation=MEASUREMENT_EXPLANATIONS.get(
                    demand.measurement_method
                ),
                window=f"{demand.window_start} to {demand.window_end} (local time)",
                days=(
                    "All days (including weekends)"
                    if demand.days == "all"
                    else "Weekdays only (Monday to Friday)"
                ),
                seasonal_applicability=SEASON_EXPLANATIONS.get(
                    season_key,
                    f"Applies in months: {season_key}",
                ),
                rate_unit="$/kW/month",
                calculation_example=CALCULATION_EXAMPLES.get(dnsp.code),
                source_url=demand_tariff.source_url,
            )
        )

    return DemandMethodologyResponse(
        title="Demand Charge Methodology by DNSP",
        description=(
            "Demand charges are a component of certain network tariffs that charge "
            "customers based on their peak electricity demand (measured in kW) during "
            "specified time windows. Unlike energy charges ($/kWh) which are based on "
            "total consumption, demand charges incentivise reducing peak usage — "
            "the single highest draw during the billing period determines the charge. "
            "This means running multiple high-power appliances simultaneously during "
            "peak hours costs more than spreading usage throughout the day."
        ),
        dnsps=dnsp_methods,
    )
