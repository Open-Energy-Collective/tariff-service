"""demand_windows against the seed demand charges (#31, #36, #56)."""

import json
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.models.tariff import Dnsp, Tariff, TariffDemandCharge
from app.services import tariff_service
from app.services.rate_calculator import demand_charges_at, demand_windows
from tests.test_seed_data import load_tariff

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
BNE = ZoneInfo("Australia/Brisbane")
MEL = ZoneInfo("Australia/Melbourne")


def charge(start: str, end: str, rate: float, period: str = "peak", **fields) -> TariffDemandCharge:
    return TariffDemandCharge(
        period=period, rate=rate, unit="kW", start=start, end=end, days="all",
        measurement_method="peak_kw", peak_period="month", **fields,
    )


def tariff_of(*charges: TariffDemandCharge, basis: str = "local") -> Tariff:
    return Tariff(
        code="T",
        time_basis=basis,
        dnsp=Dnsp(code="d", name="d", state="VIC", timezone="Australia/Melbourne"),
        demand_charges=list(charges),
    )


def melbourne_day(day: int, *hours_and_rates) -> list[tuple[datetime, datetime, float]]:
    """(start hour, end hour, rate) stretches of an October 2026 day in Melbourne."""
    return [
        (datetime(2026, 10, day, h0, tzinfo=MEL), datetime(2026, 10, day, h1, tzinfo=MEL), rate)
        for h0, h1, rate in hours_and_rates
    ]


def test_peak_over_shoulder_splits_into_three_stretches():
    tariff = tariff_of(charge("07:00", "22:00", 3.0, "shoulder"), charge("17:00", "20:00", 9.0))
    s, e = datetime(2026, 10, 20, tzinfo=MEL), datetime(2026, 10, 21, tzinfo=MEL)
    assert demand_windows(tariff, s, e) == melbourne_day(
        20, (7, 17, 3.0), (17, 20, 9.0), (20, 22, 3.0)
    )


def test_anytime_under_peak_splits_the_day():
    tariff = tariff_of(charge("00:00", "00:00", 2.0, "anytime"), charge("17:00", "20:00", 9.0))
    s, e = datetime(2026, 10, 20, tzinfo=MEL), datetime(2026, 10, 21, tzinfo=MEL)
    assert demand_windows(tariff, s, e) == [
        (s, datetime(2026, 10, 20, 17, tzinfo=MEL), 2.0),
        (datetime(2026, 10, 20, 17, tzinfo=MEL), datetime(2026, 10, 20, 20, tzinfo=MEL), 9.0),
        (datetime(2026, 10, 20, 20, tzinfo=MEL), e, 2.0),
    ]


def test_adjacent_equal_rates_merge():
    tariff = tariff_of(charge("07:00", "12:00", 3.0), charge("12:00", "17:00", 3.0))
    s, e = datetime(2026, 10, 20, tzinfo=MEL), datetime(2026, 10, 21, tzinfo=MEL)
    assert demand_windows(tariff, s, e) == melbourne_day(20, (7, 17, 3.0))


def test_nasn12_has_windows_in_both_seasons(seed_client):
    response = seed_client.get(
        "/api/v1/calculate/demand-windows",
        params={
            "dnsp": "ausnet",
            "tariff": "NASN12",
            "start": "2026-11-30T00:00:00+11:00",
            "end": "2026-12-02T00:00:00+11:00",
        },
    )
    assert response.status_code == 200
    assert response.json()["windows"] == [
        {"start": "2026-11-30T15:00:00+11:00", "end": "2026-11-30T21:00:00+11:00", "rate": 2.862},
        {"start": "2026-12-01T15:00:00+11:00", "end": "2026-12-01T21:00:00+11:00", "rate": 11.473},
    ]


def overnight_standard() -> Tariff:
    return tariff_of(charge("23:00", "07:00", 5.0), basis="standard")


def test_standard_tariff_on_changeover_day_has_no_gap_or_double():
    # Melbourne daylight saving starts 2026-10-04 02:00. 23:00-07:00 at UTC+10 all year
    # ends at 08:00 on the summer clock. The night across the change is 8 hours whole.
    s = datetime(2026, 10, 3, tzinfo=MEL)
    e = datetime(2026, 10, 5, tzinfo=MEL)
    got = demand_windows(overnight_standard(), s, e)
    assert [(a.isoformat(), b.isoformat(), r) for a, b, r in got] == [
        ("2026-10-03T00:00:00+10:00", "2026-10-03T07:00:00+10:00", 5.0),
        ("2026-10-03T23:00:00+10:00", "2026-10-04T08:00:00+11:00", 5.0),
    ]
    assert got[1][1].astimezone(UTC) - got[1][0].astimezone(UTC) == timedelta(hours=8)


