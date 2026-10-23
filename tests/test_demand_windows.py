"""demand_windows against the seed demand objects (#36)."""

import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.services.rate_calculator import demand_windows, is_in_demand_window
from tests.test_seed_data import load_tariff

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
BNE = ZoneInfo("Australia/Brisbane")
MEL = ZoneInfo("Australia/Melbourne")


def test_weekday_window_skips_the_weekend():
    # Energex 3800: 17:00-20:00 weekdays, all months. 2026-10-23 is a Friday.
    d = load_tariff("energex", "3800").demand
    got = demand_windows(
        d, BNE, datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 27, tzinfo=BNE)
    )
    assert got == [
        (datetime(2026, 10, 23, 17, tzinfo=BNE), datetime(2026, 10, 23, 20, tzinfo=BNE)),
        (datetime(2026, 10, 26, 17, tzinfo=BNE), datetime(2026, 10, 26, 20, tzinfo=BNE)),
    ]


def test_all_day_window_merges_into_one_span():
    # Energex 8300: 00:00-00:00 all.
    d = load_tariff("energex", "8300").demand
    s, e = datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 30, tzinfo=BNE)
    assert demand_windows(d, BNE, s, e) == [(s, e)]


def test_season_months_exclude_out_of_season_days():
    # Evoenergy 023: 17:00-21:00 all, [6, 7, 8]. 31 Aug to 2 Sep.
    d = load_tariff("evoenergy", "023").demand
    syd = ZoneInfo("Australia/Sydney")
    got = demand_windows(
        d, syd, datetime(2026, 8, 31, tzinfo=syd), datetime(2026, 9, 2, tzinfo=syd)
    )
    assert got == [(datetime(2026, 8, 31, 17, tzinfo=syd), datetime(2026, 8, 31, 21, tzinfo=syd))]


def test_range_inside_a_window_is_clipped():
    d = load_tariff("energex", "3800").demand
    s = datetime(2026, 10, 26, 17, 30, tzinfo=BNE)
    e = datetime(2026, 10, 26, 18, 30, tzinfo=BNE)
    assert demand_windows(d, BNE, s, e) == [(s, e)]


def test_range_starting_at_a_window_end_excludes_it():
    d = load_tariff("energex", "3800").demand
    s = datetime(2026, 10, 26, 20, tzinfo=BNE)
    assert demand_windows(d, BNE, s, s + timedelta(hours=2)) == []


def test_no_demand_is_empty():
    s = datetime(2026, 10, 23, tzinfo=BNE)
    assert demand_windows(None, BNE, s, s + timedelta(days=1)) == []


def test_dst_start_all_day_span_changes_offset():
    # Jemena A230: 00:00-00:00 all. Melbourne DST starts 2026-10-04 02:00.
    d = load_tariff("jemena", "A230").demand
    s, e = datetime(2026, 10, 1, tzinfo=MEL), datetime(2026, 10, 8, tzinfo=MEL)
    ((ws, we),) = demand_windows(d, MEL, s, e)
    assert ws.isoformat() == "2026-10-01T00:00:00+10:00"
    assert we.isoformat() == "2026-10-08T00:00:00+11:00"


# One case per distinct seed demand shape not covered above: (dnsp file, code,
# time zone, first local date, days, expected (date, start hour, end hour)).
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
        [(date(2026, 12, 1), 15, 21)],
    ),
    (
        "endeavour", "N72", "Australia/Sydney", date(2026, 10, 30), 4,
        [(date(2026, 11, 2), 16, 20)],
    ),
    (
        "energex", "3900", "Australia/Brisbane", date(2026, 10, 24), 1,
        [(date(2026, 10, 24), 16, 21)],
    ),
    (
        "evoenergy", "101", "Australia/Sydney", date(2026, 10, 23), 3,
        [(date(2026, 10, 23), 7, 17)],
    ),
    (
        "powerwater", "T5", "Australia/Darwin", date(2026, 9, 30), 2,
        [(date(2026, 10, 1), 15, 21)],
    ),
    (
        "sapn", "LBAD", "Australia/Adelaide", date(2026, 10, 31), 2,
        [(date(2026, 11, 1), 17, 21)],
    ),
]


@pytest.mark.parametrize(("dnsp_file", "code", "tz_name", "first", "days", "expected"), SHAPES)
def test_seed_demand_shape(dnsp_file, code, tz_name, first, days, expected):
    tz = ZoneInfo(tz_name)
    d = load_tariff(dnsp_file, code).demand
    start = datetime.combine(first, time(0), tzinfo=tz)
    end = datetime.combine(first + timedelta(days=days), time(0), tzinfo=tz)
    assert demand_windows(d, tz, start, end) == [
        (datetime.combine(day, time(h0), tzinfo=tz), datetime.combine(day, time(h1), tzinfo=tz))
        for day, h0, h1 in expected
    ]


def seed_demand_tariffs() -> list[tuple[str, str, str]]:
    """(dnsp file, tariff code, DNSP time zone) for every seed tariff with demand."""
    cases = []
    for path in sorted(SEED_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        (tz,) = {d["timezone"] for d in data["dnsps"]}
        cases += [(path.stem, t["code"], tz) for t in data["tariffs"] if t.get("demand")]
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


@pytest.mark.parametrize("range_name", RANGES)
@pytest.mark.parametrize(("dnsp_file", "code", "tz_name"), seed_demand_tariffs())
def test_matches_is_in_demand_window_every_minute(dnsp_file, code, tz_name, range_name):
    tz = ZoneInfo(tz_name)
    d = load_tariff(dnsp_file, code).demand
    start, end = RANGES[range_name](tz)
    windows = demand_windows(d, tz, start, end)
    t_utc, end_utc, i = start.astimezone(UTC), end.astimezone(UTC), 0
    while t_utc < end_utc:
        while i < len(windows) and windows[i][1] <= t_utc:
            i += 1
        inside = i < len(windows) and windows[i][0] <= t_utc
        t = t_utc.astimezone(tz)
        assert inside == is_in_demand_window(d, t), t.isoformat()
        t_utc += timedelta(minutes=1)
