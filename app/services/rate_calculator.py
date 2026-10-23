"""Rate calculation business logic.

Determines current tariff period and calculates demand surcharges.
"""

import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models.tariff import Tariff, TariffDemand


def parse_time(time_str: str) -> time:
    """Parse HH:MM string to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def is_in_time_window(current: time, start: time, end: time) -> bool:
    """Check if current time is within a window, handling overnight spans.

    start == end is the seed data's "applies at all other times" convention
    (e.g. an off-peak catch-all window of 00:00-00:00) and always matches.
    """
    if start == end:
        return True
    if start <= end:
        return start <= current < end
    else:
        # Overnight span (e.g., 21:00 to 00:00)
        return current >= start or current < end


def is_day_match(day_type: str, weekday: int) -> bool:
    """Check if the day type matches. weekday: 0=Monday, 6=Sunday.

    Accepts both singular and plural forms -- real seed data uses the plural
    "weekdays"/"weekends" (per TariffRateResponse's own documented values,
    see seed/powercor.json, seed/ausnet.json), but this only special-cased
    the singular until now, so any weekday-restricted rate on those tariffs
    silently fell through to the "unrecognized -> always matches" default
    below and matched every day, weekends included. Found live 2026-08-10.
    """
    if day_type == "all":
        return True
    if day_type in ("weekday", "weekdays"):
        return weekday < 5
    if day_type in ("weekend", "weekends"):
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

    catchall_rate = None
    for rate in tariff.rates:
        if not is_day_match(rate.days, weekday):
            continue
        if not is_season_match(rate.season_months, month):
            continue
        start = parse_time(rate.start_time)
        end = parse_time(rate.end_time)
        if start == end:
            # "Applies at all other times" catch-all — only used if no
            # specific window matches, regardless of row iteration order.
            catchall_rate = rate
            continue
        if is_in_time_window(current_time, start, end):
            return rate.period_name, rate.rate

    if catchall_rate is not None:
        return catchall_rate.period_name, catchall_rate.rate

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


def demand_windows(
    demand: TariffDemand | None, tz: ZoneInfo, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """The demand windows within [start, end), resolved in the DNSP's time zone.

    Membership equals is_in_demand_window at every instant: each local date is
    kept by is_day_match and is_season_match, and its in-window times follow
    is_in_time_window (start == end is the whole day, end < start spans
    midnight). Windows are half-open, clipped to the range, sorted and merged,
    as aware datetimes in tz.
    """
    if demand is None:
        return []
    ws = parse_time(demand.window_start)
    we = parse_time(demand.window_end)
    midnight = time(0, 0)

    def at(day: date, t: time) -> datetime:
        return datetime.combine(day, t, tzinfo=tz).astimezone(UTC)

    lo, hi = start.astimezone(UTC), end.astimezone(UTC)
    spans: list[tuple[datetime, datetime]] = []
    day = start.astimezone(tz).date()
    while day <= end.astimezone(tz).date():
        next_day = day + timedelta(days=1)
        if is_day_match(demand.days, day.weekday()) and is_season_match(
            demand.season_months, day.month
        ):
            if ws == we:
                parts = [(at(day, midnight), at(next_day, midnight))]
            elif ws < we:
                parts = [(at(day, ws), at(day, we))]
            else:
                parts = [(at(day, midnight), at(day, we)), (at(day, ws), at(next_day, midnight))]
            for s, e in parts:
                s, e = max(s, lo), min(e, hi)
                if s >= e:
                    continue
                if spans and s <= spans[-1][1]:
                    spans[-1] = (spans[-1][0], max(spans[-1][1], e))
                else:
                    spans.append((s, e))
        day = next_day
    return [(s.astimezone(tz), e.astimezone(tz)) for s, e in spans]


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
    if start == end:
        # "Applies at all other times" catch-all — the full day.
        window_hours_per_day = 24.0
    elif start <= end:
        window_hours_per_day = (end.hour + end.minute / 60) - (start.hour + start.minute / 60)
    else:
        window_hours_per_day = (24 - start.hour - start.minute / 60) + (
            end.hour + end.minute / 60
        )

    # Days the window runs in the month: weekdays 5/7, weekends 2/7.
    days = (demand.days or "all").lower()
    if days in ("weekday", "weekdays"):
        window_days = days_in_month * 5 / 7
    elif days in ("weekend", "weekends"):
        window_days = days_in_month * 2 / 7
    else:
        window_days = days_in_month

    window_hours_per_month = window_hours_per_day * window_days
    monthly_demand_charge = peak_demand_kw * demand.rate
    # monthly charge / (peak kW x window hours), which is rate / window hours.
    surcharge_per_kwh = demand.rate / window_hours_per_month if peak_demand_kw else 0.0

    return surcharge_per_kwh, monthly_demand_charge, window_hours_per_month