def test_standard_tariff_at_daylight_saving_end_has_no_gap_or_double():
    # Melbourne daylight saving ends 2027-04-04 03:00, back to 02:00.
    s = datetime(2027, 4, 3, tzinfo=MEL)
    e = datetime(2027, 4, 5, tzinfo=MEL)
    got = demand_windows(overnight_standard(), s, e)
    assert [(a.isoformat(), b.isoformat(), r) for a, b, r in got] == [
        ("2027-04-03T00:00:00+11:00", "2027-04-03T08:00:00+11:00", 5.0),
        ("2027-04-04T00:00:00+11:00", "2027-04-04T07:00:00+10:00", 5.0),
        ("2027-04-04T23:00:00+10:00", "2027-04-05T00:00:00+10:00", 5.0),
    ]
    assert got[1][1].astimezone(UTC) - got[1][0].astimezone(UTC) == timedelta(hours=8)


def versions_by_date(monkeypatch, *versions: tuple[date, Tariff]) -> None:
    """Serve each version from its start date, the newest start winning."""

    def in_force(db, dnsp_code, tariff_code, on):
        return next((t for start, t in sorted(versions, reverse=True) if start <= on), None)

    monkeypatch.setattr(tariff_service, "get_tariff_detail", in_force)


def versions_of(rate_before: float, rate_after: float) -> list[tuple[date, Tariff]]:
    return [
        (date(2026, 1, 1), tariff_of(charge("00:00", "00:00", rate_before, "anytime"))),
        (date(2026, 7, 1), tariff_of(charge("00:00", "00:00", rate_after, "anytime"))),
    ]


def windows_across_june_30(monkeypatch, *versions):
    versions_by_date(monkeypatch, *versions)
    return tariff_service.demand_windows_in_force(
        None, "d", "T", MEL,
        datetime(2026, 6, 30, tzinfo=MEL), datetime(2026, 7, 2, tzinfo=MEL),
    )


def test_version_change_with_new_rate_does_not_merge(monkeypatch):
    boundary = datetime(2026, 7, 1, tzinfo=MEL)
    assert windows_across_june_30(monkeypatch, *versions_of(5.0, 7.0)) == [
        (datetime(2026, 6, 30, tzinfo=MEL), boundary, 5.0),
        (boundary, datetime(2026, 7, 2, tzinfo=MEL), 7.0),
    ]


def test_version_change_at_the_same_rate_merges(monkeypatch):
    assert windows_across_june_30(monkeypatch, *versions_of(5.0, 5.0)) == [
        (datetime(2026, 6, 30, tzinfo=MEL), datetime(2026, 7, 2, tzinfo=MEL), 5.0),
    ]


def test_uncovered_date_still_404(seed_client):
    response = seed_client.get(
        "/api/v1/calculate/demand-windows",
        params={
            "dnsp": "ausnet",
            "tariff": "NASN12",
            "start": "2020-01-01T00:00:00+11:00",
            "end": "2020-01-02T00:00:00+11:00",
        },
    )
    assert response.status_code == 404


def test_weekday_window_skips_the_weekend():
    # Energex 3800: 17:00-20:00 weekdays, all months. 2026-10-23 is a Friday.
    t = load_tariff("energex", "3800")
    got = demand_windows(
        t, datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 27, tzinfo=BNE)
    )
    assert got == [
        (datetime(2026, 10, 23, 17, tzinfo=BNE), datetime(2026, 10, 23, 20, tzinfo=BNE), 7.0),
        (datetime(2026, 10, 26, 17, tzinfo=BNE), datetime(2026, 10, 26, 20, tzinfo=BNE), 7.0),
    ]


def test_all_day_window_merges_into_one_span():
    # Energex 8300: 00:00-00:00 all.
    t = load_tariff("energex", "8300")
    s, e = datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 30, tzinfo=BNE)
    assert demand_windows(t, s, e) == [(s, e, 13.913)]


