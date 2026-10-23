"""Demand tariffs against the 2026-27 sources, through the API on the real seed (#22).

Every test here uses the seed_client fixture: the API reads the database that
seed/build_db.py builds from seed/*.json, not the conftest.py fixtures.

1. Source-checked: one demand tariff per seeded DNSP. Each case states the demand
   rate, window, days, season and measurement method as its knowledge entry
   (OEC/knowledge/documents/<dnsp>/) gives them, then checks the seed, one worked
   /calculate/demand-surcharge and two /calculate/current-rate results.
2. Property sweep over every seeded demand tariff: window edges, season edges,
   day type, and surcharge_per_kwh = rate / window hours per month (#33).
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
PEAK_KW = 5.0


def tariff_detail(client, dnsp: str, code: str) -> dict:
    response = client.get(f"/api/v1/tariffs/{dnsp}/{code}")
    assert response.status_code == 200
    return response.json()


def in_window(client, dnsp: str, code: str, at: str) -> bool:
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": dnsp, "tariff": code, "datetime": at},
    )
    assert response.status_code == 200
    return response.json()["in_demand_window"]


def surcharge(client, dnsp: str, code: str, peak_kw: float = PEAK_KW) -> dict:
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": dnsp, "tariff": code, "peak_demand_kw": peak_kw},
    )
    assert response.status_code == 200
    return response.json()


# ── 1. Source-checked ──


@dataclass(frozen=True)
class SourceCase:
    """One demand tariff as its 2026-27 source states it.

    seed_rate is the source rate converted to the seed's $/kW/month (stated in
    conversion). window_hours_per_month counts a weekday window as 5/7 of a
    30-day month. inside and outside are local times for /current-rate; an
    anytime window has no outside, so both are inside.
    """

    dnsp: str
    code: str
    entry: str
    source_rate: str
    conversion: str
    seed_rate: float
    window: tuple[str, str]
    days: str
    season_months: list[int] | None
    method: str
    inside: str
    outside: str
    outside_expected: bool
    window_hours_per_month: float
    surcharge_per_kwh: float
    monthly_charge: float
    schema_gap: str | None = None


SOURCE_CASES = [
    SourceCase(
        dnsp="ausgrid",
        code="EA116",
        entry="ausgrid/2026-10-21-network-price-list-2026-27.md; "
        "ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.md (Table 11)",
        source_rate="39.4850 c/kW/day",
        conversion="x 30 / 100",
        seed_rate=11.8455,
        window=("15:00", "21:00"),
        days="all",
        season_months=[1, 2, 3, 6, 7, 8, 11, 12],
        method="30min_max",
        inside="2027-01-13T16:00:00+11:00",
        outside="2027-01-13T21:00:00+11:00",
        outside_expected=False,
        window_hours_per_month=180.0,
        surcharge_per_kwh=0.06581,
        monthly_charge=59.23,
    ),
    SourceCase(
        dnsp="ausnet",
        code="NASN12",
        entry="ausnet/2026-10-21-network-tariff-schedule-2026-27.md (structure 15)",
        source_rate="11.4725 $/kW/mth peak season (workbook 11.47253)",
        conversion="none; seed rounds to 3 dp",
        seed_rate=11.473,
        window=("15:00", "21:00"),
        days="weekdays",
        season_months=[1, 2, 3, 12],
        method="monthly_peak",
        inside="2027-01-13T15:00:00+11:00",
        outside="2027-01-16T16:00:00+11:00",  # Saturday
        outside_expected=False,
        window_hours_per_month=6 * 30 * 5 / 7,
        surcharge_per_kwh=0.08923,
        monthly_charge=57.37,
        schema_gap="off-peak season rate 2.8622 $/kW/mth (April to November) not held",
    ),
    SourceCase(
        dnsp="endeavour",
        code="N72",
        entry="endeavour-energy/2026-10-21-network-price-list-2026-27.md (s 5.3, 6.1)",
        source_rate="18.18 c/kW/day high season",
        conversion="x 30 / 100",
        seed_rate=5.454,
        window=("16:00", "20:00"),
        days="weekdays",
        season_months=[1, 2, 3, 11, 12],
        method="30min_max",
        inside="2026-11-18T16:00:00+11:00",
        outside="2026-11-18T20:00:00+11:00",
        outside_expected=False,
        window_hours_per_month=4 * 30 * 5 / 7,
        surcharge_per_kwh=0.06363,
        monthly_charge=27.27,
        schema_gap="low season rate 9.27 c/kW/day (April to October) not held",
    ),
    SourceCase(
        dnsp="energex",
        code="3900",
        entry="energex/2026-10-21-network-price-list-2026-27.md; "
        "energex/2026-10-21-network-tariff-guide-2026-27.md",
        source_rate="7 $/kW/month",
        conversion="none",
        seed_rate=7.0,
        window=("16:00", "21:00"),
        days="all",
        season_months=None,
        method="30min_avg",
        inside="2026-07-25T16:00:00+10:00",  # Saturday: weekdays and weekends
        outside="2026-07-25T21:00:00+10:00",
        outside_expected=False,
        window_hours_per_month=150.0,
        surcharge_per_kwh=0.04667,
        monthly_charge=35.0,
    ),
    SourceCase(
        dnsp="essential",
        code="BLND1AR",
        entry="essential-energy/2026-10-21-price-list-explanatory-notes-2026-27.md (p. 6, s 6)",
        source_rate="5.1925 $/kVA/month",
        conversion="none; kVA read as kW",
        seed_rate=5.1925,
        window=("17:00", "20:00"),
        days="weekdays",
        season_months=None,
        method="30min_max",
        inside="2026-07-22T17:00:00+10:00",
        outside="2026-07-22T16:30:00+10:00",
        outside_expected=False,
        window_hours_per_month=3 * 30 * 5 / 7,
        surcharge_per_kwh=0.08077,
        monthly_charge=25.96,
        schema_gap="demand priced per kVA",
    ),
    SourceCase(
        dnsp="evoenergy",
        code="023",
        entry="evoenergy/2026-10-21-schedule-of-charges-2026-27.md; "
        "evoenergy/2026-10-23-revised-tss-2024-29.md (winter months)",
        source_rate="21.808 c/kW/day Seasonal kW Demand (High)",
        conversion="x 30 / 100",
        seed_rate=6.5424,
        window=("17:00", "21:00"),
        days="all",
        season_months=[6, 7, 8],
        method="30min_max",
        inside="2026-07-25T20:30:00+10:00",
        outside="2026-07-25T21:00:00+10:00",
        outside_expected=False,
        window_hours_per_month=120.0,
        surcharge_per_kwh=0.05452,
        monthly_charge=32.71,
        schema_gap="low season 13.083 c/kW/day and off-peak demand 2.076 c/kW/day not held",
    ),
    SourceCase(
        dnsp="jemena",
        code="A230",
        entry="jemena/2026-10-21-network-tariff-schedule-2026-27.md",
        source_rate="77.889 $/kW p.a.",
        conversion="/ 12",
        seed_rate=6.49075,
        window=("00:00", "00:00"),
        days="all",
        season_months=None,
        method="rolling_12month_max",
        inside="2026-07-22T03:00:00+10:00",
        outside="2026-07-25T12:00:00+10:00",  # anytime: still inside
        outside_expected=True,
        window_hours_per_month=720.0,
        surcharge_per_kwh=0.00901,
        monthly_charge=32.45,
        schema_gap="maximum of the last 12 months not computed",
    ),
    SourceCase(
        dnsp="powerwater",
        code="T5",
        entry="power-and-water/2026-10-21-network-tariffs-2026-27.md; per month per "
        "findings/2026-10-21-tariff-service-source-gaps-resolved-2026-27.md",
        source_rate="16.7014 $/kVA On Season",
        conversion="none; read as per month, kVA read as kW",
        seed_rate=16.7014,
        window=("15:00", "21:00"),
        days="weekdays",
        season_months=[1, 2, 3, 10, 11, 12],
        method="30min_max",
        inside="2026-10-14T15:00:00+09:30",
        outside="2026-10-14T21:00:00+09:30",
        outside_expected=False,
        window_hours_per_month=6 * 30 * 5 / 7,
        surcharge_per_kwh=0.1299,
        monthly_charge=83.51,
        schema_gap="kVA; Off Season 3.9297 $/kVA (April to September) not held",
    ),
    SourceCase(
        dnsp="sapn",
        code="MBTOUD",
        entry="sa-power-networks/2026-10-21-customer-overview-2026-27.md (Table 4, Table 9)",
        source_rate="0.0861 $/kVA/day",
        conversion="x 30; kVA read as kW",
        seed_rate=2.583,
        window=("00:00", "00:00"),
        days="all",
        season_months=None,
        method="30min_max",
        inside="2026-07-20T03:00:00+09:30",
        outside="2026-07-25T12:00:00+09:30",  # anytime: still inside
        outside_expected=True,
        window_hours_per_month=720.0,
        surcharge_per_kwh=0.00359,
        monthly_charge=12.92,
        schema_gap="kVA; highest interval of the last 12 months not computed",
    ),
]


def test_source_cases_cover_every_dnsp_with_a_demand_tariff():
    with_demand = {
        tariff["dnsp"]
        for f in SEED_DIR.glob("*.json")
        for tariff in json.loads(f.read_text())["tariffs"]
        if tariff.get("demand")
    }
    assert {case.dnsp for case in SOURCE_CASES} == with_demand


@pytest.mark.parametrize("case", SOURCE_CASES, ids=lambda c: f"{c.dnsp}-{c.code}")
def test_demand_tariff_matches_source(seed_client, case):
    demand = tariff_detail(seed_client, case.dnsp, case.code)["demand"]
    assert demand["rate"] == pytest.approx(case.seed_rate)
    assert (demand["window_start"], demand["window_end"]) == case.window
    assert demand["days"] == case.days
    assert demand["season_months"] == case.season_months
    assert demand["measurement_method"] == case.method


@pytest.mark.parametrize("case", SOURCE_CASES, ids=lambda c: f"{c.dnsp}-{c.code}")
def test_demand_tariff_worked_surcharge(seed_client, case):
    result = surcharge(seed_client, case.dnsp, case.code)
    assert result["demand_window_hours_per_month"] == pytest.approx(case.window_hours_per_month)
    assert result["surcharge_per_kwh"] == pytest.approx(case.surcharge_per_kwh, abs=1e-5)
    assert result["monthly_demand_charge"] == pytest.approx(case.monthly_charge, abs=0.01)


@pytest.mark.parametrize("case", SOURCE_CASES, ids=lambda c: f"{c.dnsp}-{c.code}")
def test_demand_tariff_current_rate_window(seed_client, case):
    assert in_window(seed_client, case.dnsp, case.code, case.inside) is True
    assert in_window(seed_client, case.dnsp, case.code, case.outside) is case.outside_expected


# ── 2. Property sweep ──


def seeded_demand_tariffs() -> list[tuple[str, str, str, dict]]:
    """(dnsp, code, timezone, demand) for every seeded demand tariff."""
    found = []
    for f in sorted(SEED_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        zones = {d["code"]: d["timezone"] for d in data["dnsps"]}
        for t in data["tariffs"]:
            if t.get("demand"):
                found.append((t["dnsp"], t["code"], zones[t["dnsp"]], t["demand"]))
    return found


DEMAND_TARIFFS = seeded_demand_tariffs()
SWEEP_IDS = [f"{dnsp}-{code}" for dnsp, code, _, _ in DEMAND_TARIFFS]


def season_runs(months: list[int] | None) -> list[tuple[int, int]]:
    """Contiguous (first, last) month runs of a season, wrapping December to January."""
    if not months:
        return [(1, 12)]
    inside = set(months)
    firsts = [m for m in months if (m - 2) % 12 + 1 not in inside]
    runs = []
    for first in firsts:
        last = first
        while last % 12 + 1 in inside:
            last = last % 12 + 1
        runs.append((first, last))
    return runs


def local(tz: str, year: int, month: int, weekday: int, hhmm: str) -> str:
    """ISO datetime with the zone's offset: the first given weekday of a month at hh:mm."""
    first = datetime(year, month, 1)
    day = first + timedelta(days=(weekday - first.weekday()) % 7)
    hour, minute = map(int, hhmm.split(":"))
    return day.replace(hour=hour, minute=minute, tzinfo=ZoneInfo(tz)).isoformat()


