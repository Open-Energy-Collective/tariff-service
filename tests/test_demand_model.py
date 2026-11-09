"""The demand charge model, time basis and expected price end date (#31, #56, #61).

The 0.8.0 fixture holds every tariff's `demand` object and the methodology response, captured
before the model changed. The AusNet off-season rate is from
knowledge/documents/ausnet/2026-10-21-network-tariff-schedule-2026-27.md (structure 15).
"""

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.tariff import Dnsp, Tariff, TariffDemandCharge, TariffExport, TariffRate
from seed.build_db import populate, validate_tariff_fields

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "demand_0_8_0.json").read_text(encoding="utf-8")
)


def seeded(session: Session, dnsp: str, code: str) -> Tariff:
    return session.execute(
        select(Tariff).join(Dnsp).where(Dnsp.code == dnsp, Tariff.code == code)
    ).scalar_one()


def test_demand_object_matches_0_8_0_for_every_tariff(seed_client):
    assert len(FIXTURE["demand"]) == 102
    for key, expected in FIXTURE["demand"].items():
        assert seed_client.get(f"/api/v1/tariffs/{key}").json()["demand"] == expected, key


def test_demand_methodology_matches_0_8_0(seed_client):
    assert seed_client.get("/api/v1/docs/demand-methodology").json() == FIXTURE["methodology"]


def _charge(rate: float, start: str) -> TariffDemandCharge:
    return TariffDemandCharge(
        period="peak",
        rate=rate,
        unit="kW",
        start=start,
        end="21:00",
        days="all",
        measurement_method="30min_max",
        peak_period="month",
    )


def test_demand_object_is_highest_rate_charge_tie_to_earliest_start():
    low = _charge(2.0, "07:00")
    high_late = _charge(9.0, "17:00")
    high_early = _charge(9.0, "15:00")
    assert Tariff(demand_charges=[low, high_late, high_early]).demand is high_early
    assert Tariff(demand_charges=[]).demand is None


def test_nasn12_has_both_seasons(seed_session):
    charges = {
        tuple(sorted(json.loads(c.months))): c
        for c in seeded(seed_session, "ausnet", "NASN12").demand_charges
    }
    assert set(charges) == {(1, 2, 3, 12), (4, 5, 6, 7, 8, 9, 10, 11)}
    assert charges[(1, 2, 3, 12)].rate == 11.473
    off_season = charges[(4, 5, 6, 7, 8, 9, 10, 11)]
    assert off_season.rate == pytest.approx(2.862, abs=0.001)
    assert (off_season.start, off_season.end, off_season.days) == ("15:00", "21:00", "weekdays")
    assert (off_season.unit, off_season.peak_period) == ("kW", "month")


def test_a180_is_standard_time(seed_session):
    tariffs = seed_session.execute(select(Tariff).join(Dnsp)).scalars().all()
    standard = [(t.dnsp.code, t.code) for t in tariffs if t.time_basis == "standard"]
    assert standard == [("jemena", "A180")]
    assert {t.time_basis for t in tariffs} == {"local", "standard"}


def test_prices_expected_until_on_every_last_version(seed_session):
    tariffs = seed_session.execute(select(Tariff)).scalars().all()
    last: dict[tuple[int, str], Tariff] = {}
    for tariff in sorted(tariffs, key=lambda t: t.effective_from):
        last[(tariff.dnsp_id, tariff.code)] = tariff
    assert len(last) == 102
    assert {t.prices_expected_until for t in last.values()} == {"2027-07-01"}


def test_demand_charge_period_follows_the_window(seed_session):
    charges = seed_session.execute(select(TariffDemandCharge)).scalars().all()
    assert charges
    for charge in charges:
        assert charge.period == ("anytime" if charge.start == charge.end else "peak")


@pytest.mark.parametrize(
    ("dnsp", "code", "expected"),
    [("ausgrid", "EA302", "excluded"), ("powerwater", "T5", "included"), ("sapn", "RTOU", None)],
)
def test_public_holidays_on_weekday_windows(seed_session, dnsp, code, expected):
    tariff = seeded(seed_session, dnsp, code)
    rows = [*tariff.rates, *tariff.demand_charges]
    weekday = [r for r in rows if r.days == "weekdays"]
    assert all(r.days != "all" or r.public_holidays is None for r in rows)
    if expected is None:
        assert all(r.public_holidays == "included" for r in weekday)
    else:
        assert weekday and {r.public_holidays for r in weekday} == {expected}


