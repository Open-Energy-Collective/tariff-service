"""Test fixtures — uses a temporary file-based SQLite database."""

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
        dnsp = Dnsp(code="energex", name="Energex", state="QLD", timezone="Australia/Brisbane")
        session.add(dnsp)
        session.flush()

        tariff = Tariff(
            dnsp_id=dnsp.id,
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

        session.commit()

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as c:
        yield c
