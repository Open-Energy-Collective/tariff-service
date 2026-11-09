"""Rate calculation business logic.

Determines current tariff period and calculates demand surcharges.
"""

import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models.tariff import Tariff, TariffDemandCharge
from app.services.window_match import (
    clock_for,
    is_in_time_window,  # noqa: F401  (tests name the time helpers here)
    parse_time,
    window_applies,
)

NO_RATE_IN_FORCE: tuple[str, None] = ("none", None)
CONSUMPTION_BLOCK_PREFIX = "block_"


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


def _stored_months(stored: str | None) -> list[int] | None:
    """Decode a JSON month list from the database; None means all year."""
    return None if stored is None else json.loads(stored)


def get_current_rate(tariff: Tariff, instant: datetime) -> tuple[str, float | None]:
    """Determine which rate period applies at an aware instant, on the tariff's clock.

    Returns:
        Tuple of (period_name, rate_per_kwh). NO_RATE_IN_FORCE when no rate
        applies at that time, or when the rate depends on consumption.
    """
    if any(rate.period_name.startswith(CONSUMPTION_BLOCK_PREFIX) for rate in tariff.rates):
        return NO_RATE_IN_FORCE

    clock = clock_for(tariff)
    catchall_rate = None
    for rate in tariff.rates:
        if not window_applies(
            rate.start_time,
            rate.end_time,
            rate.days,
            rate.public_holidays,
            _stored_months(rate.season_months),
            clock,
            instant,
        ):
            continue
        if parse_time(rate.start_time) == parse_time(rate.end_time):
            # "Applies at all other times" catch-all, only used if no specific
            # window matches, regardless of row iteration order.
            catchall_rate = rate
            continue
        return rate.period_name, rate.rate

    if catchall_rate is not None:
        return catchall_rate.period_name, catchall_rate.rate

    return NO_RATE_IN_FORCE


def demand_charges_at(
    tariff: Tariff, instant: datetime
) -> list[tuple[TariffDemandCharge, bool]]:
    """Every demand charge in season at an aware instant, with whether it is active.

    In season means its months cover the date on the tariff's clock. A charge in
    season is listed even when its window does not apply, as on a public holiday.
    """
    clock = clock_for(tariff)
    month = clock.wall(instant).month
    in_force = []
    for charge in tariff.demand_charges:
        months = _stored_months(charge.months)
        if months is not None and month not in months:
            continue
        active = window_applies(
            charge.start, charge.end, charge.days, charge.public_holidays, months, clock, instant
        )
        in_force.append((charge, active))
    return in_force


def demand_windows(
    demand: TariffDemandCharge | None, tz: ZoneInfo, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """The demand windows within [start, end), resolved in the DNSP's time zone.

    Each local date is kept by is_day_match and is_season_match, and its in-window times follow
    is_in_time_window (start == end is the whole day, end < start spans
    midnight). Windows are half-open, clipped to the range, sorted and merged,
    as aware datetimes in tz.
    """
    if demand is None:
        return []
    ws = parse_time(demand.start)
    we = parse_time(demand.end)
    midnight = time(0, 0)

    def at(day: date, t: time) -> datetime:
        return datetime.combine(day, t, tzinfo=tz).astimezone(UTC)

    lo, hi = start.astimezone(UTC), end.astimezone(UTC)
    spans: list[tuple[datetime, datetime]] = []
    day = start.astimezone(tz).date()
    while day <= end.astimezone(tz).date():
        next_day = day + timedelta(days=1)
        if is_day_match(demand.days, day.weekday()) and is_season_match(
            demand.months, day.month
        ):
            # The three cases of is_in_time_window, as intervals. A point
            # predicate cannot yield intervals; test_matches_is_in_demand_window_every_minute
            # guards against the two drifting apart.
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
    demand: TariffDemandCharge, peak_demand_kw: float, days_in_month: int = 30
) -> tuple[float, float, float]:
    """Calculate demand surcharge.

    Returns:
        Tuple of (surcharge_per_kwh, monthly_demand_charge, window_hours_per_month)
    """
    start = parse_time(demand.start)
    end = parse_time(demand.end)

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
