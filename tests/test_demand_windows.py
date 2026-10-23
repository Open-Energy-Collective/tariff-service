"""demand_windows against the seed demand objects (#36)."""

import json
from datetime import UTC, datetime, timedelta
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


def seed_demand_tariffs() -> list[tuple[str, str, str]]:
    """(dnsp file, tariff code, DNSP time zone) for every seed tariff with demand."""
    cases = []
    for path in sorted(SEED_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        (tz,) = {d["timezone"] for d in data["dnsps"]}
        cases += [(path.stem, t["code"], tz) for t in data["tariffs"] if t.get("demand")]
    return cases


@pytest.mark.parametrize("month_start", [datetime(2026, 12, 1), datetime(2026, 6, 1)])
@pytest.mark.parametrize(("dnsp_file", "code", "tz_name"), seed_demand_tariffs())
def test_matches_is_in_demand_window_every_minute(dnsp_file, code, tz_name, month_start):
    tz = ZoneInfo(tz_name)
    d = load_tariff(dnsp_file, code).demand
    start = month_start.replace(tzinfo=tz)
    end = (month_start + timedelta(days=31)).replace(day=1).replace(tzinfo=tz)
    windows = demand_windows(d, tz, start, end)
    t_utc, end_utc, i = start.astimezone(UTC), end.astimezone(UTC), 0
    while t_utc < end_utc:
        while i < len(windows) and windows[i][1] <= t_utc:
            i += 1
        inside = i < len(windows) and windows[i][0] <= t_utc
        t = t_utc.astimezone(tz)
        assert inside == is_in_demand_window(d, t), t.isoformat()
        t_utc += timedelta(minutes=1)
