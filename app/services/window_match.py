"""One routine deciding whether a tariff window applies at an instant.

Energy, demand and export windows all match here: on the tariff's clock, with the
DNSP state's public holidays.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.public_holidays import is_public_holiday

WEEKDAYS_END = 5  # date.weekday() below this is Monday to Friday


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


def _standard_offset(moment: datetime) -> timedelta:
    """The zone's offset at `moment` with daylight saving removed."""
    return moment.utcoffset() - moment.dst()


@dataclass(frozen=True)
class TariffClock:
    """The clock a tariff's windows are written on. `basis` is local or standard."""

    zone: ZoneInfo
    basis: str
    state: str

    def __post_init__(self) -> None:
        if self.basis not in ("local", "standard"):
            raise ValueError(f"unknown time basis: {self.basis!r}")

    def wall(self, instant: datetime) -> datetime:
        """The naive time this clock shows at `instant`, which must be aware."""
        if instant.utcoffset() is None:
            raise ValueError("instant must be timezone aware")
        zoned = instant.astimezone(self.zone)
        if self.basis == "local":
            return zoned.replace(tzinfo=None)
        return (instant.astimezone(UTC) + _standard_offset(zoned)).replace(tzinfo=None)

    def instant(self, day: date, t: time) -> datetime:
        """The aware UTC instant at which this clock shows `t` on `day`."""
        zoned = datetime.combine(day, t, tzinfo=self.zone)
        if self.basis == "local":
            return zoned.astimezone(UTC)
        fixed = timezone(_standard_offset(zoned))
        return datetime.combine(day, t, tzinfo=fixed).astimezone(UTC)


def day_applies(days: str, public_holidays: str | None, day: date, state: str) -> bool:
    """Whether a window with this `days` and holiday marker runs on `day` in `state`.

    `days` is all, weekdays or weekends; anything else raises ValueError. all runs
    every day. On a public holiday a marker of included or excluded decides;
    otherwise `days` decides by weekday.
    """
    if days not in ("all", "weekdays", "weekends"):
        raise ValueError(f"unknown days value: {days!r}")
    if days == "all":
        return True
    if public_holidays in ("included", "excluded") and is_public_holiday(state, day):
        return public_holidays == "included"
    is_weekday = day.weekday() < WEEKDAYS_END
    return is_weekday if days == "weekdays" else not is_weekday


def window_applies(
    start: str,
    end: str,
    days: str,
    public_holidays: str | None,
    months: list[int] | None,
    clock: TariffClock,
    instant: datetime,
) -> bool:
    """Whether the window applies at `instant`, judged on `clock`.

    Date, weekday, month and holiday come from the clock's wall time, so each
    date of an overnight window is judged alone.
    """
    wall = clock.wall(instant)
    if not day_applies(days, public_holidays, wall.date(), clock.state):
        return False
    if months is not None and wall.month not in months:
        return False
    return is_in_time_window(wall.time(), parse_time(start), parse_time(end))
