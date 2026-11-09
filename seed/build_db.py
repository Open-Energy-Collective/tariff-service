"""Build SQLite database from seed JSON files.

Usage: python seed/build_db.py

Reads all JSON files in seed/ directory and creates data/tariffs.db.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.config import DATA_DIR, DB_PATH
from app.database import Base, engine
from app.models.tariff import Dnsp, Tariff, TariffDemandCharge, TariffExport, TariffRate
from app.services.public_holidays import is_known_state

SEED_DIR = Path(__file__).resolve().parent
TIME_BASES = ("local", "standard")
DAY_TYPES = ("all", "weekdays", "weekends")
PUBLIC_HOLIDAY_TREATMENTS = ("included", "excluded")


def load_seed_files() -> list[dict]:
    """Load all JSON seed files."""
    data = []
    for f in sorted(SEED_DIR.glob("*.json")):
        print(f"  Loading {f.name}")
        with open(f) as fp:
            data.append(json.load(fp))
    return data


def validate_tariff_versions(seed_files: list[dict]) -> None:
    """Raise ValueError unless each version ends on the date the next one starts.

    A tariff's last version must have no end date, so prices never expire by accident
    while new versions are loaded by hand.
    """
    versions: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for data in seed_files:
        for tariff in data.get("tariffs", []):
            versions[(tariff["dnsp"], tariff["code"])].append(tariff)

    for (dnsp, code), rows in versions.items():
        rows.sort(key=lambda row: row["effective_from"])
        for row, following in zip(rows, [*rows[1:], None]):
            start, end = row["effective_from"], row.get("effective_to")
            if end is not None and end <= start:
                raise ValueError(f"{dnsp}/{code}: version from {start} ends on {end}")
            if following is None and end is not None:
                raise ValueError(f"{dnsp}/{code}: last version from {start} has end date {end}")
            if following is not None and end != following["effective_from"]:
                raise ValueError(
                    f"{dnsp}/{code}: version from {start} must end on "
                    f"{following['effective_from']}, the next version's start, not {end}"
                )


def validate_tariff_fields(seed_files: list[dict]) -> None:
    """Raise ValueError unless each tariff's time basis, windows and demand units are usable."""
    for data in seed_files:
        for dnsp in data.get("dnsps", []):
            if not is_known_state(dnsp["state"]):
                raise ValueError(f"{dnsp['code']}: unknown state {dnsp['state']!r}")
        for tariff in data.get("tariffs", []):
            name = f"{tariff['dnsp']}/{tariff['code']}"
            if tariff.get("time_basis") not in TIME_BASES:
                raise ValueError(f"{name}: time_basis must be one of {TIME_BASES}")

            charges = tariff.get("demand_charges", [])
            exports = tariff.get("exports", [])
            for row in [*tariff.get("rates", []), *charges, *exports]:
                days = row.get("days", "all")
                if days not in DAY_TYPES:
                    raise ValueError(f"{name}: unrecognised days value {days!r}")
                if days != "all" and row.get("public_holidays") not in PUBLIC_HOLIDAY_TREATMENTS:
                    raise ValueError(
                        f"{name}: a {days} window needs public_holidays, one of "
                        f"{PUBLIC_HOLIDAY_TREATMENTS}"
                    )

            units = {charge.get("unit") for charge in charges}
            if len(units) > 1:
                raise ValueError(f"{name}: demand charges mix units {sorted(map(str, units))}")

            for export in exports:
                if (
                    export.get("free_threshold_kwh") is not None
                    and export.get("free_threshold_period") is None
                ):
                    raise ValueError(f"{name}: free threshold has no free_threshold_period")


