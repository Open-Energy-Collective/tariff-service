"""Unit tests for app/services/rate_calculator.py's period-matching helpers.
No DB fixture needed -- these take primitive args directly."""

from datetime import time

import pytest

from app.models.tariff import TariffDemand
from app.services.rate_calculator import (
    calculate_demand_surcharge,
    is_day_match,
    is_in_time_window,
    is_season_match,
)


def test_is_day_match_all_matches_every_weekday():
    assert all(is_day_match("all", wd) for wd in range(7))


def test_is_day_match_singular_weekday():
    assert is_day_match("weekday", 0) is True  # Monday
    assert is_day_match("weekday", 5) is False  # Saturday


def test_is_day_match_singular_weekend():
    assert is_day_match("weekend", 5) is True  # Saturday
    assert is_day_match("weekend", 0) is False  # Monday


def test_is_day_match_plural_weekdays():
    """Regression test: real seed data uses the plural form (see
    seed/powercor.json, seed/ausnet.json) -- only the singular was
    special-cased before, so this silently matched every day via the
    unrecognized-value fallback. Found live 2026-08-10."""
    assert is_day_match("weekdays", 0) is True  # Monday
    assert is_day_match("weekdays", 5) is False  # Saturday
    assert is_day_match("weekdays", 6) is False  # Sunday


def test_is_day_match_plural_weekends():
    assert is_day_match("weekends", 5) is True  # Saturday
    assert is_day_match("weekends", 6) is True  # Sunday
    assert is_day_match("weekends", 0) is False  # Monday


def test_is_in_time_window_normal_span():
    assert is_in_time_window(time(17, 0), time(16, 0), time(21, 0)) is True
    assert is_in_time_window(time(15, 0), time(16, 0), time(21, 0)) is False
    assert is_in_time_window(time(21, 0), time(16, 0), time(21, 0)) is False  # end exclusive


def test_is_in_time_window_overnight_span():
    assert is_in_time_window(time(23, 0), time(21, 0), time(6, 0)) is True
    assert is_in_time_window(time(3, 0), time(21, 0), time(6, 0)) is True
    assert is_in_time_window(time(12, 0), time(21, 0), time(6, 0)) is False


def test_is_in_time_window_catchall_start_equals_end():
    assert is_in_time_window(time(3, 0), time(0, 0), time(0, 0)) is True


def test_is_season_match_none_means_all_months():
    assert is_season_match(None, 6) is True


def test_is_season_match_within_and_outside_season():
    import json

    months = json.dumps([12, 1, 2, 3])
    assert is_season_match(months, 1) is True
    assert is_season_match(months, 6) is False


def _demand(days: str) -> TariffDemand:
    return TariffDemand(
        rate=7.0,
        window_start="17:00",
        window_end="20:00",
        measurement_method="30min_avg",
        days=days,
    )


def test_demand_surcharge_weekday_window_counts_weekdays_only():
    """A weekday-only window runs 5/7 of a 30-day month (#33)."""
    surcharge, monthly, hours = calculate_demand_surcharge(_demand("weekdays"), 4.0)
    assert hours == pytest.approx(3 * 30 * 5 / 7)
    assert monthly == pytest.approx(28.0)
    assert surcharge == pytest.approx(7.0 / (3 * 30 * 5 / 7))


def test_demand_surcharge_weekend_window_counts_weekends_only():
    _, _, hours = calculate_demand_surcharge(_demand("weekends"), 4.0)
    assert hours == pytest.approx(3 * 30 * 2 / 7)


def test_demand_surcharge_is_monthly_charge_per_kwh_at_peak():
    """surcharge = monthly charge / (peak kW x window hours), the documented contract."""
    surcharge, monthly, hours = calculate_demand_surcharge(_demand("all"), 4.0)
    assert hours == 90.0
    assert surcharge == pytest.approx(monthly / (4.0 * hours))


def test_demand_surcharge_zero_peak_is_zero():
    surcharge, monthly, _ = calculate_demand_surcharge(_demand("all"), 0.0)
    assert (surcharge, monthly) == (0.0, 0.0)
