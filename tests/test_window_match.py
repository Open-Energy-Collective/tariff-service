"""One window matching routine: the tariff's clock, public holidays, days and months."""

from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services import rate_calculator, window_match
from app.services.window_match import TariffClock, day_applies, window_applies

MELB_STD = TariffClock(ZoneInfo("Australia/Melbourne"), "standard", "VIC")
MELB_LOCAL = TariffClock(ZoneInfo("Australia/Melbourne"), "local", "VIC")
BRIS_STD = TariffClock(ZoneInfo("Australia/Brisbane"), "standard", "QLD")
BRIS_LOCAL = TariffClock(ZoneInfo("Australia/Brisbane"), "local", "QLD")

AEDT = timezone(timedelta(hours=11))
AEST = timezone(timedelta(hours=10))

CHRISTMAS_2026 = date(2026, 12, 25)  # Friday
ORDINARY_THURSDAY = date(2026, 11, 12)
ORDINARY_SATURDAY = date(2026, 11, 14)


def test_standard_clock_is_an_hour_behind_in_daylight_saving():
    i = datetime(2026, 11, 11, 7, 30, tzinfo=AEDT)
    assert MELB_STD.wall(i).time() == time(6, 30)


def test_local_clock_follows_daylight_saving():
    i = datetime(2026, 11, 11, 7, 30, tzinfo=AEDT)
    assert MELB_LOCAL.wall(i).time() == time(7, 30)


def test_wall_is_naive():
    i = datetime(2026, 11, 11, 7, 30, tzinfo=AEDT)
    assert MELB_STD.wall(i).tzinfo is None
    assert MELB_LOCAL.wall(i).tzinfo is None


def test_wall_rejects_a_naive_instant():
    with pytest.raises(ValueError):
        MELB_STD.wall(datetime(2026, 11, 11, 7, 30))


def test_standard_and_local_agree_in_winter():
    i = datetime(2026, 7, 15, 7, 30, tzinfo=AEST)
    assert MELB_STD.wall(i) == MELB_LOCAL.wall(i) == datetime(2026, 7, 15, 7, 30)


def test_standard_date_comes_from_the_standard_clock():
    # 00:30+11:00 on 12 Nov is 23:30 on 11 Nov standard
    i = datetime(2026, 11, 12, 0, 30, tzinfo=AEDT)
    assert MELB_STD.wall(i) == datetime(2026, 11, 11, 23, 30)
    assert MELB_LOCAL.wall(i) == datetime(2026, 11, 12, 0, 30)


def test_queensland_standard_matches_local():
    i = datetime(2026, 11, 11, 7, 30, tzinfo=AEST)
    assert BRIS_STD.wall(i) == BRIS_LOCAL.wall(i) == datetime(2026, 11, 11, 7, 30)


def test_instant_on_standard_clock_is_aware_utc():
    got = MELB_STD.instant(date(2026, 11, 11), time(6, 30))
    assert got == datetime(2026, 11, 10, 20, 30, tzinfo=UTC)
    assert got.utcoffset() == timedelta(0)


def test_instant_on_local_clock_follows_daylight_saving():
    got = MELB_LOCAL.instant(date(2026, 11, 11), time(6, 30))
    assert got == datetime(2026, 11, 10, 19, 30, tzinfo=UTC)
    assert got.utcoffset() == timedelta(0)


@pytest.mark.parametrize("clock", [MELB_STD, MELB_LOCAL])
def test_instant_round_trips_through_wall(clock):
    day, t = date(2026, 1, 15), time(16, 45)
    assert clock.wall(clock.instant(day, t)) == datetime.combine(day, t)


def test_unknown_basis_raises_value_error():
    with pytest.raises(ValueError):
        TariffClock(ZoneInfo("Australia/Melbourne"), "solar", "VIC")


def test_excluded_weekday_window_off_on_holiday():
    assert day_applies("weekdays", "excluded", CHRISTMAS_2026, "VIC") is False


def test_included_weekday_window_on_on_holiday():
    assert day_applies("weekdays", "included", CHRISTMAS_2026, "VIC") is True


def test_included_weekend_window_on_on_a_weekday_holiday():
    assert day_applies("weekends", "included", CHRISTMAS_2026, "VIC") is True


def test_excluded_weekend_window_off_on_a_weekend_holiday():
    new_years_day_2028 = date(2028, 1, 1)  # Saturday
    assert new_years_day_2028.weekday() == 5
    assert day_applies("weekends", "excluded", new_years_day_2028, "VIC") is False


def test_no_marker_lets_days_decide_on_holiday():
    assert day_applies("weekdays", None, CHRISTMAS_2026, "VIC") is True
    assert day_applies("weekends", None, CHRISTMAS_2026, "VIC") is False


@pytest.mark.parametrize("marker", ["included", "excluded", None])
def test_all_days_window_ignores_marker(marker):
    assert day_applies("all", marker, CHRISTMAS_2026, "VIC") is True
    assert day_applies("all", marker, ORDINARY_THURSDAY, "VIC") is True


