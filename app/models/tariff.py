"""SQLAlchemy ORM models for tariff data."""

import json
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Dnsp(Base):
    __tablename__ = "dnsp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(10), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariffs: Mapped[list["Tariff"]] = relationship(back_populates="dnsp", cascade="all, delete")


class Tariff(Base):
    __tablename__ = "tariff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dnsp_id: Mapped[int] = mapped_column(Integer, ForeignKey("dnsp.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tariff_type: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_from: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    effective_to: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_supply_charge: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    dnsp: Mapped["Dnsp"] = relationship(back_populates="tariffs")
    demand: Mapped["TariffDemand | None"] = relationship(
        back_populates="tariff", uselist=False, cascade="all, delete"
    )
    rates: Mapped[list["TariffRate"]] = relationship(
        back_populates="tariff", cascade="all, delete"
    )
    exports: Mapped[list["TariffExport"]] = relationship(
        back_populates="tariff", cascade="all, delete"
    )


class TariffDemand(Base):
    __tablename__ = "tariff_demand"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(Integer, ForeignKey("tariff.id"), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # $/kW/month
    window_start: Mapped[str] = mapped_column(String, nullable=False)  # HH:MM
    window_end: Mapped[str] = mapped_column(String, nullable=False)
    measurement_method: Mapped[str] = mapped_column(String(30), nullable=False)
    days: Mapped[str] = mapped_column(String(20), default="all")
    season_months: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariff: Mapped["Tariff"] = relationship(back_populates="demand")

    @property
    def season_months_list(self) -> list[int] | None:
        if self.season_months is None:
            return None
        return json.loads(self.season_months)


class TariffRate(Base):
    __tablename__ = "tariff_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(Integer, ForeignKey("tariff.id"), nullable=False)
    period_name: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # $/kWh
    start_time: Mapped[str] = mapped_column(String, nullable=False)
    end_time: Mapped[str] = mapped_column(String, nullable=False)
    days: Mapped[str] = mapped_column(String(20), default="all")
    season: Mapped[str] = mapped_column(String(20), default="all")
    season_months: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariff: Mapped["Tariff"] = relationship(back_populates="rates")


class TariffExport(Base):
    __tablename__ = "tariff_export"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(Integer, ForeignKey("tariff.id"), nullable=False)
    credit_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_window_start: Mapped[str | None] = mapped_column(String, nullable=True)
    credit_window_end: Mapped[str | None] = mapped_column(String, nullable=True)
    credit_season_months: Mapped[str | None] = mapped_column(Text, nullable=True)
    charge_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    charge_window_start: Mapped[str | None] = mapped_column(String, nullable=True)
    charge_window_end: Mapped[str | None] = mapped_column(String, nullable=True)
    free_threshold_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    days: Mapped[str] = mapped_column(String(20), default="all")
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariff: Mapped["Tariff"] = relationship(back_populates="exports")
