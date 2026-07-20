"""Rate calculation business logic.

Determines current tariff period and calculates demand surcharges.
"""

import json
from datetime import datetime, time

from app.models.tariff import Tariff, TariffDemand


def parse_time(time_str: str) -> time:
    """Parse HH:MM string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def is_in_time_window(current: time, start: time, end: time) -> bool:
    """Check if current time is within a window, handling overnight spans."""
    if start <= end:
        return start <= current < end
    else:
        # Overnight span (e.g., 21:00 to 00:00)
        return current >= start or current < end


def is_day_match(day_type: str, weekday: int) -> bool:
    """Check if the day type matches. weekday: 0=Monday, 6=Sunday."""
    if day_type == "all":
        return True
    if day_type == "weekday":
        return weekday < 5
    if day_type == "weekend":
        return weekday >= 5
    return True


def is_season_match(season_months: str | None, month: int) -> bool:
    """Check if the current month is in the season months."""
    if season_months is None:
        return True
    months = json.loads(season_months)
    return month in months


def get_current_rate(tariff: Tariff, dt: datetime) -> tuple[str, float]:
    """Determine which rate period applies at the given datetime.

    Returns:
        Tuple of (period_name, rate_per_kwh)
    """
    current_time = dt.time()
    weekday = dt.weekday()
    month = dt.month

    for rate in tariff.rates:
        if not is_day_match(rate.days, weekday):
            continue
        if not is_season_match(rate.season_months, month):
            continue
        start = parse_time(rate.start_time)
        end = parse_time(rate.end_time)
        if is_in_time_window(current_time, start, end):
            return rate.period_name, rate.rate

    # Fallback: return first rate (shouldn't happen with properly configured data)
    if tariff.rates:
        return tariff.rates[0].period_name, tariff.rates[0].rate
    return "unknown", 0.0


def is_in_demand_window(demand: TariffDemand | None, dt: datetime) -> bool:
    """Check if the given datetime falls within the demand window."""
    if demand is None:
        return False

    current_time = dt.time()
    weekday = dt.weekday()
    month = dt.month

    if not is_day_match(demand.days, weekday):
        return False
    if not is_season_match(demand.season_months, month):
        return False

    start = parse_time(demand.window_start)
    end = parse_time(demand.window_end)
    return is_in_time_window(current_time, start, end)


def calculate_demand_surcharge(
    demand: TariffDemand, peak_demand_kw: float, days_in_month: int = 30
) -> tuple[float, float, float]:
    """Calculate demand surcharge.

    Returns:
        Tuple of (surcharge_per_kwh, monthly_demand_charge, window_hours_per_month)
    """
    start = parse_time(demand.window_start)
    end = parse_time(demand.window_end)

    # Calculate window hours per day
    if start <= end:
        window_hours_per_day = (end.hour + end.minute / 60) - (start.hour + start.minute / 60)
    else:
        window_hours_per_day = (24 - start.hour - start.minute / 60) + (
            end.hour + end.minute / 60
        )

    window_hours_per_month = window_hours_per_day * days_in_month
    monthly_demand_charge = peak_demand_kw * demand.rate
    surcharge_per_kwh = monthly_demand_charge / window_hours_per_month

    return surcharge_per_kwh, monthly_demand_charge, window_hours_per_month
