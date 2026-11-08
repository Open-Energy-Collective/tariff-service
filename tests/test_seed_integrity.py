"""The real seed through seed/build_db.py and the API (#51).

1. Every tariff resolves to exactly one rate at every half hour.
2. The API returns what seed/*.json holds, field for field.
3. Each DNSP's time zone is stated here, independently of the seed.
4. Known defects are strict xfails linked to their issue, so a fix reports as XPASS.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.tariff import Dnsp, Tariff, TariffDemand, TariffExport, TariffRate
from app.services.rate_calculator import (
    is_day_match,
    is_in_time_window,
    is_season_match,
    parse_time,
)
from seed.build_db import populate

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

SEED_TARIFFS = [
    tariff
    for path in sorted(SEED_DIR.glob("*.json"))
    for tariff in json.loads(path.read_text())["tariffs"]
]


def tariff_id(tariff: dict) -> str:
    return f"{tariff['dnsp']}-{tariff['code']}"


# ── 1. Every half hour resolves to one rate ──

# No rate matches, or the rate depends on row order. Each is a defect with an issue.
UNRESOLVED = {
    ("ausgrid", "EA029"): "#49: no energy rates seeded",
    ("endeavour", "N90"): "#47: two all-day block rates, the block depends on consumption",
    ("jemena", "A180"): "#48: no rate outside 23:00-07:00",
}


def sweep_params():
    for tariff in SEED_TARIFFS:
        reason = UNRESOLVED.get((tariff["dnsp"], tariff["code"]))
        marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
        yield pytest.param(tariff["dnsp"], tariff["code"], id=tariff_id(tariff), marks=marks)


def sample_days() -> list[datetime]:
    """A Monday, Saturday and Sunday of each month."""
    days = []
    for month in range(1, 13):
        first = datetime(2026, month, 1)
        monday = first + timedelta(days=-first.weekday() % 7)
        days += [monday, monday + timedelta(days=5), monday + timedelta(days=6)]
    return days


def matching_rates(tariff: Tariff, at: datetime) -> list[TariffRate]:
    """The rows that decide the rate at a time: specific windows, else catch-alls."""
    active = [
        r
        for r in tariff.rates
        if is_day_match(r.days, at.weekday()) and is_season_match(r.season_months, at.month)
    ]
    specific = [
        r
        for r in active
        if r.start_time != r.end_time
        and is_in_time_window(at.time(), parse_time(r.start_time), parse_time(r.end_time))
    ]
    return specific or [r for r in active if r.start_time == r.end_time]


@pytest.mark.parametrize(("dnsp", "code"), sweep_params())
def test_every_half_hour_has_exactly_one_rate(seed_engine, dnsp, code):
    with Session(seed_engine) as session:
        tariff = session.execute(
            select(Tariff).join(Dnsp).where(Dnsp.code == dnsp, Tariff.code == code)
        ).scalar_one()
        for day in sample_days():
            for i in range(48):
                at = day + timedelta(minutes=30 * i)
                found = [(r.period_name, r.rate) for r in matching_rates(tariff, at)]
                assert len(found) == 1, f"{at:%a %m-%d %H:%M}: {found}"


# ── 2. The API returns what the seed holds ──


def expected_rate(rate: dict) -> dict:
    return {
        "period": rate["period_name"],
        "rate": rate["rate"],
        "start_time": rate["start_time"],
        "end_time": rate["end_time"],
        "days": rate.get("days", "all"),
        "season": rate.get("season", "all"),
        "season_months": rate.get("season_months") or None,
    }


def expected_demand(demand: dict | None) -> dict | None:
    if demand is None:
        return None
    return {
        "rate": demand["rate"],
        "window_start": demand["window_start"],
        "window_end": demand["window_end"],
        "measurement_method": demand["measurement_method"],
        "days": demand.get("days", "all"),
        "season_months": demand.get("season_months") or None,
    }


EXPORT_FIELDS = (
    "credit_rate",
    "credit_window_start",
    "credit_window_end",
    "charge_rate",
    "charge_window_start",
    "charge_window_end",
    "free_threshold_kwh",
)


def expected_export(export: dict) -> dict:
    return {
        **{field: export.get(field) for field in EXPORT_FIELDS},
        "credit_season_months": export.get("credit_season_months") or None,
        "days": export.get("days", "all"),
    }


def by_content(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))


@pytest.mark.parametrize("seed", SEED_TARIFFS, ids=tariff_id)
def test_api_returns_the_seed_tariff(seed_client, seed):
    response = seed_client.get(f"/api/v1/tariffs/{seed['dnsp']}/{seed['code']}")
    assert response.status_code == 200
    body = response.json()

    assert (body["name"], body["tariff_type"]) == (seed["name"], seed["tariff_type"])
    assert body["effective_from"] == seed["effective_from"]
    assert body["effective_to"] == seed.get("effective_to")
    assert body["daily_supply_charge"] == seed.get("daily_supply_charge")
    assert body["source_url"] == seed.get("source_url")
    assert body["last_verified"] == seed.get("last_verified")
    assert by_content(body["rates"]) == by_content([expected_rate(r) for r in seed["rates"]])
    if body["demand"] is None or seed.get("demand") is None:
        assert body["demand"] == seed.get("demand")
    else:
        assert {k: body["demand"][k] for k in expected_demand(seed["demand"])} == expected_demand(
            seed["demand"]
        )
    assert by_content(body["export"]) == by_content(
        [expected_export(e) for e in seed.get("exports", [])]
    )


def test_seed_has_tariffs_with_exports():
    """The field-for-field test above is only evidence for exports while some exist."""
    assert any(tariff.get("exports") for tariff in SEED_TARIFFS)


@pytest.mark.parametrize(
    ("section", "model"),
    [("rates", TariffRate), ("demand", TariffDemand), ("exports", TariffExport)],
)
def test_seed_values_all_have_a_column(section, model):
    """A populated seed key with no model column would be dropped without an error."""
    columns = set(model.__table__.columns.keys())
    dropped = set()
    for tariff in SEED_TARIFFS:
        rows = tariff.get(section) or []
        for row in [rows] if isinstance(rows, dict) else rows:
            dropped |= {
                key for key, value in row.items() if key not in columns and value is not None
            }
    dropped.discard("period")
    assert dropped == set()


def test_populate_rejects_an_export_in_the_rates_shape():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    seed = {
        "dnsps": [{"code": "x", "name": "X", "state": "QLD", "timezone": "Australia/Brisbane"}],
        "tariffs": [
            {
                "dnsp": "x",
                "code": "T",
                "name": "T",
                "tariff_type": "tou_export",
                "effective_from": "2026-07-01",
                "rates": [],
                "exports": [{"period_name": "peak", "rate": 0.1}],
            }
        ],
    }
    with Session(engine) as session, pytest.raises(ValueError, match="x/T"):
        populate(session, [seed])


# ── 3. Time zones ──

DNSP_TIME_ZONES = {
    "ausgrid": "Australia/Sydney",
    "ausnet": "Australia/Melbourne",
    "citipower": "Australia/Melbourne",
    "endeavour": "Australia/Sydney",
    "energex": "Australia/Brisbane",
    "essential": "Australia/Sydney",
    "evoenergy": "Australia/Sydney",
    "jemena": "Australia/Melbourne",
    "powercor": "Australia/Melbourne",
    "powerwater": "Australia/Darwin",
    "sapn": "Australia/Adelaide",
    "united_energy": "Australia/Melbourne",
}


def test_each_dnsp_has_its_stated_time_zone(seed_client):
    response = seed_client.get("/api/v1/dnsps")
    assert {d["code"]: d["timezone"] for d in response.json()} == DNSP_TIME_ZONES


# ── 4. Known defects ──

NOON = "2026-11-11T12:00:00+11:00"


def current_rate(client, dnsp: str, tariff: str, at: str = NOON):
    return client.get(
        "/api/v1/calculate/current-rate", params={"dnsp": dnsp, "tariff": tariff, "datetime": at}
    )


@pytest.mark.xfail(reason="#46: saver period 11:00-16:00 not seeded", strict=True)
@pytest.mark.parametrize(
    ("dnsp", "tariff"),
    [("citipower", "CRSTOU"), ("powercor", "PRSTOU"), ("united_energy", "URSTOU")],
)
def test_victorian_residential_tou_has_a_saver_period(seed_client, dnsp, tariff):
    assert current_rate(seed_client, dnsp, tariff).json()["period"] == "saver"


@pytest.mark.xfail(reason="#48: the no-match fallback reports the first rate", strict=True)
def test_a180_does_not_report_off_peak_outside_its_window(seed_client):
    assert current_rate(seed_client, "jemena", "A180").json().get("period") != "off_peak"


@pytest.mark.xfail(reason="#49: a tariff with no energy rates returns 200 and zero", strict=True)
def test_ea029_does_not_report_a_zero_rate_as_success(seed_client):
    response = current_rate(seed_client, "ausgrid", "EA029")
    assert (response.status_code, response.json().get("period")) != (200, "unknown")