def minus_one_minute(hhmm: str) -> str:
    hour, minute = map(int, hhmm.split(":"))
    total = (hour * 60 + minute - 1) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def day_fraction(days: str) -> float:
    return {"weekdays": 5 / 7, "weekday": 5 / 7, "weekends": 2 / 7, "weekend": 2 / 7}.get(days, 1.0)


def window_hours_per_day(start: str, end: str) -> float:
    s = int(start[:2]) * 60 + int(start[3:])
    e = int(end[:2]) * 60 + int(end[3:])
    return ((e - s) % (24 * 60) or 24 * 60) / 60


def in_season_weekday(demand: dict) -> int:
    """A weekday (0 Monday) the window runs on: Wednesday, or Saturday for weekend windows."""
    return 5 if demand["days"] in ("weekend", "weekends") else 2


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_window_edges(seed_client, dnsp, code, tz, demand):
    """Window start is inside, window end and the minute before start are outside."""
    month = season_runs(demand["season_months"])[0][0]
    wd = in_season_weekday(demand)
    start, end = demand["window_start"], demand["window_end"]
    if start == end:  # anytime window
        for hhmm in ("00:00", "12:00", "23:59"):
            assert in_window(seed_client, dnsp, code, local(tz, 2026, month, wd, hhmm))
        return
    assert in_window(seed_client, dnsp, code, local(tz, 2026, month, wd, start))
    assert not in_window(seed_client, dnsp, code, local(tz, 2026, month, wd, end))
    before = minus_one_minute(start)
    assert not in_window(seed_client, dnsp, code, local(tz, 2026, month, wd, before))


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_season_edges(seed_client, dnsp, code, tz, demand):
    """First and last month of each season run are inside; the months either side are not."""
    wd = in_season_weekday(demand)
    start = demand["window_start"]
    for first, last in season_runs(demand["season_months"]):
        assert in_window(seed_client, dnsp, code, local(tz, 2026, first, wd, start))
        assert in_window(seed_client, dnsp, code, local(tz, 2026, last, wd, start))
        if demand["season_months"]:
            before, after = (first - 2) % 12 + 1, last % 12 + 1
            assert not in_window(seed_client, dnsp, code, local(tz, 2026, before, wd, start))
            assert not in_window(seed_client, dnsp, code, local(tz, 2026, after, wd, start))


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_day_type(seed_client, dnsp, code, tz, demand):
    """A Wednesday and a Saturday in season, at window start, match the window's days."""
    month = season_runs(demand["season_months"])[0][0]
    start = demand["window_start"]
    days = demand["days"]
    wednesday = local(tz, 2026, month, 2, start)
    saturday = local(tz, 2026, month, 5, start)
    assert in_window(seed_client, dnsp, code, wednesday) is (days not in ("weekend", "weekends"))
    assert in_window(seed_client, dnsp, code, saturday) is (days not in ("weekday", "weekdays"))


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_surcharge_is_rate_over_window_hours(seed_client, dnsp, code, tz, demand):
    """surcharge_per_kwh = rate / window hours per month, counting only the window's days."""
    hours = window_hours_per_day(demand["window_start"], demand["window_end"]) * 30
    hours *= day_fraction(demand["days"])
    result = surcharge(seed_client, dnsp, code)
    assert result["demand_window_hours_per_month"] == pytest.approx(hours)
    # The API rounds to 5 and 2 dp; a value on a rounding tie (Endeavour N19:
    # 15.933 / 85.714 = 0.185885) can round either way with float operation
    # order, so compare to the exact value within half a unit of the last place.
    assert result["surcharge_per_kwh"] == pytest.approx(demand["rate"] / hours, abs=5e-6 + 1e-12)
    assert result["monthly_demand_charge"] == pytest.approx(
        PEAK_KW * demand["rate"], abs=5e-3 + 1e-12
    )
    assert surcharge(seed_client, dnsp, code, peak_kw=0)["surcharge_per_kwh"] == 0
