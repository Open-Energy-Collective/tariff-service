"""Tariff data access service."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.tariff import Dnsp, Tariff
from app.services.rate_calculator import demand_windows


def get_all_dnsps(db: Session) -> list[Dnsp]:
    """Return all DNSPs."""
    return list(db.execute(select(Dnsp).order_by(Dnsp.name)).scalars().all())


def get_tariffs_for_dnsp(db: Session, dnsp_code: str) -> list[Tariff]:
    """Return all active tariffs for a given DNSP code."""
    today = date.today().isoformat()
    return list(
        db.execute(
            select(Tariff)
            .join(Dnsp)
            .where(Dnsp.code == dnsp_code)
            .where(Tariff.effective_from <= today)
            .where((Tariff.effective_to.is_(None)) | (Tariff.effective_to > today))
            .order_by(Tariff.code)
        )
        .scalars()
        .all()
    )


def get_dnsp(db: Session, dnsp_code: str) -> Dnsp | None:
    """Return one DNSP by code."""
    return db.execute(select(Dnsp).where(Dnsp.code == dnsp_code)).scalars().first()


def get_tariff_detail(
    db: Session, dnsp_code: str, tariff_code: str, on: date | None = None
) -> Tariff | None:
    """Return the tariff version in force on a date (default today), relationships loaded."""
    day = (on or date.today()).isoformat()
    result = db.execute(
        select(Tariff)
        .join(Dnsp)
        .options(
            joinedload(Tariff.demand),
            joinedload(Tariff.rates),
            joinedload(Tariff.exports),
            joinedload(Tariff.dnsp),
        )
        .where(Dnsp.code == dnsp_code)
        .where(Tariff.code == tariff_code)
        .where(Tariff.effective_from <= day)
        .where((Tariff.effective_to.is_(None)) | (Tariff.effective_to > day))
        .order_by(Tariff.effective_from.desc())
    )
    return result.scalars().first()


def demand_windows_in_force(
    db: Session, dnsp_code: str, tariff_code: str, tz: ZoneInfo, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]] | None:
    """Demand windows over [start, end), each local date using the version in force that day.

    Dates with no version in force have no windows. Windows that touch across a version
    boundary are merged. None when no date in the range has a version in force.
    """
    lo, hi = start.astimezone(UTC), end.astimezone(UTC)
    last = hi.astimezone(tz).date()
    day = lo.astimezone(tz).date()
    any_version = False
    spans: list[tuple[datetime, datetime]] = []
    while day <= last:
        next_day = day + timedelta(days=1)
        version = get_tariff_detail(db, dnsp_code, tariff_code, on=day)
        if version is not None:
            day_start = datetime.combine(day, time(0, 0), tzinfo=tz).astimezone(UTC)
            day_end = datetime.combine(next_day, time(0, 0), tzinfo=tz).astimezone(UTC)
            s, e = max(lo, day_start), min(hi, day_end)
            if s < e:
                any_version = True
                for window_start, window_end in demand_windows(version.demand, tz, s, e):
                    window_start = window_start.astimezone(UTC)
                    window_end = window_end.astimezone(UTC)
                    if spans and window_start <= spans[-1][1]:
                        spans[-1] = (spans[-1][0], max(spans[-1][1], window_end))
                    else:
                        spans.append((window_start, window_end))
        day = next_day
    if not any_version:
        return None
    return [(s.astimezone(tz), e.astimezone(tz)) for s, e in spans]


def get_tariff_history(db: Session, dnsp_code: str, tariff_code: str) -> list[Tariff]:
    """Return all versions of a tariff (newest first)."""
    return list(
        db.execute(
            select(Tariff)
            .join(Dnsp)
            .options(
                joinedload(Tariff.demand),
                joinedload(Tariff.rates),
                joinedload(Tariff.exports),
            )
            .where(Dnsp.code == dnsp_code)
            .where(Tariff.code == tariff_code)
            .order_by(Tariff.effective_from.desc())
        )
        .scalars()
        .unique()
        .all()
    )
