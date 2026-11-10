"""Demand tariffs against the 2026-27 sources, through the API on the real seed (#22).

Every test here uses the seed_client fixture: the API reads the database that
seed/build_db.py builds from seed/*.json, not the conftest.py fixtures.

1. Source-checked: one demand tariff per seeded DNSP. Each case states the demand
   rate, window, days, season and measurement method as its knowledge entry
   (OEC/knowledge/documents/<dnsp>/) gives them, then checks the seed, one worked
   /calculate/demand-surcharge and two /calculate/current-rate results.
2. Property sweep over every seeded demand tariff: window edges, season edges,
   day type, and surcharge_per_kwh = rate / window hours per month (#33).
3. Every demand charge of every seeded demand tariff against its source (#62),
   and strict xfails for source charges the model cannot hold yet.
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


def charge_active(client, dnsp: str, code: str, at: str, rate: float) -> bool:
    """Whether the charge with this rate is active at the time; other charges are ignored."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": dnsp, "tariff": code, "datetime": at},
    )
    assert response.status_code == 200
    return any(c["active"] and c["rate"] == rate for c in response.json()["demand_charges"])


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
    """One demand tariff as its 2026-27 source states it. Where the source is
    silent (a measurement interval), the case holds the seed's value and says so.

    seed_rate is the source rate converted to the seed's per unit per month
    (stated in conversion). window_hours_per_month counts a weekday window as 5/7
    of a 30-day month. inside and outside are local times for /current-rate,
    judged on the charge at seed_rate; an anytime window has no outside, so both
    are inside. unit and peak_period hold for every charge of the tariff (#62);
    off_season_charged is a local time outside the highest charge's months when
    the source still charges demand.
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
    unit: str = "kW"
    peak_period: str = "month"
    off_season_charged: str | None = None


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
        method="30min_max",  # as seeded: the source states no measurement interval
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
    ),
    SourceCase(
        dnsp="endeavour",
        code="N72",
        entry="endeavour-energy/2026-10-21-network-price-list-2026-27.md (s 5.3, 6.1)",
        source_rate="18.18 c/kW/day high season, 9.27 low season",
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
        off_season_charged="2026-07-15T16:00:00+10:00",
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
        conversion="none",
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
        unit="kVA",
    ),
    SourceCase(
        dnsp="evoenergy",
        code="023",
        entry="evoenergy/2026-10-21-schedule-of-charges-2026-27.md; "
        "evoenergy/2026-10-23-revised-tss-2024-29.md (winter months)",
        source_rate="21.808 c/kW/day Seasonal kW Demand (High); Low 13.083, off-peak 2.076",
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
        off_season_charged="2026-10-14T18:00:00+11:00",
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
        peak_period="rolling_12_months",
    ),
    SourceCase(
        dnsp="powerwater",
        code="T5",
        entry="power-and-water/2026-10-21-network-tariffs-2026-27.md; per month per "
        "findings/2026-10-21-tariff-service-source-gaps-resolved-2026-27.md",
        source_rate="16.7014 $/kVA On Season, 3.9297 Off Season",
        conversion="none; read as per month",
        seed_rate=16.7014,
        window=("15:00", "21:00"),
        days="weekdays",
        season_months=[1, 2, 3, 10, 11, 12],
        method="30min_max",  # as seeded: the source states no measurement interval
        inside="2026-10-14T15:00:00+09:30",
        outside="2026-10-14T21:00:00+09:30",
        outside_expected=False,
        window_hours_per_month=6 * 30 * 5 / 7,
        surcharge_per_kwh=0.1299,
        monthly_charge=83.51,
        unit="kVA",
        off_season_charged="2026-07-15T15:00:00+09:30",
    ),
    SourceCase(
        dnsp="sapn",
        code="MBTOUD",
        entry="sa-power-networks/2026-10-21-customer-overview-2026-27.md (Table 4, Table 9)",
        source_rate="0.0861 $/kVA/day",
        conversion="x 30",
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
        unit="kVA",
        peak_period="rolling_12_months",
    ),
]


def test_source_cases_cover_every_dnsp_with_a_demand_tariff():
    with_demand = {
        tariff["dnsp"]
        for f in SEED_DIR.glob("*.json")
        for tariff in json.loads(f.read_text())["tariffs"]
        if tariff.get("demand_charges")
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
    """The charge at seed_rate is active inside its window; other charges may run outside it."""
    assert charge_active(seed_client, case.dnsp, case.code, case.inside, case.seed_rate)
    outside = charge_active(seed_client, case.dnsp, case.code, case.outside, case.seed_rate)
    assert outside is case.outside_expected


@pytest.mark.parametrize("case", SOURCE_CASES, ids=lambda c: f"{c.dnsp}-{c.code}")
def test_demand_tariff_unit_peak_period_and_off_season(seed_client, case):
    """Every charge carries the source's unit and peak period, and demand charged
    outside the highest charge's months is in a window then (#62)."""
    charges = tariff_detail(seed_client, case.dnsp, case.code)["demand_charges"]
    assert {(c["unit"], c["peak_period"]) for c in charges} == {(case.unit, case.peak_period)}
    if case.off_season_charged is not None:
        assert in_window(seed_client, case.dnsp, case.code, case.off_season_charged) is True