def populate(session: Session, seed_files: list[dict]) -> None:
    """Add every DNSP, tariff, rate, demand charge and export in seed_files, then commit."""
    validate_tariff_versions(seed_files)
    validate_tariff_fields(seed_files)
    dnsp_map: dict[str, Dnsp] = {}

    for data in seed_files:
        # Create DNSPs
        for dnsp_data in data.get("dnsps", []):
            if dnsp_data["code"] not in dnsp_map:
                dnsp = Dnsp(
                    code=dnsp_data["code"],
                    name=dnsp_data["name"],
                    state=dnsp_data["state"],
                    timezone=dnsp_data["timezone"],
                )
                session.add(dnsp)
                session.flush()
                dnsp_map[dnsp_data["code"]] = dnsp
                print(f"  + DNSP: {dnsp.name} ({dnsp.code})")

        # Create Tariffs
        for tariff_data in data.get("tariffs", []):
            dnsp = dnsp_map[tariff_data["dnsp"]]
            tariff = Tariff(
                dnsp_id=dnsp.id,
                code=tariff_data["code"],
                name=tariff_data["name"],
                tariff_type=tariff_data["tariff_type"],
                effective_from=tariff_data["effective_from"],
                effective_to=tariff_data.get("effective_to"),
                time_basis=tariff_data["time_basis"],
                prices_expected_until=tariff_data.get("prices_expected_until"),
                daily_supply_charge=tariff_data.get("daily_supply_charge"),
                source_url=tariff_data.get("source_url"),
                last_verified=tariff_data.get("last_verified"),
                verified_by=tariff_data.get("verified_by"),
            )
            session.add(tariff)
            session.flush()

            # Demand charges
            for charge_data in tariff_data.get("demand_charges", []):
                charge = TariffDemandCharge(
                    tariff_id=tariff.id,
                    period=charge_data["period"],
                    rate=charge_data["rate"],
                    unit=charge_data["unit"],
                    start=charge_data["start"],
                    end=charge_data["end"],
                    days=charge_data.get("days", "all"),
                    public_holidays=charge_data.get("public_holidays"),
                    months=json.dumps(charge_data["months"]) if charge_data.get("months") else None,
                    measurement_method=charge_data["measurement_method"],
                    peak_period=charge_data["peak_period"],
                )
                session.add(charge)

            # Rates
            for rate_data in tariff_data.get("rates", []):
                rate = TariffRate(
                    tariff_id=tariff.id,
                    period_name=rate_data["period_name"],
                    rate=rate_data["rate"],
                    start_time=rate_data["start_time"],
                    end_time=rate_data["end_time"],
                    days=rate_data.get("days", "all"),
                    public_holidays=rate_data.get("public_holidays"),
                    season=rate_data.get("season", "all"),
                    season_months=(
                        json.dumps(rate_data["season_months"])
                        if rate_data.get("season_months")
                        else None
                    ),
                )
                session.add(rate)

            # Exports
            for export_data in tariff_data.get("exports", []):
                # Guard against the 2026-08-10 bug class: seed data
                # authored in the same shape as "rates" (period_name/
                # rate/start_time/end_time) instead of this model's real
                # credit_rate/charge_rate columns silently produced an
                # all-null row -- every field access below is a .get()
                # with no required-key check, so a shape mismatch never
                # raised, it just lost the data. Fail loudly instead.
                if "credit_rate" not in export_data and "charge_rate" not in export_data:
                    raise ValueError(
                        f"Tariff {tariff_data['dnsp']}/{tariff_data['code']}: "
                        f"exports entry has neither 'credit_rate' nor 'charge_rate' "
                        f"({list(export_data.keys())}) -- wrong shape, see "
                        f"TariffExportResponse for the expected fields."
                    )
                export = TariffExport(
                    tariff_id=tariff.id,
                    credit_rate=export_data.get("credit_rate"),
                    credit_window_start=export_data.get("credit_window_start"),
                    credit_window_end=export_data.get("credit_window_end"),
                    credit_season_months=(
                        json.dumps(export_data["credit_season_months"])
                        if export_data.get("credit_season_months")
                        else None
                    ),
                    charge_rate=export_data.get("charge_rate"),
                    charge_window_start=export_data.get("charge_window_start"),
                    charge_window_end=export_data.get("charge_window_end"),
                    free_threshold_kwh=export_data.get("free_threshold_kwh"),
                    free_threshold_period=export_data.get("free_threshold_period"),
                    free_threshold_rollover=export_data.get("free_threshold_rollover"),
                    days=export_data.get("days", "all"),
                    public_holidays=export_data.get("public_holidays"),
                )
                session.add(export)

            print(f"  + Tariff: {tariff.code} ({tariff.name})")

    session.commit()


def build_database() -> None:
    """Create SQLite database from seed data."""
    # Load and check the seed first: a failed build keeps the existing database
    seed_files = load_seed_files()
    validate_tariff_versions(seed_files)
    validate_tariff_fields(seed_files)

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"  Removed old {DB_PATH.name}")

    # Create tables
    Base.metadata.create_all(engine)
    print(f"  Created {DB_PATH.name}")

    with Session(engine) as session:
        populate(session, seed_files)
        print(f"\n✓ Database built: {DB_PATH} ({DB_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    print("Building tariff database from seed files...")
    build_database()
