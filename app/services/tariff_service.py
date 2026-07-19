"""Tariff data access service."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.tariff import Dnsp, Tariff


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


def get_tariff_detail(db: Session, dnsp_code: str, tariff_code: str) -> Tariff | None:
    """Return full tariff detail (current active version) with all relationships loaded."""
    today = date.today().isoformat()
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
        .where(Tariff.effective_from <= today)
        .where((Tariff.effective_to.is_(None)) | (Tariff.effective_to > today))
        .order_by(Tariff.effective_from.desc())
    )
    return result.scalars().first()


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