def test_season_months_change_the_rate_at_the_season_edge():
    # Evoenergy 023: 17:00-21:00 all, 6.5424 in [6, 7, 8] and 3.9249 in the other
    # months; off-peak 0.6228 21:00-09:00 all year. 31 Aug to 2 Sep.
    t = load_tariff("evoenergy", "023")
    syd = ZoneInfo("Australia/Sydney")

    def at(day: int, hour: int) -> datetime:
        return datetime(2026, 8 if day > 2 else 9, day, hour, tzinfo=syd)

    got = demand_windows(t, at(31, 0), at(2, 0))
    assert got == [
        (at(31, 0), at(31, 9), 0.6228),
        (at(31, 17), at(31, 21), 6.5424),
        (at(31, 21), at(1, 9), 0.6228),
        (at(1, 17), at(1, 21), 3.9249),
        (at(1, 21), at(2, 0), 0.6228),
    ]


def test_seed_peak_over_anytime_splits_the_day():
    # SAPN LBAD: peak 10.224 17:00-21:00 all, November to March, over anytime 1.89.
    t = load_tariff("sapn", "LBAD")
    adl = ZoneInfo("Australia/Adelaide")
    s, e = datetime(2026, 11, 1, tzinfo=adl), datetime(2026, 11, 2, tzinfo=adl)
    assert demand_windows(t, s, e) == [
        (s, datetime(2026, 11, 1, 17, tzinfo=adl), 1.89),
        (datetime(2026, 11, 1, 17, tzinfo=adl), datetime(2026, 11, 1, 21, tzinfo=adl), 10.224),
        (datetime(2026, 11, 1, 21, tzinfo=adl), e, 1.89),
    ]


def test_range_inside_a_window_is_clipped():
    t = load_tariff("energex", "3800")
    s = datetime(2026, 10, 26, 17, 30, tzinfo=BNE)
    e = datetime(2026, 10, 26, 18, 30, tzinfo=BNE)
    assert demand_windows(t, s, e) == [(s, e, 7.0)]


def test_range_starting_at_a_window_end_excludes_it():
    t = load_tariff("energex", "3800")
    s = datetime(2026, 10, 26, 20, tzinfo=BNE)
    assert demand_windows(t, s, s + timedelta(hours=2)) == []


def test_no_demand_is_empty():
    s = datetime(2026, 10, 23, tzinfo=BNE)
    assert demand_windows(tariff_of(), s, s + timedelta(days=1)) == []


def test_dst_start_all_day_span_changes_offset():
    # Jemena A230: 00:00-00:00 all. Melbourne DST starts 2026-10-04 02:00.
    t = load_tariff("jemena", "A230")
    s, e = datetime(2026, 10, 1, tzinfo=MEL), datetime(2026, 10, 8, tzinfo=MEL)
    ((ws, we, _),) = demand_windows(t, s, e)
    assert ws.isoformat() == "2026-10-01T00:00:00+10:00"
    assert we.isoformat() == "2026-10-08T00:00:00+11:00"


# One case per distinct seed demand shape not covered above: (dnsp file, code,
# time zone, first local date, days, expected (date, start hour, end hour)).
# NASN12's 30 November is its off-season charge and 1 December its summer one;
# likewise N72 on 30 October and 2 November, and T5 on 30 September and 1 October.
# Each range crosses the shape's season edge or a weekend.
SHAPES = [
    (
        "ausgrid", "EA116", "Australia/Sydney", date(2026, 3, 30), 3,
        [(date(2026, 3, 30), 15, 21), (date(2026, 3, 31), 15, 21)],
    ),
    (
        "ausgrid", "EA251", "Australia/Sydney", date(2026, 11, 27), 4,
        [(date(2026, 11, 27), 15, 21), (date(2026, 11, 30), 15, 21)],
    ),
    (
        "ausgrid", "EA302", "Australia/Sydney", date(2026, 5, 1), 4,
        [(date(2026, 5, 1), 15, 21), (date(2026, 5, 4), 15, 21)],
    ),
    (
        "ausnet", "NASN12", "Australia/Melbourne", date(2026, 11, 30), 2,
        [(date(2026, 11, 30), 15, 21), (date(2026, 12, 1), 15, 21)],
    ),
    (
        "endeavour", "N72", "Australia/Sydney", date(2026, 10, 30), 4,
        [(date(2026, 10, 30), 16, 20), (date(2026, 11, 2), 16, 20)],
    ),
    (
        "energex", "3900", "Australia/Brisbane", date(2026, 10, 24), 1,
        [(date(2026, 10, 24), 16, 21)],
    ),
    (
        # 07:00-17:00 AEST is 08:00-18:00 on the Canberra clock in daylight saving (#68).
        "evoenergy", "101", "Australia/Sydney", date(2026, 10, 23), 3,
        [(date(2026, 10, 23), 8, 18)],
    ),
    (
        "powerwater", "T5", "Australia/Darwin", date(2026, 9, 30), 2,
        [(date(2026, 9, 30), 15, 21), (date(2026, 10, 1), 15, 21)],
    ),
]


