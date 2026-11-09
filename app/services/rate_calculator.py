"""Rate calculation business logic.

Determines current tariff period and calculates demand surcharges.
"""

import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models.tariff import Tariff, TariffDemandCharge
from app.services.window_match import (
    TariffClock,
    clock_for,
    day_applies,
    parse_time,
    window_applies,
)

NO_RATE_IN_FORCE: tuple[str, None] = ("none", None)
CONSUMPTION_BLOCK_PREFIX = "block_"


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


def _charge_parts(
    charge: TariffDemandCharge, day: date, clock: TariffClock
) -> list[tuple[datetime, datetime]]:
    """The spans `charge` covers on `day` of `clock`, as instants, each inside that date.

    window_applies as intervals: the date alone decides its parts of an overnight
    window, so they never cross midnight. start == end is the whole day.
    test_matches_is_in_demand_window_every_minute guards against the two drifting apart.
    """
    if not is_season_match(charge.months, day.month):
        return []
    if not day_applies(charge.days, charge.public_holidays, day, clock.state):
        return []
    ws, we = parse_time(charge.start), parse_time(charge.end)
    midnight = time(0, 0)
    next_midnight = clock.instant(day + timedelta(days=1), midnight)
    if ws == we:
        return [(clock.instant(day, midnight), next_midnight)]
    if ws < we:
        return [(clock.instant(day, ws), clock.instant(day, we))]
    return [
        (clock.instant(day, midnight), clock.instant(day, we)),
        (clock.instant(day, ws), next_midnight),
    ]


def merge_demand_stretches(
    parts: list[tuple[datetime, datetime, float]], zone: ZoneInfo
) -> list[tuple[datetime, datetime, float]]:
    """Sweep (start, end, rate) parts into sorted, non-overlapping stretches.

    The highest rate covering a stretch wins, and neighbours merge only at an equal
    rate. Sweeps in UTC, since datetimes sharing a zone compare by wall clock across
    a daylight saving change. The stretches come back in `zone`.
    """
    spans = [(s.astimezone(UTC), e.astimezone(UTC), rate) for s, e, rate in parts if s < e]
    boundaries = sorted({moment for s, e, _ in spans for moment in (s, e)})
    stretches: list[tuple[datetime, datetime, float]] = []
    for lo, hi in zip(boundaries, boundaries[1:]):
        covering = [rate for s, e, rate in spans if s <= lo and hi <= e]
        if not covering:
            continue
        rate = max(covering)
        if stretches and stretches[-1][1] == lo and stretches[-1][2] == rate:
            stretches[-1] = (stretches[-1][0], hi, rate)
        else:
            stretches.append((lo, hi, rate))
    return [(s.astimezone(zone), e.astimezone(zone), rate) for s, e, rate in stretches]


def demand_windows(
    tariff: Tariff, start: datetime, end: datetime
) -> list[tuple[datetime, datetime, float]]:
    """Each demand charge's windows within [start, end), with the rate of each stretch.

    Dates run on the tariff's clock. Windows are half-open, clipped to the range,
    sorted and merged by merge_demand_stretches, as aware datetimes in the DNSP's
    local offset.
    """
    clock = clock_for(tariff)
    lo, hi = start.astimezone(UTC), end.astimezone(UTC)
    # Every part lies inside its own date, so the two end dates bound the range.
    day = clock.wall(lo).date()
    last = clock.wall(hi).date()
    parts: list[tuple[datetime, datetime, float]] = []
    while day <= last:
        for charge in tariff.demand_charges:
            for s, e in _charge_parts(charge, day, clock):
                parts.append((max(s, lo), min(e, hi), charge.rate))
        day += timedelta(days=1)
    return merge_demand_stretches(parts, clock.zone)


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
