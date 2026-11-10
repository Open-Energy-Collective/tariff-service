"""SQLAlchemy ORM models for tariff data."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
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
    time_basis: Mapped[str] = mapped_column(String(10), nullable=False, default="local")
    prices_expected_until: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO date
    daily_supply_charge: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    dnsp: Mapped["Dnsp"] = relationship(back_populates="tariffs")
    demand_charges: Mapped[list["TariffDemandCharge"]] = relationship(
        back_populates="tariff", cascade="all, delete"
    )
    rates: Mapped[list["TariffRate"]] = relationship(
        back_populates="tariff", cascade="all, delete"
    )
    exports: Mapped[list["TariffExport"]] = relationship(
        back_populates="tariff", cascade="all, delete"
    )

    @property
    def demand(self) -> "TariffDemandCharge | None":
        """The charge with the highest rate, a tie going to the earliest start."""
        return min(self.demand_charges, key=lambda c: (-c.rate, c.start), default=None)


class TariffDemandCharge(Base):
    """One demand charge of a tariff version, one row per charge and season."""

    __tablename__ = "tariff_demand_charge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(Integer, ForeignKey("tariff.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # peak, shoulder, ...
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # per unit per month
    unit: Mapped[str] = mapped_column(String(10), nullable=False)  # kW or kVA
    start: Mapped[str] = mapped_column(String, nullable=False)  # HH:MM
    end: Mapped[str] = mapped_column(String, nullable=False)  # start == end is all day
    days: Mapped[str] = mapped_column(String(20), default="all")
    public_holidays: Mapped[str | None] = mapped_column(String(20), nullable=True)
    months: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array, null all year
    measurement_method: Mapped[str] = mapped_column(String(30), nullable=False)
    peak_period: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariff: Mapped["Tariff"] = relationship(back_populates="demand_charges")


class TariffRate(Base):
    __tablename__ = "tariff_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tariff_id: Mapped[int] = mapped_column(Integer, ForeignKey("tariff.id"), nullable=False)
    period_name: Mapped[str] = mapped_column(String(20), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # $/kWh
    start_time: Mapped[str] = mapped_column(String, nullable=False)
    end_time: Mapped[str] = mapped_column(String, nullable=False)
    days: Mapped[str] = mapped_column(String(20), default="all")
    public_holidays: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    free_threshold_period: Mapped[str | None] = mapped_column(String(10), nullable=True)
    free_threshold_rollover: Mapped[str | None] = mapped_column(String(30), nullable=True)
    days: Mapped[str] = mapped_column(String(20), default="all")
    public_holidays: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    tariff: Mapped["Tariff"] = relationship(back_populates="exports")
