"""Public holiday lookup by Australian state, backed by the `holidays` package (MIT)."""

from datetime import date
from functools import lru_cache

import holidays


@lru_cache(maxsize=None)
def _holidays_for(state: str, year: int) -> frozenset[date]:
    return frozenset(holidays.country_holidays("AU", subdiv=state, years=year))


def is_known_state(state: str) -> bool:
    """True when the package lists `state` as an AU subdivision."""
    return state in holidays.country_holidays("AU").subdivisions


def is_public_holiday(state: str, day: date) -> bool:
    """True when `day` is a public holiday in `state`. Cached per state and year."""
    return day in _holidays_for(state, day.year)