# ── 2. Property sweep ──


# A `standard` tariff's clock: the zone's standard offset all year (Etc/GMT-10 is UTC+10).
STANDARD_CLOCK = {"Australia/Sydney": "Etc/GMT-10", "Australia/Melbourne": "Etc/GMT-10"}


def seeded_demand_tariffs() -> list[tuple[str, str, str, dict]]:
    """(dnsp, code, timezone, demand) for every seeded demand tariff. The timezone is
    the tariff's clock: the DNSP zone, or its standard offset for a `standard` tariff."""
    found = []
    for f in sorted(SEED_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        zones = {d["code"]: d["timezone"] for d in data["dnsps"]}
        for t in data["tariffs"]:
            if t.get("demand_charges"):
                charge = min(t["demand_charges"], key=lambda c: (-c["rate"], c["start"]))
                demand = {
                    **charge,
                    "window_start": charge["start"],
                    "window_end": charge["end"],
                    "season_months": charge["months"],
                }
                zone = zones[t["dnsp"]]
                if t["time_basis"] == "standard":
                    zone = STANDARD_CLOCK[zone]
                found.append((t["dnsp"], t["code"], zone, demand))
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


def local(tz: str, month: int, weekday: int, hhmm: str) -> str:
    """ISO datetime with the zone's offset: the first given weekday of a month at hh:mm."""
    # A month of the 2026-27 tariff year, which the seed versions are in force for.
    first = datetime(2027 if month < 7 else 2026, month, 1)
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
    """Window start is inside, window end and the minute before start are outside.
    Judged on the highest charge alone: the tariff's other charges may run then."""
    month = season_runs(demand["season_months"])[0][0]
    wd = in_season_weekday(demand)
    start, end, rate = demand["window_start"], demand["window_end"], demand["rate"]
    if start == end:  # anytime window
        for hhmm in ("00:00", "12:00", "23:59"):
            assert charge_active(seed_client, dnsp, code, local(tz, month, wd, hhmm), rate)
        return
    assert charge_active(seed_client, dnsp, code, local(tz, month, wd, start), rate)
    assert not charge_active(seed_client, dnsp, code, local(tz, month, wd, end), rate)
    before = minus_one_minute(start)
    assert not charge_active(seed_client, dnsp, code, local(tz, month, wd, before), rate)


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_season_edges(seed_client, dnsp, code, tz, demand):
    """First and last month of each season run are inside; the months either side are not."""
    wd = in_season_weekday(demand)
    start, rate = demand["window_start"], demand["rate"]
    for first, last in season_runs(demand["season_months"]):
        assert charge_active(seed_client, dnsp, code, local(tz, first, wd, start), rate)
        assert charge_active(seed_client, dnsp, code, local(tz, last, wd, start), rate)
        if demand["season_months"]:
            before, after = (first - 2) % 12 + 1, last % 12 + 1
            assert not charge_active(seed_client, dnsp, code, local(tz, before, wd, start), rate)
            assert not charge_active(seed_client, dnsp, code, local(tz, after, wd, start), rate)


@pytest.mark.parametrize(("dnsp", "code", "tz", "demand"), DEMAND_TARIFFS, ids=SWEEP_IDS)
def test_sweep_day_type(seed_client, dnsp, code, tz, demand):
    """A Wednesday and a Saturday in season, at window start, match the window's days."""
    month = season_runs(demand["season_months"])[0][0]
    start, rate, days = demand["window_start"], demand["rate"], demand["days"]
    wednesday = local(tz, month, 2, start)
    saturday = local(tz, month, 5, start)
    weekday_runs = days not in ("weekend", "weekends")
    weekend_runs = days not in ("weekday", "weekdays")
    assert charge_active(seed_client, dnsp, code, wednesday, rate) is weekday_runs
    assert charge_active(seed_client, dnsp, code, saturday, rate) is weekend_runs


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


# ── 3. Every demand charge against its source (#62) ──


def dc(
    rate: float,
    start: str,
    end: str,
    days: str = "all",
    months: list[int] | None = None,
    *,
    holidays: str | None = None,
    unit: str = "kW",
    period: str = "peak",
    method: str = "30min_max",
    peak_period: str = "month",
) -> tuple:
    """One demand charge as compared with the API: months sorted, null as ()."""
    return (
        period, rate, unit, start, end, days, holidays or "",
        tuple(sorted(months or ())), method, peak_period,
    )


def as_charge(c: dict) -> tuple:
    return dc(
        c["rate"], c["start"], c["end"], c["days"], c["months"],
        holidays=c["public_holidays"], unit=c["unit"], period=c["period"],
        method=c["measurement_method"], peak_period=c["peak_period"],
    )


AUSGRID_HIGH = [1, 2, 3, 6, 7, 8, 11, 12]
ENDEAVOUR_HIGH, ENDEAVOUR_LOW = [1, 2, 3, 11, 12], [4, 5, 6, 7, 8, 9, 10]
POWERWATER_ON, POWERWATER_OFF = [1, 2, 3, 10, 11, 12], [4, 5, 6, 7, 8, 9]
EVOENERGY_WINTER = [6, 7, 8]
EVOENERGY_NON_WINTER = [1, 2, 3, 4, 5, 9, 10, 11, 12]


def ausgrid_capacity(rate: float, unit: str) -> tuple:
    """Capacity: 15:00-21:00 working weekdays all year, on the prior 12 months' peak."""
    return dc(rate, "15:00", "21:00", "weekdays", holidays="excluded", unit=unit,
              peak_period="rolling_12_months")


def endeavour(high: float, low: float, unit: str = "kW") -> list[tuple]:
    """Peak 16:00-20:00 business days, high season November to March, low April to October."""
    return [
        dc(rate, "16:00", "20:00", "weekdays", months, holidays="excluded", unit=unit)
        for rate, months in ((high, ENDEAVOUR_HIGH), (low, ENDEAVOUR_LOW))
    ]


def essential(peak: float) -> list[tuple]:
    """Peak 17:00-20:00 weekdays, times unchanged on a weekday public holiday."""
    return [dc(peak, "17:00", "20:00", "weekdays", holidays="included", unit="kVA")]


def powerwater(on: float, off: float) -> list[tuple]:
    """15:00-21:00 Monday to Friday including public holidays, On and Off Season."""
    return [
        dc(rate, "15:00", "21:00", "weekdays", months, holidays="included", unit="kVA")
        for rate, months in ((on, POWERWATER_ON), (off, POWERWATER_OFF))
    ]


# Per tariff: the knowledge entries (OEC/knowledge/documents/) its values are
# checked against, and every demand charge they give, converted to per unit per
# month (c/day x 30 / 100, $/day x 30, $/yr / 12). Where a source is silent the
# seed's value is kept and the gap is named in the tariff's notes.
AUSGRID = "ausgrid/2026-10-21-network-price-list-2026-27.md; " \
    "ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.md (Table 11)"
ENDEAVOUR = "endeavour-energy/2026-10-21-network-price-list-2026-27.md (s 5.3, 6.1, 6.2, Table 1a)"
ENERGEX = "energex/2026-10-21-network-price-list-2026-27.md; " \
    "energex/2026-10-21-network-tariff-guide-2026-27.md (Table 6, s 3.3)"
ESSENTIAL = "essential-energy/2026-10-21-price-list-explanatory-notes-2026-27.md (p 1, s 4, s 6)"
EVOENERGY = "evoenergy/2026-10-21-schedule-of-charges-2026-27.md; " \
    "evoenergy/2026-10-23-revised-tss-2024-29.md (winter months)"
POWERWATER = "power-and-water/2026-10-21-network-tariffs-2026-27.md"
SAPN = "sa-power-networks/2026-10-21-customer-overview-2026-27.md (Table 4, 5, 9)"

SOURCE_CHARGES: dict[tuple[str, str], tuple[str, list[tuple]]] = {
    ("ausgrid", "EA111"): (AUSGRID, [dc(0.43752, "15:00", "21:00", "all", AUSGRID_HIGH)]),
    ("ausgrid", "EA116"): (AUSGRID, [dc(11.8455, "15:00", "21:00", "all", AUSGRID_HIGH)]),
    ("ausgrid", "EA251"): (AUSGRID, [
        dc(0.41451, "15:00", "21:00", "weekdays", AUSGRID_HIGH, holidays="excluded"),
    ]),
    ("ausgrid", "EA256"): (AUSGRID, [
        dc(13.35933, "15:00", "21:00", "weekdays", AUSGRID_HIGH, holidays="excluded"),
    ]),
    ("ausgrid", "EA302"): (AUSGRID, [ausgrid_capacity(14.50191, "kW")]),
    ("ausgrid", "EA305"): (AUSGRID, [ausgrid_capacity(17.33886, "kVA")]),
    ("ausgrid", "EA310"): (AUSGRID, [ausgrid_capacity(17.85894, "kVA")]),
    ("ausgrid", "EA370"): (AUSGRID, [ausgrid_capacity(10.38696, "kVA")]),
    ("ausgrid", "EA390"): (AUSGRID, [ausgrid_capacity(2.91345, "kVA")]),
    ("ausnet", "NASN12"): (
        "ausnet/2026-10-21-network-tariff-schedule-2026-27.md (structure 15)",
        [
            dc(rate, "15:00", "21:00", "weekdays", months, holidays="included",
               method="monthly_peak")
            for rate, months in ((11.473, [1, 2, 3, 12]), (2.862, [4, 5, 6, 7, 8, 9, 10, 11]))
        ],
    ),
    ("endeavour", "N72"): (ENDEAVOUR, endeavour(5.454, 2.781)),
    ("endeavour", "N73"): (ENDEAVOUR, endeavour(4.908, 2.502)),
    ("endeavour", "N92"): (ENDEAVOUR, endeavour(7.254, 3.576)),
    ("endeavour", "N93"): (ENDEAVOUR, endeavour(6.528, 3.219)),
    ("endeavour", "N19"): (ENDEAVOUR, endeavour(15.933, 14.499, "kVA")),
    ("endeavour", "N29"): (ENDEAVOUR, endeavour(12.588, 12.42, "kVA")),
    ("endeavour", "N39"): (ENDEAVOUR, endeavour(11.22, 11.061, "kVA")),
    ("energex", "3900"): (ENERGEX, [dc(7.0, "16:00", "21:00", "all", method="30min_avg")]),
    ("energex", "3800"): (ENERGEX, [
        dc(7.0, "17:00", "20:00", "weekdays", holidays="included", method="30min_avg"),
    ]),
    # The kW variant, which the guide provides when the meter cannot publish kVA.
    ("energex", "7200"): (ENERGEX, [
        dc(15.459, "17:00", "20:00", "weekdays", holidays="included", method="30min_avg"),
    ]),
    ("energex", "8300"): (ENERGEX, [
        dc(13.913, "00:00", "00:00", unit="kVA", period="anytime", method="30min_avg"),
    ]),
    ("essential", "BLND1AR"): (ESSENTIAL, essential(5.1925)),
    ("essential", "BLND1AB"): (ESSENTIAL, essential(9.7035)),
    ("essential", "BLND3AO"): (ESSENTIAL, essential(12.039)),
    ("essential", "BHND3AO"): (ESSENTIAL, essential(11.5026)),
    ("essential", "BSSD3AO"): (ESSENTIAL, essential(4.4388)),
    ("evoenergy", "023"): (EVOENERGY, [
        dc(6.5424, "17:00", "21:00", "all", EVOENERGY_WINTER),
        dc(3.9249, "17:00", "21:00", "all", EVOENERGY_NON_WINTER),
        dc(0.6228, "21:00", "09:00", "all", period="off_peak"),
    ]),
    ("evoenergy", "101"): (EVOENERGY, [
        dc(13.2651, "07:00", "17:00", "weekdays", holidays="included", unit="kVA"),
    ]),
    ("jemena", "A230"): ("jemena/2026-10-21-network-tariff-schedule-2026-27.md", [
        dc(6.49075, "00:00", "00:00", period="anytime", method="rolling_12month_max",
           peak_period="rolling_12_months"),
    ]),
    ("powerwater", "T5"): (POWERWATER, powerwater(16.7014, 3.9297)),
    ("powerwater", "T6"): (POWERWATER, powerwater(8.8419, 2.6154)),
    ("sapn", "MBTOUD"): (SAPN, [
        dc(2.583, "00:00", "00:00", unit="kVA", period="anytime",
           peak_period="rolling_12_months"),
    ]),
    ("sapn", "LBAD"): (SAPN, [
        dc(10.224, "17:00", "21:00", "all", [11, 12, 1, 2, 3], unit="kVA",
           peak_period="rolling_12_months"),
        dc(1.89, "00:00", "00:00", unit="kVA", period="anytime",
           peak_period="rolling_12_months"),
    ]),
}


def test_source_charges_cover_every_seeded_demand_tariff():
    assert set(SOURCE_CHARGES) == {(dnsp, code) for dnsp, code, _, _ in DEMAND_TARIFFS}


@pytest.mark.parametrize(("dnsp", "code"), SOURCE_CHARGES, ids=lambda v: v)
def test_demand_charges_match_source(seed_client, dnsp, code):
    _, expected = SOURCE_CHARGES[(dnsp, code)]
    charges = tariff_detail(seed_client, dnsp, code)["demand_charges"]
    assert sorted(map(as_charge, charges)) == sorted(expected)


# Source charges the model cannot hold yet, so the seed leaves them out (#70).
WEEKEND_HOLIDAY_GAP = (
    "a weekends window that runs on weekend public holidays and not on weekday ones "
    "has no public_holidays value"
)
TWO_WINDOW_GAP = "one charge measured over two windows has no single row"
UNHELD_CHARGES = [
    pytest.param(
        "essential", code, period, rate,
        marks=pytest.mark.xfail(reason=f"#70: {why}", strict=True),
        id=f"essential-{code}-{period}",
    )
    for code, shoulder, off_peak in (
        ("BLND3AO", 10.8924, 2.8541),
        ("BHND3AO", 10.4071, 3.1143),
        ("BSSD3AO", 3.1645, 1.2614),
    )
    for period, rate, why in (
        ("shoulder", shoulder, f"shoulder 07:00-17:00 and 20:00-22:00 weekdays: {TWO_WINDOW_GAP}"),
        ("off_peak", off_peak, f"off-peak 22:00-07:00 weekdays and all weekend: "
                               f"{TWO_WINDOW_GAP}; {WEEKEND_HOLIDAY_GAP}"),
    )
] + [
    pytest.param(
        "energex", "7200", "shoulder", 4.08,
        marks=pytest.mark.xfail(
            reason=f"#70: shoulder 13:00-17:00 and 20:00-11:00 weekdays, 13:00-11:00 weekends: "
            f"{TWO_WINDOW_GAP}; {WEEKEND_HOLIDAY_GAP}",
            strict=True,
        ),
        id="energex-7200-shoulder",
    ),
]


@pytest.mark.parametrize(("dnsp", "code", "period", "rate"), UNHELD_CHARGES)
def test_source_charge_the_model_cannot_hold(seed_client, dnsp, code, period, rate):
    charges = tariff_detail(seed_client, dnsp, code)["demand_charges"]
    assert any(c["period"] == period and c["rate"] == rate for c in charges)


@pytest.mark.xfail(
    reason="#70: LBAD peak demand is the highest daily average in the window, "
    "which no measurement_method value names",
    strict=True,
)
def test_lbad_peak_demand_is_a_daily_average(seed_client):
    demand = tariff_detail(seed_client, "sapn", "LBAD")["demand"]
    assert demand["measurement_method"] not in ("30min_max", "30min_avg")


def test_weekend_public_holiday_matches_an_ordinary_weekend_day(seed_client):
    """Energex 3800: Saturday Christmas Day 2027 is judged like an ordinary Saturday."""
    results = {}
    times = {"holiday": "2027-12-25T17:30:00+10:00", "ordinary": "2027-12-18T17:30:00+10:00"}
    for label, at in times.items():
        response = seed_client.get(
            "/api/v1/calculate/current-rate",
            params={"dnsp": "energex", "tariff": "3800", "datetime": at},
        )
        assert response.status_code == 200
        body = response.json()
        results[label] = (body["period"], body["in_demand_window"])
    assert results["holiday"] == results["ordinary"]
    assert results["holiday"][1] is False

    windows = seed_client.get(
        "/api/v1/calculate/demand-windows",
        params={
            "dnsp": "energex",
            "tariff": "3800",
            "start": "2027-12-25T00:00:00+10:00",
            "end": "2027-12-26T00:00:00+10:00",
        },
    )
    assert windows.status_code == 200
    assert windows.json()["windows"] == []


def test_current_rate_lists_demand_charges_highest_rate_first():
    from app.models.tariff import TariffDemandCharge
    from app.services.rate_calculator import demand_charge_order

    def c(rate, start):
        return TariffDemandCharge(
            period="p", rate=rate, unit="kW", start=start, end="22:00", days="all"
        )

    charges = [c(2.0, "07:00"), c(9.0, "17:00"), c(9.0, "15:00")]
    ordered = sorted(charges, key=demand_charge_order)
    assert [(x.rate, x.start) for x in ordered] == [(9.0, "15:00"), (9.0, "17:00"), (2.0, "07:00")]
