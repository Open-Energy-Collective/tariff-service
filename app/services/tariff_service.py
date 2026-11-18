"""Tariff data access service."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.tariff import Dnsp, Tariff, TariffDemandCharge
from app.services.rate_calculator import (
    charge_windows,
    demand_charge_order,
    join_spans,
    merge_demand_stretches,
)


def get_all_dnsps(db: Session) -> list[Dnsp]:
    """Return all DNSPs."""
    return list(db.execute(select(Dnsp).order_by(Dnsp.name)).scalars().all())


def get_tariffs_for_dnsp(db: Session, dnsp_code: str) -> list[Tariff]:
    """Return the version in force today of each tariff for a DNSP; the newest start wins."""
    today = date.today().isoformat()
    in_force = (
        db.execute(
            select(Tariff)
            .join(Dnsp)
            .where(Dnsp.code == dnsp_code)
            .where(Tariff.effective_from <= today)
            .where((Tariff.effective_to.is_(None)) | (Tariff.effective_to > today))
            .order_by(Tariff.code, Tariff.effective_from.desc())
        )
        .scalars()
        .all()
    )
    return list({tariff.code: tariff for tariff in reversed(in_force)}.values())[::-1]


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
            joinedload(Tariff.demand_charges),
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


def merge_charge_windows(
    per_charge: list[tuple[TariffDemandCharge, list[tuple[datetime, datetime]]]], tz: ZoneInfo
) -> list[tuple[datetime, datetime, float]]:
    """Per-charge windows merged into rated stretches, as `/calculate/demand-windows` `windows`.

    The higher rate takes an overlap; neighbours merge at an equal rate, across a
    version boundary too.
    """
    return merge_demand_stretches(
        [(s, e, charge.rate) for charge, spans in per_charge for s, e in spans], tz
    )


def demand_windows_in_force(
    db: Session, dnsp_code: str, tariff_code: str, tz: ZoneInfo, start: datetime, end: datetime
) -> list[tuple[datetime, datetime, float]] | None:
    """Demand windows over [start, end), each local date using the version in force that day.

    merge_charge_windows over demand_charge_windows_in_force, the path the endpoint
    uses. None when any date in the range has no version in force.
    """
    per_charge = demand_charge_windows_in_force(db, dnsp_code, tariff_code, tz, start, end)
    return None if per_charge is None else merge_charge_windows(per_charge, tz)


def _charge_key(charge: TariffDemandCharge) -> tuple:
    """The published fields of a demand charge: equal keys are the same charge."""
    return (
        charge.period, charge.rate, charge.unit, charge.start, charge.end, charge.days,
        charge.public_holidays, charge.months, charge.measurement_method, charge.peak_period,
    )


def demand_charge_windows_in_force(
    db: Session, dnsp_code: str, tariff_code: str, tz: ZoneInfo, start: datetime, end: datetime
) -> list[tuple[TariffDemandCharge, list[tuple[datetime, datetime]]]] | None:
    """Each demand charge with its own windows over [start, end), by the version in force.

    Each local date uses the version in force that day. A charge whose published
    fields are the same in two versions is one entry; one that changes is an entry
    per version. Entries follow demand_charge_order, then their first window.
    None when any date in the range has no version in force.
    """
    lo, hi = start.astimezone(UTC), end.astimezone(UTC)
    last = hi.astimezone(tz).date()
    day = lo.astimezone(tz).date()
    entries: dict[tuple, tuple[TariffDemandCharge, list[tuple[datetime, datetime]]]] = {}
    while day <= last:
        next_day = day + timedelta(days=1)
        day_start = datetime.combine(day, time(0, 0), tzinfo=tz).astimezone(UTC)
        day_end = datetime.combine(next_day, time(0, 0), tzinfo=tz).astimezone(UTC)
        s, e = max(lo, day_start), min(hi, day_end)
        if s < e:
            version = get_tariff_detail(db, dnsp_code, tariff_code, on=day)
            if version is None:
                return None
            for charge, spans in charge_windows(version, s, e):
                entries.setdefault(_charge_key(charge), (charge, []))[1].extend(spans)
        day = next_day
    joined = [(charge, join_spans(spans, tz)) for charge, spans in entries.values()]
    return sorted(
        joined, key=lambda cs: (*demand_charge_order(cs[0]), cs[1][0][0].astimezone(UTC))
    )


def get_tariff_history(db: Session, dnsp_code: str, tariff_code: str) -> list[Tariff]:
    """Return all versions of a tariff (newest first)."""
    return list(
        db.execute(
            select(Tariff)
            .join(Dnsp)
            .options(
                joinedload(Tariff.demand_charges),
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