@pytest.mark.parametrize(("dnsp_file", "code", "tz_name", "first", "days", "expected"), SHAPES)
def test_seed_demand_shape(dnsp_file, code, tz_name, first, days, expected):
    tz = ZoneInfo(tz_name)
    t = load_tariff(dnsp_file, code)
    start = datetime.combine(first, time(0), tzinfo=tz)
    end = datetime.combine(first + timedelta(days=days), time(0), tzinfo=tz)
    assert [(a, b) for a, b, _ in demand_windows(t, start, end)] == [
        (datetime.combine(day, time(h0), tzinfo=tz), datetime.combine(day, time(h1), tzinfo=tz))
        for day, h0, h1 in expected
    ]


def seed_demand_tariffs() -> list[tuple[str, str, str]]:
    """(dnsp file, tariff code, DNSP time zone) for every seed tariff with demand."""
    cases = []
    for path in sorted(SEED_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        (tz,) = {d["timezone"] for d in data["dnsps"]}
        cases += [(path.stem, t["code"], tz) for t in data["tariffs"] if t.get("demand_charges")]
    return cases


def local_month(year: int, month: int):
    """[1st of the month, 1st of the next) in the DNSP's local time."""
    return lambda tz: (
        datetime(year, month, 1, tzinfo=tz),
        datetime(year + month // 12, month % 12 + 1, 1, tzinfo=tz),
    )


RANGES = {
    "december": local_month(2026, 12),
    "june": local_month(2026, 6),
    # A UTC start off the local hour (23:07 on 31 March in Brisbane, 00:07 on
    # 1 April in Sydney), across the 5 April DST end.
    "april-utc": lambda tz: (
        datetime(2026, 3, 31, 13, 7, tzinfo=UTC),
        datetime(2026, 5, 1, tzinfo=UTC),
    ),
}


def assert_matches_demand_charges_at(tariff: Tariff, start: datetime, end: datetime) -> None:
    """Every minute of [start, end) is inside a window exactly when a charge is active."""
    zone = ZoneInfo(tariff.dnsp.timezone)
    windows = demand_windows(tariff, start, end)
    t_utc, end_utc, i = start.astimezone(UTC), end.astimezone(UTC), 0
    while t_utc < end_utc:
        while i < len(windows) and windows[i][1] <= t_utc:
            i += 1
        inside = i < len(windows) and windows[i][0] <= t_utc
        t = t_utc.astimezone(zone)
        assert inside == any(active for _, active in demand_charges_at(tariff, t)), t.isoformat()
        t_utc += timedelta(minutes=1)


@pytest.mark.parametrize("range_name", RANGES)
@pytest.mark.parametrize(("dnsp_file", "code", "tz_name"), seed_demand_tariffs())
def test_matches_is_in_demand_window_every_minute(dnsp_file, code, tz_name, range_name):
    start, end = RANGES[range_name](ZoneInfo(tz_name))
    assert_matches_demand_charges_at(load_tariff(dnsp_file, code), start, end)


@pytest.mark.parametrize(
    "first, last",
    [
        (datetime(2026, 10, 1, tzinfo=MEL), datetime(2026, 10, 8, tzinfo=MEL)),
        (datetime(2027, 4, 1, tzinfo=MEL), datetime(2027, 4, 8, tzinfo=MEL)),
    ],
    ids=["daylight-saving-starts", "daylight-saving-ends"],
)
@pytest.mark.parametrize(
    "tariff",
    [
        overnight_standard(),
        tariff_of(charge("15:00", "21:00", 4.0, months="[10, 4]"), basis="standard"),
        tariff_of(charge("00:00", "00:00", 2.0, "anytime"), basis="standard"),
    ],
    ids=["overnight", "evening-in-season", "all-day"],
)
def test_matches_demand_charges_at_on_a_standard_clock_every_minute(tariff, first, last):
    assert_matches_demand_charges_at(tariff, first, last)


# Bounds inside the daylight saving hour (#63). Melbourne 2026: daylight saving ends
# 2026-04-05 03:00, back to 02:00, so 02:00-03:00 reads twice; it starts 2026-10-04
# 02:00, on to 03:00, so 02:00-03:00 never reads. A local window is the set of
# instants whose local clock reads inside it.
FALL_BACK = date(2026, 4, 5)
SPRING_FORWARD = date(2026, 10, 4)
AEST_FIXED = timezone(timedelta(hours=10))


def windows_on(tariff: Tariff, day: date) -> list[tuple[str, str]]:
    s = datetime.combine(day, time(0), tzinfo=MEL)
    e = datetime.combine(day + timedelta(days=1), time(0), tzinfo=MEL)
    return [(a.isoformat(), b.isoformat()) for a, b, _ in demand_windows(tariff, s, e)]


@pytest.mark.parametrize(
    ("start", "end", "day", "expected"),
    [
        # Fall back: the repeated half hour 02:00-02:30 is in the window both times.
        ("01:30", "02:30", FALL_BACK, [
            ("2026-04-05T01:30:00+11:00", "2026-04-05T02:30:00+11:00"),
            ("2026-04-05T02:00:00+10:00", "2026-04-05T02:30:00+10:00"),
        ]),
        ("02:00", "03:00", FALL_BACK, [
            ("2026-04-05T02:00:00+11:00", "2026-04-05T03:00:00+10:00"),
        ]),
        ("02:30", "03:00", FALL_BACK, [
            ("2026-04-05T02:30:00+11:00", "2026-04-05T02:00:00+10:00"),
            ("2026-04-05T02:30:00+10:00", "2026-04-05T03:00:00+10:00"),
        ]),
        # Spring forward: the clock skips 02:00-03:00, so that part matches nothing.
        ("01:30", "02:30", SPRING_FORWARD, [
            ("2026-10-04T01:30:00+10:00", "2026-10-04T03:00:00+11:00"),
        ]),
        ("02:00", "03:00", SPRING_FORWARD, []),
        ("02:30", "04:00", SPRING_FORWARD, [
            ("2026-10-04T03:00:00+11:00", "2026-10-04T04:00:00+11:00"),
        ]),
    ],
)
def test_local_window_bound_in_the_daylight_saving_hour(start, end, day, expected):
    assert windows_on(tariff_of(charge(start, end, 1.0)), day) == expected


@pytest.mark.parametrize("day", [FALL_BACK, SPRING_FORWARD])
def test_standard_window_bound_in_the_daylight_saving_hour(day):
    # UTC+10 all year: 01:30-02:30 standard is one hour whatever the local clock does.
    ((a, b),) = windows_on(tariff_of(charge("01:30", "02:30", 1.0), basis="standard"), day)
    a, b = datetime.fromisoformat(a), datetime.fromisoformat(b)
    assert a == datetime.combine(day, time(1, 30), tzinfo=AEST_FIXED)
    assert b - a == timedelta(hours=1)


# Bounds at, inside and either side of the shifted hour, including overnight spans.
SHIFTED_HOUR_WINDOWS = [
    ("01:30", "02:30"), ("02:00", "03:00"), ("02:30", "03:00"), ("02:00", "02:30"),
    ("01:00", "02:00"), ("03:00", "04:00"), ("02:30", "06:00"), ("22:00", "02:30"),
    ("02:30", "02:00"), ("03:00", "02:00"), ("00:00", "00:00"),
]


@pytest.mark.parametrize("basis", ["local", "standard"])
@pytest.mark.parametrize("day", [FALL_BACK, SPRING_FORWARD], ids=["fall-back", "spring-forward"])
@pytest.mark.parametrize(("start", "end"), SHIFTED_HOUR_WINDOWS)
def test_windows_agree_with_active_every_15_minutes_across_transitions(start, end, day, basis):
    tariff = tariff_of(charge(start, end, 1.0), basis=basis)
    first = datetime.combine(day - timedelta(days=1), time(0), tzinfo=MEL)
    last = datetime.combine(day + timedelta(days=2), time(0), tzinfo=MEL)
    windows = demand_windows(tariff, first, last)
    t = first.astimezone(UTC)
    while t < last.astimezone(UTC):
        inside = any(a <= t < b for a, b, _ in windows)
        active = any(on for _, on in demand_charges_at(tariff, t))
        assert inside == active, t.astimezone(MEL).isoformat()
        t += timedelta(minutes=15)