@pytest.mark.parametrize(
    ("dnsp", "code", "rollover"),
    [
        ("sapn", "RSR", "billing_period"),
        ("sapn", "SBTOU", "billing_period_like_days"),
        ("ausnet", "RCER11", "none"),
    ],
)
def test_export_free_threshold_fields(seed_session, dnsp, code, rollover):
    (export,) = seeded(seed_session, dnsp, code).exports
    assert (export.free_threshold_period, export.free_threshold_rollover) == ("day", rollover)


def test_export_with_no_threshold_has_no_threshold_fields(seed_session):
    (export,) = seeded(seed_session, "jemena", "A10E").exports
    assert (export.free_threshold_period, export.free_threshold_rollover) == (None, None)


VALID_SEED = {
    "dnsps": [{"code": "x", "name": "X", "state": "QLD", "timezone": "Australia/Brisbane"}],
    "tariffs": [
        {
            "dnsp": "x",
            "code": "T",
            "name": "T",
            "tariff_type": "tou_demand",
            "effective_from": "2026-07-01",
            "time_basis": "local",
            "prices_expected_until": "2027-07-01",
            "rates": [
                {
                    "period_name": "peak",
                    "rate": 0.1,
                    "start_time": "16:00",
                    "end_time": "21:00",
                    "days": "weekdays",
                    "public_holidays": "excluded",
                }
            ],
            "demand_charges": [
                {
                    "period": "peak",
                    "rate": 5.0,
                    "unit": "kW",
                    "start": "16:00",
                    "end": "21:00",
                    "days": "weekdays",
                    "public_holidays": "excluded",
                    "months": None,
                    "measurement_method": "30min_avg",
                    "peak_period": "month",
                }
            ],
            "exports": [
                {
                    "charge_rate": 0.01,
                    "free_threshold_kwh": 1.0,
                    "free_threshold_period": "day",
                    "free_threshold_rollover": "none",
                    "days": "all",
                }
            ],
        }
    ],
}


def _without(section: str, field: str):
    def mutate(tariff: dict) -> None:
        del tariff[section][0][field]

    return mutate


def _set(section: str, field: str, value: str):
    def mutate(tariff: dict) -> None:
        tariff[section][0][field] = value

    return mutate


def _no_time_basis(tariff: dict) -> None:
    del tariff["time_basis"]


def _mixed_units(tariff: dict) -> None:
    tariff["demand_charges"].append({**tariff["demand_charges"][0], "unit": "kVA"})


REJECTED = [
    (_no_time_basis, "time_basis"),
    (_without("rates", "public_holidays"), "public_holidays"),
    (_without("demand_charges", "public_holidays"), "public_holidays"),
    (_set("rates", "days", "fortnightly"), "fortnightly"),
    (_set("demand_charges", "days", "fortnightly"), "fortnightly"),
    (_set("exports", "days", "fortnightly"), "fortnightly"),
    (_mixed_units, "kVA"),
    (_without("exports", "free_threshold_period"), "free_threshold_period"),
]


def _seed(mutation=None) -> dict:
    seed = copy.deepcopy(VALID_SEED)
    if mutation:
        mutation(seed["tariffs"][0])
    return seed


def test_seed_load_accepts_a_valid_seed():
    validate_tariff_fields([_seed()])


@pytest.mark.parametrize(("mutation", "message"), REJECTED)
def test_seed_load_rejects(mutation, message):
    with pytest.raises(ValueError, match=f"x/T.*{message}"):
        validate_tariff_fields([_seed(mutation)])


@pytest.mark.parametrize(("mutation", "message"), REJECTED)
def test_populate_applies_the_field_checks(mutation, message):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(ValueError, match=f"x/T.*{message}"):
        populate(session, [_seed(mutation)])


def test_new_columns_exist():
    assert {"public_holidays"} <= set(TariffRate.__table__.columns.keys())
    assert {"public_holidays", "free_threshold_period", "free_threshold_rollover"} <= set(
        TariffExport.__table__.columns.keys()
    )
