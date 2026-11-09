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
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.tariff import Dnsp, Tariff, TariffDemandCharge, TariffRate  # noqa: E402
from seed.build_db import load_seed_files, populate  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables and synthetic test data before each test, drop after.

    These rows exercise API behaviour only and are not checked against any source.
    Seed correctness is tested on the real seed: test_seed_data.py,
    test_seed_integrity.py and test_demand_tariffs.py.
    """
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

        demand = TariffDemandCharge(
            period="peak",
            unit="kW",
            peak_period="month",
            tariff_id=tariff.id,
            rate=7.434,
            start="16:00",
            end="21:00",
            measurement_method="30min_avg",
            days="all",
            months=None,
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
            TariffDemandCharge(
                period="peak",
                unit="kW",
                peak_period="month",
                tariff_id=ausgrid_demand.id,
                rate=11.8455,
                start="15:00",
                end="21:00",
                measurement_method="30min_max",
                days="all",
                months=high_season,
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

        # Ausgrid demand tariff with an all-day (00:00-00:00) demand window —
        # matches the real Jemena A230 / Energex 8300 / AusNet NASN12 convention
        # ("applies at all other times"), regression coverage for the
        # division-by-zero this used to cause in calculate_demand_surcharge.
        ausgrid_alldaydemand = Tariff(
            dnsp_id=ausgrid.id,
            code="EA117",
            name="Residential All-Day Demand",
            tariff_type="tou_demand",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=0.6,
        )
        session.add(ausgrid_alldaydemand)
        session.flush()

        session.add(
            TariffDemandCharge(
                period="anytime",
                unit="kW",
                peak_period="month",
                tariff_id=ausgrid_alldaydemand.id,
                rate=11.473,
                start="00:00",
                end="00:00",
                measurement_method="monthly_peak",
                days="all",
                months=None,
            )
        )
        session.add(
            TariffRate(
                tariff_id=ausgrid_alldaydemand.id,
                period_name="anytime",
                rate=0.03,
                start_time="00:00",
                end_time="00:00",
                days="all",
                season="all",
            )
        )

        # ── SA Power Networks (solar sponge, off-peak, peak all other times) ──
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

        # The structure of seed/sapn.json RTOU: peak is every hour not listed.
        for period, rate, start, end in [
            ("off_peak", 0.1067, "00:00", "06:00"),
            ("solar_sponge", 0.0535, "10:00", "16:00"),
            ("peak", 0.2133, "00:00", "00:00"),
        ]:
            session.add(
                TariffRate(
                    tariff_id=sapn_tou.id,
                    period_name=period,
                    rate=rate,
                    start_time=start,
                    end_time=end,
                    days="all",
                    season="all",
                )
            )

        session.commit()

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    """Create a test client with rate limiting disabled (TestClient shares one source IP)."""
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c
    app.state.limiter.enabled = True


@pytest.fixture(scope="session")
def seed_engine(tmp_path_factory):
    """The real seed data (seed/build_db.py), built once into its own SQLite file."""
    seed_db = create_engine(
        f"sqlite:///{tmp_path_factory.mktemp('seed') / 'tariffs.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(seed_db)
    with Session(seed_db) as session:
        populate(session, load_seed_files())
    return seed_db


@pytest.fixture
def seed_session(seed_engine):
    """A database session on the real seed data."""
    with Session(seed_engine) as session:
        yield session


@pytest.fixture
def seed_client(seed_engine):
    """A test client whose API reads the real seed data, not the fixtures above."""
    seed_session = sessionmaker(bind=seed_engine)

    def _seed_db():
        db = seed_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _seed_db
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c
    app.state.limiter.enabled = True
    del app.dependency_overrides[get_db]