@pytest.mark.parametrize("marker", ["included", "excluded", None])
def test_days_decides_on_an_ordinary_day(marker):
    assert day_applies("weekdays", marker, ORDINARY_THURSDAY, "VIC") is True
    assert day_applies("weekdays", marker, ORDINARY_SATURDAY, "VIC") is False
    assert day_applies("weekends", marker, ORDINARY_THURSDAY, "VIC") is False
    assert day_applies("weekends", marker, ORDINARY_SATURDAY, "VIC") is True


def test_holiday_is_looked_up_for_the_clock_state():
    melbourne_cup_2026 = date(2026, 11, 3)  # Tuesday, VIC only
    assert day_applies("weekdays", "excluded", melbourne_cup_2026, "VIC") is False
    assert day_applies("weekdays", "excluded", melbourne_cup_2026, "QLD") is True


@pytest.mark.parametrize("days", ["weekday", "weekend", "sometimes", "", "Weekdays"])
@pytest.mark.parametrize("day", [ORDINARY_THURSDAY, CHRISTMAS_2026])
def test_unknown_days_raises_value_error(days, day):
    with pytest.raises(ValueError):
        day_applies(days, "included", day, "VIC")


def overnight_excluded(instant: datetime) -> bool:
    return window_applies("23:00", "07:00", "weekdays", "excluded", None, MELB_LOCAL, instant)


def test_overnight_window_judges_each_date_alone():
    # 23:00-07:00 weekdays excluded: 03:00 on Christmas Day 2026 (Fri) False,
    # 23:30 on 24 Dec (Thu) True
    assert overnight_excluded(datetime(2026, 12, 25, 3, 0, tzinfo=AEDT)) is False
    assert overnight_excluded(datetime(2026, 12, 24, 23, 30, tzinfo=AEDT)) is True


def test_window_applies_outside_the_time_window():
    assert overnight_excluded(datetime(2026, 12, 24, 12, 0, tzinfo=AEDT)) is False


def test_window_end_is_exclusive():
    day = datetime(2026, 11, 12, 21, 0, tzinfo=AEDT)
    assert window_applies("16:00", "21:00", "all", None, None, MELB_LOCAL, day) is False
    assert window_applies(
        "16:00", "21:00", "all", None, None, MELB_LOCAL, day - timedelta(minutes=1)
    ) is True


def test_start_equal_end_covers_the_whole_day():
    i = datetime(2026, 11, 12, 3, 0, tzinfo=AEDT)
    assert window_applies("00:00", "00:00", "all", None, None, MELB_LOCAL, i) is True


def test_month_check():
    i = datetime(2026, 11, 12, 12, 0, tzinfo=AEDT)
    assert window_applies("00:00", "00:00", "all", None, [11], MELB_LOCAL, i) is True
    assert window_applies("00:00", "00:00", "all", None, [1, 2], MELB_LOCAL, i) is False
    assert window_applies("00:00", "00:00", "all", None, None, MELB_LOCAL, i) is True


def test_time_is_judged_on_the_tariff_clock():
    # 21:30 AEDT is 20:30 standard, inside 16:00-21:00 only on the standard clock.
    i = datetime(2026, 11, 12, 21, 30, tzinfo=AEDT)
    assert window_applies("16:00", "21:00", "all", None, None, MELB_STD, i) is True
    assert window_applies("16:00", "21:00", "all", None, None, MELB_LOCAL, i) is False


def test_instant_in_another_offset_is_judged_on_the_tariff_clock():
    # 13:30 UTC on Saturday 14 Nov is 00:30 Sunday local and 23:30 Saturday standard.
    i = datetime(2026, 11, 14, 13, 30, tzinfo=UTC)
    assert MELB_LOCAL.wall(i) == datetime(2026, 11, 15, 0, 30)
    assert MELB_STD.wall(i) == datetime(2026, 11, 14, 23, 30)


def test_month_is_judged_on_the_tariff_clock():
    # 00:30 AEDT on 1 Dec is 23:30 on 30 Nov standard.
    i = datetime(2026, 12, 1, 0, 30, tzinfo=AEDT)
    assert window_applies("00:00", "00:00", "all", None, [11], MELB_STD, i) is True
    assert window_applies("00:00", "00:00", "all", None, [11], MELB_LOCAL, i) is False


def test_holiday_is_judged_on_the_tariff_clock():
    # 00:30 AEDT on Christmas Day is 23:30 on Thursday 24 Dec standard.
    i = datetime(2026, 12, 25, 0, 30, tzinfo=AEDT)
    assert window_applies("00:00", "00:00", "weekdays", "excluded", None, MELB_STD, i) is True
    assert window_applies("00:00", "00:00", "weekdays", "excluded", None, MELB_LOCAL, i) is False


def test_rate_calculator_keeps_the_time_helpers_under_the_same_names():
    assert rate_calculator.parse_time is window_match.parse_time
    assert rate_calculator.is_in_time_window is window_match.is_in_time_window
