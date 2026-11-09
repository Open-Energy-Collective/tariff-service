"""The real seed through seed/build_db.py and the API (#51).

1. Every tariff resolves to exactly one rate at every half hour, or to a defined gap.
2. The API returns what seed/*.json holds, field for field.
3. Each DNSP's time zone is stated here, independently of the seed.
4. Known defects are strict xfails linked to their issue, so a fix reports as XPASS.
5. Energy rates and supply charges match the 2026-27 sources, one tariff per DNSP and type.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.tariff import Dnsp, Tariff, TariffDemandCharge, TariffExport, TariffRate
from app.services.rate_calculator import get_current_rate
from app.services.window_match import clock_for, window_applies
from seed import build_db
from seed.build_db import populate, validate_tariff_versions

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

SEED_TARIFFS = [
    tariff
    for path in sorted(SEED_DIR.glob("*.json"))
    for tariff in json.loads(path.read_text())["tariffs"]
]


def tariff_id(tariff: dict) -> str:
    return f"{tariff['dnsp']}-{tariff['code']}"


# ── 1. Every half hour resolves to one rate ──

# Times with no rate in force: current-rate reports period "none" and a null rate
# (governance/adr/cross-project.md, 2026-11-09). Any other tariff has one rate at all times.
NO_RATE_AT = {
    ("ausgrid", "EA029"): lambda at: True,  # #49: export terms only, no energy rates
    ("endeavour", "N90"): lambda at: True,  # #47: the block depends on consumption
    ("jemena", "A180"): lambda at: 7 <= at.hour < 23,  # #48: one rate, 23:00-07:00
}


def sweep_params():
    for tariff in SEED_TARIFFS:
        yield pytest.param(tariff["dnsp"], tariff["code"], id=tariff_id(tariff))


def sample_days() -> list[datetime]:
    """A Monday, Saturday and Sunday of each month."""
    days = []
    for month in range(1, 13):
        first = datetime(2026, month, 1)
        monday = first + timedelta(days=-first.weekday() % 7)
        days += [monday, monday + timedelta(days=5), monday + timedelta(days=6)]
    return days


def matching_rates(tariff: Tariff, instant: datetime) -> list[TariffRate]:
    """The rows that decide the rate at an instant: specific windows, else catch-alls."""
    clock = clock_for(tariff)

    def applies(r: TariffRate) -> bool:
        months = json.loads(r.season_months) if r.season_months else None
        return window_applies(
            r.start_time, r.end_time, r.days, r.public_holidays, months, clock, instant
        )

    active = [r for r in tariff.rates if applies(r)]
    specific = [r for r in active if r.start_time != r.end_time]
    return specific or [r for r in active if r.start_time == r.end_time]


@pytest.mark.parametrize(("dnsp", "code"), sweep_params())
def test_every_half_hour_has_exactly_one_rate_or_a_defined_gap(seed_engine, dnsp, code):
    no_rate_at = NO_RATE_AT.get((dnsp, code))
    with Session(seed_engine) as session:
        tariff = session.execute(
            select(Tariff).join(Dnsp).where(Dnsp.code == dnsp, Tariff.code == code)
        ).scalar_one()
        for day in sample_days():
            for i in range(48):
                at = day + timedelta(minutes=30 * i)
                instant = clock_for(tariff).instant(at.date(), at.time())
                resolved = get_current_rate(tariff, instant)
                if no_rate_at is not None and no_rate_at(at):
                    assert resolved == ("none", None), f"{at:%a %m-%d %H:%M}: {resolved}"
                    continue
                found = [(r.period_name, r.rate) for r in matching_rates(tariff, instant)]
                assert len(found) == 1, f"{at:%a %m-%d %H:%M}: {found}"
                assert resolved == found[0], f"{at:%a %m-%d %H:%M}: {resolved}"


# ── Version dates are aligned ──


def version(start: str, end: str | None, code: str = "T1", dnsp: str = "d") -> dict:
    return {"dnsp": dnsp, "code": code, "effective_from": start, "effective_to": end}


def seed_with(*tariffs: dict) -> list[dict]:
    return [{"tariffs": list(tariffs)}]


def test_aligned_versions_are_accepted():
    validate_tariff_versions(
        seed_with(version("2027-07-01", None), version("2026-07-01", "2027-07-01"))
    )


@pytest.mark.parametrize(
    "tariffs",
    [
        pytest.param([version("2026-07-01", "2027-06-30"), version("2027-07-01", None)], id="gap"),
        pytest.param(
            [version("2026-07-01", "2027-08-01"), version("2027-07-01", None)], id="overlap"
        ),
        pytest.param([version("2026-07-01", None), version("2027-07-01", None)], id="no-end"),
        pytest.param([version("2026-07-01", None), version("2026-07-01", None)], id="same-start"),
        pytest.param(
            [version("2026-07-01", "2026-07-01"), version("2026-07-01", None)],
            id="empty-version",
        ),
        pytest.param([version("2026-07-01", "2027-07-01")], id="end-on-only-version"),
        pytest.param(
            [version("2026-07-01", "2027-07-01"), version("2027-07-01", "2028-07-01")],
            id="end-on-last-version",
        ),
    ],
)
def test_misaligned_versions_are_rejected(tariffs):
    with pytest.raises(ValueError, match="d/T1"):
        validate_tariff_versions(seed_with(*tariffs))


def test_versions_are_checked_per_tariff():
    validate_tariff_versions(
        seed_with(
            version("2026-07-01", None, code="T1"),
            version("2027-07-01", None, code="T2"),
            version("2027-07-01", None, code="T1", dnsp="e"),
        )
    )


def test_populate_rejects_misaligned_versions_before_writing():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    dnsp = {"code": "d", "name": "D", "state": "QLD", "timezone": "Australia/Brisbane"}
    misaligned = [version("2026-07-01", None), version("2027-07-01", None)]
    files = [{"dnsps": [dnsp], "tariffs": misaligned}]
    with Session(engine) as session:
        with pytest.raises(ValueError):
            populate(session, files)
        assert session.query(Dnsp).count() == 0


def test_failed_build_keeps_the_existing_database(tmp_path, monkeypatch):
    existing = tmp_path / "tariffs.db"
    existing.write_text("previous build")
    monkeypatch.setattr(build_db, "DB_PATH", existing)
    monkeypatch.setattr(
        build_db,
        "load_seed_files",
        lambda: seed_with(version("2026-07-01", None), version("2027-07-01", None)),
    )
    with pytest.raises(ValueError):
        build_db.build_database()
    assert existing.read_text() == "previous build"


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


def expected_demand(tariff: dict) -> dict | None:
    """The `demand` object: the highest-rate charge, a tie going to the earliest start."""
    charges = tariff.get("demand_charges") or []
    if not charges:
        return None
    charge = min(charges, key=lambda c: (-c["rate"], c["start"]))
    return {
        "rate": charge["rate"],
        "window_start": charge["start"],
        "window_end": charge["end"],
        "measurement_method": charge["measurement_method"],
        "days": charge.get("days", "all"),
        "season_months": charge.get("months") or None,
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
    demand = expected_demand(seed)
    if body["demand"] is None or demand is None:
        assert body["demand"] == demand
    else:
        assert {k: body["demand"][k] for k in demand} == demand
    assert by_content(body["export"]) == by_content(
        [expected_export(e) for e in seed.get("exports", [])]
    )


def test_seed_has_tariffs_with_exports():
    """The field-for-field test above is only evidence for exports while some exist."""
    assert any(tariff.get("exports") for tariff in SEED_TARIFFS)


@pytest.mark.parametrize(
    ("section", "model"),
    [("rates", TariffRate), ("demand_charges", TariffDemandCharge), ("exports", TariffExport)],
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
                "time_basis": "local",
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


def assert_no_rate_in_force(response) -> None:
    assert response.status_code == 200
    body = response.json()
    assert (body["period"], body["rate"]) == ("none", None)


def test_a180_reports_no_rate_outside_its_window(seed_client):
    assert_no_rate_in_force(current_rate(seed_client, "jemena", "A180"))


def test_a180_reports_its_rate_inside_its_window(seed_client):
    body = current_rate(seed_client, "jemena", "A180", "2026-07-15T23:30:00+10:00").json()
    assert (body["period"], body["rate"]) == ("off_peak", 0.04252)


def test_ea029_reports_no_rate_in_force(seed_client):
    assert_no_rate_in_force(current_rate(seed_client, "ausgrid", "EA029"))


@pytest.mark.parametrize("at", [NOON, "2026-07-15T02:00:00+10:00"])
def test_n90_reports_no_single_rate_because_the_block_depends_on_consumption(seed_client, at):
    assert_no_rate_in_force(current_rate(seed_client, "endeavour", "N90", at))


def test_n90_still_lists_both_blocks(seed_client):
    rates = seed_client.get("/api/v1/tariffs/endeavour/N90").json()["rates"]
    assert {r["period"] for r in rates} == {"block_1", "block_2"}


# ── 5. Source-checked energy rates and supply charges ──

# Sources are knowledge/documents/<entry> in the OEC root, ex GST. Expected values are
# written in the source's own units and were read from the source, not from the seed.
# CitiPower, Powercor and United Energy have no captured 2026-27 rates (#46).
AUSGRID = "ausgrid/2026-10-21-network-price-list-2026-27.pdf"
AUSNET = "ausnet/2026-10-21-network-tariff-schedule-2026-27.xlsx, sheet Network 2026-27"
ENDEAVOUR = "endeavour-energy/2026-10-21-network-price-list-2026-27.pdf"
ENERGEX = "energex/2026-10-21-network-price-list-2026-27.xlsx"
ESSENTIAL = "essential-energy/2026-10-21-price-list-explanatory-notes-2026-27.pdf"
EVOENERGY = "evoenergy/2026-10-21-schedule-of-charges-2026-27.pdf, excluding metering"
JEMENA = "jemena/2026-10-21-network-tariff-schedule-2026-27.pdf"
POWERWATER = "power-and-water/2026-10-21-network-tariffs-2026-27.pdf"
SAPN = "sa-power-networks/2026-10-21-tariff-price-list-2026-27.pdf, Table 1"


def cents(value: float) -> float:
    return value / 100


def per_year(value: float) -> float:
    return value / 365


@dataclass(frozen=True)
class SourcePrices:
    dnsp: str
    code: str
    entry: str
    supply: float  # $/day
    rates: tuple[tuple[str, float], ...]  # (period, $/kWh)
    export: tuple[float, float] | None = None  # (credit, charge) in $/kWh
    defect: str | None = None


def flat(dnsp, code, entry, supply, rate, period="anytime"):
    return SourcePrices(dnsp, code, entry, supply, ((period, rate),))


SOURCE_PRICES = [
    flat("ausgrid", "EA010", AUSGRID, cents(50.8550), cents(12.7029)),
    SourcePrices(
        "ausgrid",
        "EA025",
        AUSGRID,
        cents(63.2330),
        (("peak", cents(32.5164)), ("off_peak", cents(5.3570))),
    ),
    SourcePrices(
        "ausgrid",
        "EA116",
        AUSGRID,
        cents(67.0054),
        (("peak", cents(2.8061)), ("off_peak", cents(2.8061))),
    ),
    SourcePrices("ausgrid", "EA029", AUSGRID, 0.0, (), export=(cents(3.8551), cents(1.2320))),
    flat("ausgrid", "EA030", AUSGRID, cents(1.4842), cents(2.9657)),
    flat("ausnet", "NEE11", AUSNET, per_year(145.30522), cents(13.42965)),
    SourcePrices(
        "ausnet",
        "NASS11",
        AUSNET,
        per_year(145.30522),
        (("peak", cents(26.95562)), ("solar_soak", cents(1)), ("off_peak", cents(5.32994))),
    ),
    SourcePrices(
        "ausnet",
        "RCER11",
        AUSNET,
        per_year(145.30522),
        (("peak", cents(26.95562)), ("solar_soak", cents(1)), ("off_peak", cents(5.32994))),
        export=(cents(10), cents(1)),
    ),
    flat("ausnet", "NEE33", AUSNET, 0.0, cents(4.90046)),
    SourcePrices(
        "ausnet",
        "NASN12",
        AUSNET,
        per_year(148.93785),
        (("anytime", cents(16.79589)),),
    ),
    flat("endeavour", "N70", ENDEAVOUR, cents(70.1921), cents(12.0348)),
    SourcePrices(
        "endeavour",
        "N71",
        ENDEAVOUR,
        cents(70.1921),
        (
            ("peak", cents(23.4471)),
            ("peak", cents(15.2042)),
            ("solar_soak", cents(4.5355)),
            ("off_peak", cents(11.7340)),
        ),
    ),
    SourcePrices(
        "endeavour",
        "N72",
        ENDEAVOUR,
        cents(70.1921),
        (("solar_soak", cents(4.5355)), ("anytime", cents(10.1466))),
    ),
    flat("endeavour", "N50", ENDEAVOUR, cents(11.8721), cents(4.8190)),
    flat("energex", "8400", ENERGEX, 0.994, 0.09391),
    SourcePrices(
        "energex",
        "6900",
        ENERGEX,
        0.774,
        (("peak", 0.19533), ("shoulder", 0.06069), ("off_peak", 0.00434)),
    ),
    SourcePrices(
        "energex",
        "3900",
        ENERGEX,
        0.574,
        (("peak", 0.02533), ("shoulder", 0.06069), ("off_peak", 0.00434)),
    ),
    flat("energex", "9100", ENERGEX, 0.0, 0.02675, period="controlled_load"),
    flat("energex", "8300", ENERGEX, 10.44, 0.03365),
    SourcePrices(
        "energex",
        "96200",
        ENERGEX,
        0.651,
        (("peak", 0.19533), ("shoulder", 0.06069), ("off_peak", 0.00434)),
        export=(0.12195, 0.0221),
    ),
    SourcePrices(
        "essential",
        "BLNRSS2",
        ESSENTIAL,
        1.4704,
        (("peak", cents(17.9566)), ("off_peak", cents(6.3275))),
    ),
    SourcePrices(
        "essential",
        "BLND1AR",
        ESSENTIAL,
        1.4704,
        (("peak", cents(10.8399)), ("shoulder", cents(7.3713)), ("off_peak", cents(4.3811))),
    ),
    flat("essential", "BLNC1AU", ESSENTIAL, 0.1338, cents(3.5046)),
    SourcePrices(
        "evoenergy",
        "017",
        EVOENERGY,
        cents(39.331),
        (("peak", cents(19.084)), ("solar_soak", cents(4.814)), ("off_peak", cents(7.386))),
    ),
    SourcePrices(
        "evoenergy",
        "023",
        EVOENERGY,
        cents(39.391),
        (("solar_soak", cents(4.665)), ("off_peak", cents(6.569))),
    ),
    flat("evoenergy", "060", EVOENERGY, 0.0, cents(5.413)),
    flat("jemena", "A100", JEMENA, per_year(120.774), cents(9.486)),
    SourcePrices(
        "jemena",
        "A130",
        JEMENA,
        per_year(120.754),
        (("peak", cents(18.208)), ("solar_soak", cents(1)), ("off_peak", cents(4.551))),
    ),
    SourcePrices(
        "jemena",
        "A10E",
        JEMENA,
        per_year(121.014),
        (("peak", cents(18.208)), ("solar_soak", cents(1)), ("off_peak", cents(4.551))),
        export=(cents(15), cents(3)),
    ),
    flat("jemena", "A180", JEMENA, 0.0, cents(4.252), period="off_peak"),
    SourcePrices(
        "jemena",
        "A230",
        JEMENA,
        per_year(494.463),
        (("peak", cents(9.809)), ("off_peak", cents(3.442))),
    ),
    flat("powerwater", "T1", POWERWATER, 2.4599, 0.0659),
    SourcePrices(
        "powerwater",
        "T3A",
        POWERWATER,
        2.4596,
        (("peak", 0.1968), ("solar_soak", 0.0592), ("off_peak", 0.0592)),
    ),
    flat("powerwater", "T5", POWERWATER, 108.0677, 0.0295),
    flat("sapn", "RSR", SAPN, 0.6553, 0.1634),
    SourcePrices(
        "sapn",
        "RTOU",
        SAPN,
        0.6553,
        (("peak", 0.2133), ("off_peak", 0.1067), ("solar_sponge", 0.0535)),
    ),
    SourcePrices(
        "sapn",
        "MBTOUD",
        SAPN,
        1.5082,
        (("peak", 0.2073), ("off_peak", 0.0780), ("shoulder", 0.1442)),
    ),
]

SEED_ROUNDING = 6e-6  # the seed holds 5 decimal places


def source_params():
    for case in SOURCE_PRICES:
        marks = [pytest.mark.xfail(reason=case.defect, strict=True)] if case.defect else []
        yield pytest.param(case, id=f"{case.dnsp}-{case.code}", marks=marks)


@pytest.mark.parametrize("case", source_params())
def test_prices_match_the_source(seed_client, case):
    body = seed_client.get(f"/api/v1/tariffs/{case.dnsp}/{case.code}").json()

    assert body["daily_supply_charge"] == pytest.approx(case.supply, abs=SEED_ROUNDING)
    seeded = sorted({(r["period"], r["rate"]) for r in body["rates"]})
    expected = sorted(case.rates)
    assert [period for period, _ in seeded] == [period for period, _ in expected]
    assert [rate for _, rate in seeded] == pytest.approx(
        [rate for _, rate in expected], abs=SEED_ROUNDING
    )
    if case.export:
        assert [(e["credit_rate"], e["charge_rate"]) for e in body["export"]] == [
            pytest.approx(case.export, abs=SEED_ROUNDING)
        ]


def test_each_dnsp_and_type_with_captured_rates_has_a_source_check():
    covered = {
        (c.dnsp, t["tariff_type"])
        for c in SOURCE_PRICES
        for t in SEED_TARIFFS
        if (t["dnsp"], t["code"]) == (c.dnsp, c.code)
    }
    unpriced = {"citipower", "powercor", "united_energy"}
    assert {
        (t["dnsp"], t["tariff_type"]) for t in SEED_TARIFFS if t["dnsp"] not in unpriced
    } == covered


def test_rcer11_export_windows_match_the_source(seed_client):
    """AusNet workbook, sheet Tariff structures, structure 20, local time, every day."""
    export = seed_client.get("/api/v1/tariffs/ausnet/RCER11").json()["export"][0]
    assert (export["charge_window_start"], export["charge_window_end"]) == ("11:00", "16:00")
    assert (export["credit_window_start"], export["credit_window_end"]) == ("16:00", "21:00")
    assert export["free_threshold_kwh"] == 1  # the basic export level, kWh per day
    assert export["days"] == "all"


# sa-power-networks/2026-10-21-tariff-price-list-2026-27.pdf Table 1 (rates) and
# 2026-10-21-customer-overview-2026-27.pdf Tables 2 and 4 (windows, allowances), 0-30 kW export.
SAPN_SOLAR_SPONGE = ("10:00", "16:00")
SAPN_NOV_MAR = [1, 2, 3, 11, 12]
SAPN_EXPORTS = [
    ("RSR", 0.0075, (None, None), 11.0, None),
    ("BSR", 0.0075, (None, None), 11.0, None),
    ("RTOU", 0.0100, SAPN_SOLAR_SPONGE, 9.0, None),
    ("SBTOU", 0.0100, SAPN_SOLAR_SPONGE, 9.0, None),
    ("MBTOUD", 0.0100, SAPN_SOLAR_SPONGE, 9.0, None),
    ("RESELE", 0.0100, SAPN_SOLAR_SPONGE, 9.0, 0.1322),
    ("SBELE", 0.0100, SAPN_SOLAR_SPONGE, 9.0, 0.1322),
]


@pytest.mark.parametrize(("code", "charge", "window", "free", "credit"), SAPN_EXPORTS)
def test_sapn_exports_match_the_source(seed_client, code, charge, window, free, credit):
    exports = seed_client.get(f"/api/v1/tariffs/sapn/{code}").json()["export"]
    assert len(exports) == 1
    export = exports[0]
    assert export["charge_rate"] == charge
    assert (export["charge_window_start"], export["charge_window_end"]) == window
    assert export["free_threshold_kwh"] == free
    assert export["credit_rate"] == credit
    assert (export["credit_window_start"], export["credit_window_end"]) == (
        ("17:00", "21:00") if credit else (None, None)
    )
    assert export["credit_season_months"] == (SAPN_NOV_MAR if credit else None)
    assert export["days"] == "all"


# ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.pdf, time of use tariff:
# from 1 July 2024 peak 3pm-9pm all days, November to March and June to August.
AUSGRID_HIGH_SEASON = {1, 2, 3, 6, 7, 8, 11, 12}


@pytest.mark.parametrize("month", range(1, 13))
def test_ea025_peak_only_in_the_source_high_season(seed_client, month):
    year = 2027 if month < 7 else 2026
    period = current_rate(seed_client, "ausgrid", "EA025", f"{year}-{month:02d}-15T18:00:00")
    assert period.json()["period"] == ("peak" if month in AUSGRID_HIGH_SEASON else "off_peak")


@pytest.mark.parametrize(
    ("hhmm", "period"),
    [("14:59", "off_peak"), ("15:00", "peak"), ("20:59", "peak"), ("21:00", "off_peak")],
)
def test_ea025_peak_window_matches_the_source(seed_client, hhmm, period):
    response = current_rate(seed_client, "ausgrid", "EA025", f"2026-07-18T{hhmm}:00")
    assert response.json()["period"] == period
