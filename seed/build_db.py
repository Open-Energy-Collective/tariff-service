"""Build SQLite database from seed JSON files.

Usage: python seed/build_db.py

Reads all JSON files in seed/ directory and creates data/tariffs.db.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DB_PATH
from app.database import Base, engine
from app.models.tariff import Dnsp, Tariff, TariffDemand, TariffExport, TariffRate
from sqlalchemy.orm import Session


SEED_DIR = Path(__file__).resolve().parent


def load_seed_files() -> list[dict]:
    """Load all JSON seed files."""
    data = []
    for f in sorted(SEED_DIR.glob("*.json")):
        print(f"  Loading {f.name}")
        with open(f) as fp:
            data.append(json.load(fp))
    return data


def build_database() -> None:
    """Create SQLite database from seed data."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"  Removed old {DB_PATH.name}")

    # Create tables
    Base.metadata.create_all(engine)
    print(f"  Created {DB_PATH.name}")

    # Load seed data
    seed_files = load_seed_files()

    with Session(engine) as session:
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
                    daily_supply_charge=tariff_data.get("daily_supply_charge"),
                    source_url=tariff_data.get("source_url"),
                    last_verified=tariff_data.get("last_verified"),
                    verified_by=tariff_data.get("verified_by"),
                )
                session.add(tariff)
                session.flush()

                # Demand
                if demand_data := tariff_data.get("demand"):
                    demand = TariffDemand(
                        tariff_id=tariff.id,
                        rate=demand_data["rate"],
                        window_start=demand_data["window_start"],
                        window_end=demand_data["window_end"],
                        measurement_method=demand_data["measurement_method"],
                        days=demand_data.get("days", "all"),
                        season_months=(
                            json.dumps(demand_data["season_months"])
                            if demand_data.get("season_months")
                            else None
                        ),
                    )
                    session.add(demand)

                # Rates
                for rate_data in tariff_data.get("rates", []):
                    rate = TariffRate(
                        tariff_id=tariff.id,
                        period_name=rate_data["period_name"],
                        rate=rate_data["rate"],
                        start_time=rate_data["start_time"],
                        end_time=rate_data["end_time"],
                        days=rate_data.get("days", "all"),
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
                        days=export_data.get("days", "all"),
                    )
                    session.add(export)

                print(f"  + Tariff: {tariff.code} ({tariff.name})")

        session.commit()
        print(f"\n✓ Database built: {DB_PATH} ({DB_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    print("Building tariff database from seed files...")
    build_database()
