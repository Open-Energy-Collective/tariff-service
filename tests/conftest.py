"""Test fixtures — uses a temporary file-based SQLite database."""

import json
import os
import tempfile

import pytest

# Set test database BEFORE importing app
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.tariff import Dnsp, Tariff, TariffDemand, TariffRate  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables and seed test data before each test, drop after."""
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # ── Energex (year-round peak, simple TOU) ──
        energex = Dnsp(code="energex", name="Energex", state="QLD", timezone="Australia/Brisbane")
        session.add(energex)
        session.flush()

        tariff = Tariff(
            dnsp_id=energex.id,
            code="T12A",
            name="Residential Demand",
            tariff_type="tou_demand",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=1.1282,
        )
        session.add(tariff)
        session.flush()

        demand = TariffDemand(
            tariff_id=tariff.id,
            rate=7.434,
            window_start="16:00",
            window_end="21:00",
            measurement_method="30min_avg",
            days="all",
            season_months=None,
        )
        session.add(demand)

        rates = [
            TariffRate(
                tariff_id=tariff.id,
                period_name="peak",
                rate=0.02367,
                start_time="16:00",
                end_time="21:00",
                days="all",
                season="all",
            ),
            TariffRate(
                tariff_id=tariff.id,
                period_name="shoulder",
                rate=0.04868,
                start_time="21:00",
                end_time="00:00",
                days="all",
                season="all",
            ),
            TariffRate(
                tariff_id=tariff.id,
                period_name="off_peak",
                rate=0.00476,
                start_time="00:00",
                end_time="16:00",
                days="all",
                season="all",
            ),
        ]
        for r in rates:
            session.add(r)

        # ── Ausgrid (seasonal peak — only Jun-Aug & Nov-Mar) ──
        ausgrid = Dnsp(
            code="ausgrid", name="Ausgrid", state="NSW", timezone="Australia/Sydney"
        )
        session.add(ausgrid)
        session.flush()

        ausgrid_tou = Tariff(
            dnsp_id=ausgrid.id,
            code="EA025",
            name="Residential ToU",
            tariff_type="tou",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=0.63233,
        )
        session.add(ausgrid_tou)
        session.flush()

        high_season = json.dumps([1, 2, 3, 6, 7, 8, 11, 12])
        session.add(
            TariffRate(
                tariff_id=ausgrid_tou.id,
                period_name="peak",
                rate=0.32516,
                start_time="15:00",
                end_time="21:00",
                days="all",
                season="high",
                season_months=high_season,
            )
        )
        session.add(
            TariffRate(
                tariff_id=ausgrid_tou.id,
                period_name="off_peak",
                rate=0.05357,
                start_time="00:00",
                end_time="00:00",
                days="all",
                season="all",
            )
        )

        # Ausgrid demand tariff (seasonal)
        ausgrid_demand = Tariff(
            dnsp_id=ausgrid.id,
            code="EA116",
            name="Residential Demand",
            tariff_type="tou_demand",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=0.67005,
        )
        session.add(ausgrid_demand)
        session.flush()

        session.add(
            TariffDemand(
                tariff_id=ausgrid_demand.id,
                rate=11.8455,
                window_start="15:00",
                window_end="21:00",
                measurement_method="30min_max",
                days="all",
                season_months=high_season,
            )
        )
        session.add(
            TariffRate(
                tariff_id=ausgrid_demand.id,
                period_name="peak",
                rate=0.02806,
                start_time="15:00",
                end_time="21:00",
                days="all",
                season="high",
                season_months=high_season,
            )
        )
        session.add(
            TariffRate(
                tariff_id=ausgrid_demand.id,
                period_name="off_peak",
                rate=0.02806,
                start_time="00:00",
                end_time="00:00",
                days="all",
                season="all",
            )
        )

        # ── SA Power Networks (solar sponge, peak 17:00-21:00) ──
        sapn = Dnsp(
            code="sapn", name="SA Power Networks", state="SA", timezone="Australia/Adelaide"
        )
        session.add(sapn)
        session.flush()

        sapn_tou = Tariff(
            dnsp_id=sapn.id,
            code="RTOU",
            name="Residential Time of Use",
            tariff_type="tou",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=0.6553,
        )
        session.add(sapn_tou)
        session.flush()

        session.add(
            TariffRate(
                tariff_id=sapn_tou.id,
                period_name="peak",
                rate=0.2133,
                start_time="17:00",
                end_time="21:00",
                days="all",
                season="all",
            )
        )
        session.add(
            TariffRate(
                tariff_id=sapn_tou.id,
                period_name="solar_sponge",
                rate=0.0535,
                start_time="10:00",
                end_time="15:00",
                days="all",
                season="all",
            )
        )
        session.add(
            TariffRate(
                tariff_id=sapn_tou.id,
                period_name="shoulder",
                rate=0.1067,
                start_time="06:00",
                end_time="10:00",
                days="all",
                season="all",
            )
        )
        session.add(
            TariffRate(
                tariff_id=sapn_tou.id,
                period_name="off_peak",
                rate=0.0535,
                start_time="01:00",
                end_time="06:00",
                days="all",
                season="all",
            )
        )

        session.commit()

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as c:
        yield c
