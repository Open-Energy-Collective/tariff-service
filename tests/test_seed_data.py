"""Seed data checked against the 2026-27 DNSP sources.

Each test loads a tariff straight from seed/*.json (no DB) and runs it through
the rate calculator, so a wrong window or rate in the seed fails here. Sources
are the knowledge entries under OEC/knowledge/documents/<dnsp>/, cited per test.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.models.tariff import Tariff, TariffDemand, TariffRate
from app.services.rate_calculator import get_current_rate, is_in_demand_window

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _months(value: list[int] | None) -> str | None:
    """Store season months as seed/build_db.py does: a JSON array, or None."""
    return json.dumps(value) if value else None


def load_tariff(dnsp_file: str, code: str) -> Tariff:
    """Build an unsaved Tariff with its rates and demand from one seed file."""
    data = json.loads((SEED_DIR / f"{dnsp_file}.json").read_text())
    (tariff_data,) = [t for t in data["tariffs"] if t["code"] == code]
    tariff = Tariff(code=code, name=tariff_data["name"], tariff_type=tariff_data["tariff_type"])
    tariff.rates = [
        TariffRate(
            period_name=r["period_name"],
            rate=r["rate"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            days=r.get("days", "all"),
            season_months=_months(r.get("season_months")),
        )
        for r in tariff_data["rates"]
    ]
    if demand := tariff_data.get("demand"):
        tariff.demand = TariffDemand(
            rate=demand["rate"],
            window_start=demand["window_start"],
            window_end=demand["window_end"],
            measurement_method=demand["measurement_method"],
            days=demand.get("days", "all"),
            season_months=_months(demand.get("season_months")),
        )
    return tariff


def half_hours(day: datetime) -> list[datetime]:
    """The 48 half-hour starts of one local day."""
    return [day + timedelta(minutes=30 * i) for i in range(48)]


# ── SA Power Networks ──
# knowledge/documents/sa-power-networks/2026-10-21-customer-overview-2026-27.md,
# Table 2 (RESELE) and Table 4 (SBELE); rates from Table 9, columns Peak,
# Off-Peak, Shoulder, Solar Sponge. Times are local (ACST/ACDT).

WORKDAY = datetime(2026, 7, 20)  # Monday
NON_WORKDAY = datetime(2026, 7, 25)  # Saturday
SUMMER_WORKDAY = datetime(2027, 1, 13)  # Wednesday


def resele_expected(t: datetime) -> tuple[str, float]:
    """RESELE: peak 5pm-9pm, solar sponge 10am-4pm, shoulder the other 14 hours."""
    if 17 <= t.hour < 21:
        return "peak", 0.3601
    if 10 <= t.hour < 16:
        return "solar_sponge", 0.0321
    return "shoulder", 0.1068


@pytest.mark.parametrize("day", [WORKDAY, NON_WORKDAY, SUMMER_WORKDAY], ids=str)
def test_sapn_resele_every_half_hour(day):
    tariff = load_tariff("sapn", "RESELE")
    for t in half_hours(day):
        assert get_current_rate(tariff, t) == resele_expected(t), t


def test_sapn_resele_has_no_off_peak():
    tariff = load_tariff("sapn", "RESELE")
    assert {r.period_name for r in tariff.rates} == {"peak", "shoulder", "solar_sponge"}


def sbele_expected(t: datetime) -> tuple[str, float]:
    """SBELE: peak 5pm-9pm all days, shoulder 7am-10am and 4pm-5pm workdays,
    off-peak all other times."""
    if 17 <= t.hour < 21:
        return "peak", 0.3636
    if t.weekday() < 5 and (7 <= t.hour < 10 or t.hour == 16):
        return "shoulder", 0.1875
    return "off_peak", 0.1072


@pytest.mark.parametrize("day", [WORKDAY, NON_WORKDAY, SUMMER_WORKDAY], ids=str)
def test_sapn_sbele_every_half_hour(day):
    tariff = load_tariff("sapn", "SBELE")
    for t in half_hours(day):
        assert get_current_rate(tariff, t) == sbele_expected(t), t


# ── Ausgrid ──
# knowledge/documents/ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.md,
# Table 11 note (p. 40): large business capacity charges apply on working
# weekdays (all year); peak energy charges apply in high-season months only.

AUSGRID_CAPACITY = ["EA302", "EA305", "EA310", "EA370", "EA390"]


@pytest.mark.parametrize("code", AUSGRID_CAPACITY)
@pytest.mark.parametrize("month", range(1, 13))
def test_ausgrid_capacity_window_every_month(code, month):
    tariff = load_tariff("ausgrid", code)
    first = datetime(2026, month, 1)
    weekday = first + timedelta(days=(2 - first.weekday()) % 7)  # first Wednesday
    assert is_in_demand_window(tariff.demand, weekday.replace(hour=16))
    assert not is_in_demand_window(tariff.demand, weekday.replace(hour=14))
    saturday = weekday + timedelta(days=3)
    assert not is_in_demand_window(tariff.demand, saturday.replace(hour=16))


@pytest.mark.parametrize("code", AUSGRID_CAPACITY)
def test_ausgrid_capacity_peak_energy_stays_high_season(code):
    tariff = load_tariff("ausgrid", code)
    assert get_current_rate(tariff, datetime(2026, 7, 15, 16))[0] == "peak"
    assert get_current_rate(tariff, datetime(2026, 4, 15, 16))[0] == "off_peak"


# ── Evoenergy ──
# Tariff 023's winter months are not in the 2026-27 schedule of charges; the
# revised TSS 2024-29 defines them as 1 June to 31 August (pp. 7, 15):
# knowledge/documents/evoenergy/2026-10-23-revised-tss-2024-29.md.


@pytest.mark.parametrize("month", range(1, 13))
def test_evoenergy_023_demand_winter_months(month):
    tariff = load_tariff("evoenergy", "023")
    t = datetime(2026, month, 15, 18)
    assert is_in_demand_window(tariff.demand, t) is (month in (6, 7, 8))
