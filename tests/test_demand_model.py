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
    """0.9.0 adds `unit` to `demand` (#71); every 0.8.0 field is unchanged."""
    assert len(FIXTURE["demand"]) == 102
    for key, expected in FIXTURE["demand"].items():
        demand = seed_client.get(f"/api/v1/tariffs/{key}").json()["demand"]
        if expected is None:
            assert demand is None, key
            continue
        assert demand["unit"] in ("kW", "kVA"), key
        assert {k: v for k, v in demand.items() if k != "unit"} == expected, key


def test_demand_methodology_matches_0_8_0(seed_client):
    """0.9.0 sets `rate_unit` from the tariff's demand unit (#71); the rest is unchanged."""
    body = seed_client.get("/api/v1/docs/demand-methodology").json()
    expected = FIXTURE["methodology"]
    assert {k: v for k, v in body.items() if k not in ("dnsps", "description")} == {
        k: v for k, v in expected.items() if k not in ("dnsps", "description")
    }
    assert body["description"] == expected["description"].replace(
        "measured in kW", "measured in kW or kVA, as each tariff states"
    )
    assert len(body["dnsps"]) == len(expected["dnsps"])
    for got, want in zip(body["dnsps"], expected["dnsps"], strict=True):
        assert got["rate_unit"] in ("$/kW/month", "$/kVA/month"), got["dnsp_code"]
        skip = ("rate_unit", "measurement_explanation")
        assert {k: v for k, v in got.items() if k not in skip} == {
            k: v for k, v in want.items() if k not in skip
        }
        text = want["measurement_explanation"]
        if got["rate_unit"] == "$/kVA/month" and text is not None:
            text = text.replace("power draw (kW)", "apparent power (kVA)")
        assert got["measurement_explanation"] == text, got["dnsp_code"]


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
    assert off_season.rate == 2.862
    assert (off_season.start, off_season.end, off_season.days) == ("15:00", "21:00", "weekdays")
    assert (off_season.unit, off_season.peak_period) == ("kW", "month")


def test_standard_time_tariffs(seed_session):
    # Jemena A180 and every Evoenergy tariff state their windows in AEST (#68).
    tariffs = seed_session.execute(select(Tariff).join(Dnsp)).scalars().all()
    standard = sorted((t.dnsp.code, t.code) for t in tariffs if t.time_basis == "standard")
    assert standard == [
        ("evoenergy", "017"),
        ("evoenergy", "023"),
        ("evoenergy", "060"),
        ("evoenergy", "090"),
        ("evoenergy", "101"),
        ("jemena", "A180"),
    ]
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
        if charge.start == charge.end:
            assert charge.period == "anytime"
        else:
            assert charge.period in ("peak", "shoulder", "off_peak")


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


# ── Demand unit on the compatibility outputs (#71) ──
# Essential BLND1AR is priced per kVA, Energex 7200 per kW, Energex 8400 has no demand charge
# (seed/essential.json, seed/energex.json; checked against knowledge/documents/essential/ and
# knowledge/documents/energex/ under #62).

UNIT_CASES = [
    ("essential", "BLND1AR", "kVA", 5.1925, 25.96),
    ("energex", "7200", "kW", 15.459, 77.30),
]


@pytest.mark.parametrize(("dnsp", "code", "unit", "rate", "monthly"), UNIT_CASES)
def test_demand_object_states_its_charge_unit(seed_client, dnsp, code, unit, rate, monthly):
    body = seed_client.get(f"/api/v1/tariffs/{dnsp}/{code}").json()
    assert body["demand"]["rate"] == rate
    assert body["demand"]["unit"] == unit
    assert body["demand_charges"][0]["unit"] == unit


@pytest.mark.parametrize(("dnsp", "code", "unit", "rate", "monthly"), UNIT_CASES)
def test_demand_surcharge_states_the_unit_of_its_rate(
    seed_client, dnsp, code, unit, rate, monthly
):
    response = seed_client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": dnsp, "tariff": code, "peak_demand_kw": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["demand_rate"] == rate
    assert data["monthly_demand_charge"] == monthly
    assert data["demand_unit"] == unit
    assert data["unit"] == "$/kWh"


def test_methodology_rate_unit_follows_the_tariff(seed_client):
    """Essential's demand tariffs are all per kVA; Jemena's are all per kW."""
    dnsps = {
        d["dnsp_code"]: d
        for d in seed_client.get("/api/v1/docs/demand-methodology").json()["dnsps"]
    }
    assert dnsps["essential"]["rate_unit"] == "$/kVA/month"
    assert dnsps["jemena"]["rate_unit"] == "$/kW/month"


def test_methodology_rate_unit_matches_its_tariffs_demand_unit(seed_client):
    """Each DNSP's rate_unit is the unit of the tariff whose source_url it reports."""
    for d in seed_client.get("/api/v1/docs/demand-methodology").json()["dnsps"]:
        if not d["has_demand_tariffs"]:
            continue
        unit = d["rate_unit"].split("/")[1]
        dnsp = d["dnsp_code"]
        codes = [t["code"] for t in seed_client.get(f"/api/v1/tariffs/{dnsp}").json()]
        units = {
            c["unit"]
            for code in codes
            for c in seed_client.get(f"/api/v1/tariffs/{dnsp}/{code}").json()["demand_charges"]
        }
        assert unit in units, dnsp


def test_no_demand_charge_has_no_demand_unit(seed_client):
    """With no demand charge, `demand` is null, so no unit is stated; the surcharge is a 400."""
    body = seed_client.get("/api/v1/tariffs/energex/8400").json()
    assert body["demand"] is None
    assert body["demand_charges"] == []
    response = seed_client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "8400", "peak_demand_kw": 5},
    )
    assert response.status_code == 400


def test_methodology_without_demand_tariffs_keeps_the_0_8_0_rate_unit(seed_client):
    """Additive only (#71): a DNSP with no demand tariff keeps its 0.8.0 rate_unit."""
    for d in seed_client.get("/api/v1/docs/demand-methodology").json()["dnsps"]:
        if not d["has_demand_tariffs"]:
            assert d["rate_unit"] == "$/kW/month", d["dnsp_code"]


def test_methodology_explanation_names_kva_for_a_kva_entry(seed_client):
    """Essential is per kVA (#77): its explanation names kVA, not kW."""
    dnsps = {
        d["dnsp_code"]: d
        for d in seed_client.get("/api/v1/docs/demand-methodology").json()["dnsps"]
    }
    text = dnsps["essential"]["measurement_explanation"]
    assert dnsps["essential"]["rate_unit"] == "$/kVA/month"
    assert "maximum apparent power (kVA)" in text
    assert "kW" not in text


def test_methodology_explanation_is_unchanged_for_a_kw_entry(seed_client):
    """Energex is per kW (#77): its explanation keeps the 0.8.0 text."""
    dnsps = {
        d["dnsp_code"]: d
        for d in seed_client.get("/api/v1/docs/demand-methodology").json()["dnsps"]
    }
    assert dnsps["energex"]["rate_unit"] == "$/kW/month"
    assert dnsps["energex"]["measurement_explanation"] == (
        "The average power draw (kW) over the highest 30-minute interval within "
        "the demand window during the billing month. Your meter records consumption "
        "in 30-minute blocks; the block with the highest average is your peak demand "
        "for that month."
    )


def test_methodology_description_states_both_units(seed_client):
    description = seed_client.get("/api/v1/docs/demand-methodology").json()["description"]
    assert "kW or kVA" in description
