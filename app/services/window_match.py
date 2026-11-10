"""One routine deciding whether a tariff window applies at an instant.

Energy, demand and export windows all match here: on the tariff's clock, with the
DNSP state's public holidays.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.tariff import Tariff
from app.services.public_holidays import is_public_holiday

WEEKDAYS_END = 5  # date.weekday() below this is Monday to Friday
# Wider than any UTC offset, so it bounds the instants a wall time can fall on.
_OFFSET_BOUND = timedelta(hours=15)


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

    def offset(self, instant: datetime) -> timedelta:
        """How far this clock runs ahead of UTC at `instant`, which must be aware."""
        zoned = instant.astimezone(self.zone)
        return zoned.utcoffset() if self.basis == "local" else _standard_offset(zoned)

    def wall(self, instant: datetime) -> datetime:
        """The naive time this clock shows at `instant`, which must be aware."""
        if instant.utcoffset() is None:
            raise ValueError("instant must be timezone aware")
        return (instant.astimezone(UTC) + self.offset(instant)).replace(tzinfo=None)

    def spans(self, day: date, start: time, end: time | None) -> list[tuple[datetime, datetime]]:
        """Every instant at which wall() reads `day` at a time in [start, end), as UTC spans.

        `end` None is the next midnight. This is wall() inverted, so a window matched
        here as intervals matches exactly the instants window_applies accepts: a time
        the clock skips at a daylight saving start yields no instant, and a time it
        repeats at the end yields both. The spans are sorted, disjoint and half-open.
        """
        lo = datetime.combine(day, start)
        hi = datetime.combine(day + timedelta(days=1) if end is None else day, end or time(0))
        found: list[tuple[datetime, datetime]] = []
        for p0, p1, off in self._pieces(lo - _OFFSET_BOUND, hi + _OFFSET_BOUND):
            s, e = max(p0, lo - off), min(p1, hi - off)
            if s >= e:
                continue
            if found and found[-1][1] == s:
                found[-1] = (found[-1][0], e)
            else:
                found.append((s, e))
        return [(s.replace(tzinfo=UTC), e.replace(tzinfo=UTC)) for s, e in found]

    def _pieces(
        self, lo: datetime, hi: datetime
    ) -> list[tuple[datetime, datetime, timedelta]]:
        """Naive UTC [lo, hi) cut where offset() changes, each piece with its offset.

        Probes hourly and bisects to the microsecond, so it assumes the offset changes
        at most once in any hour, as in every Australian zone.
        """

        def off(u: datetime) -> timedelta:
            return self.offset(u.replace(tzinfo=UTC))

        pieces = []
        p0, o0, t = lo, off(lo), lo
        while t < hi:
            probe = min(t + timedelta(hours=1), hi)
            if off(probe) == o0:
                t = probe
                continue
            a, b = t, probe  # off(a) == o0 != off(b)
            while b - a > timedelta(microseconds=1):
                mid = a + (b - a) // 2
                a, b = (mid, b) if off(mid) == o0 else (a, mid)
            pieces.append((p0, b, o0))
            p0, o0, t = b, off(b), b
        pieces.append((p0, hi, o0))
        return pieces

    def instant(self, day: date, t: time) -> datetime:
        """The aware UTC instant at which this clock shows `t` on `day`."""
        zoned = datetime.combine(day, t, tzinfo=self.zone)
        if self.basis == "local":
            return zoned.astimezone(UTC)
        fixed = timezone(_standard_offset(zoned))
        return datetime.combine(day, t, tzinfo=fixed).astimezone(UTC)


def clock_for(tariff: Tariff) -> TariffClock:
    """The clock this tariff's windows are written on, in its DNSP's zone and state."""
    return TariffClock(
        zone=ZoneInfo(tariff.dnsp.timezone), basis=tariff.time_basis, state=tariff.dnsp.state
    )


def day_applies(days: str, public_holidays: str | None, day: date, state: str) -> bool:
    """Whether a window with this `days` and holiday marker runs on `day` in `state`.

    `days` is all, weekdays or weekends; anything else raises ValueError. all runs
    every day. On a public holiday, excluded switches the window off and included
    switches a weekends window on; every other case follows the weekday rule, so a
    weekdays window stays off on a weekend holiday.
    """
    if days not in ("all", "weekdays", "weekends"):
        raise ValueError(f"unknown days value: {days!r}")
    if days == "all":
        return True
    if public_holidays in ("included", "excluded") and is_public_holiday(state, day):
        if public_holidays == "excluded":
            return False
        if days == "weekends":
            return True
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
