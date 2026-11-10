"""/calculate/current-rate on the demand model: charges in force, tariff clock, holidays."""

import pytest


def current(client, dnsp: str, code: str, at: str) -> dict:
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": dnsp, "tariff": code, "datetime": at},
    )
    assert response.status_code == 200
    return response.json()


# NASN12, Melbourne: 2026-11-11 is a Wednesday
@pytest.mark.parametrize(
    ("when", "rate", "active"),
    [
        ("2026-11-11T10:00:00+11:00", 2.862, False),
        ("2026-11-11T17:00:00+11:00", 2.862, True),
        ("2026-12-09T17:00:00+11:00", 11.473, True),
    ],
)
def test_nasn12_charge_in_force(seed_client, when, rate, active):
    body = current(seed_client, "ausnet", "NASN12", when)
    assert body["demand_charges"] == [
        {"period": "peak", "rate": rate, "unit": "kW", "peak_period": "month", "active": active}
    ]
    assert body["in_demand_window"] is active


def test_nasn12_season_boundary(seed_client):
    last_peak = current(seed_client, "ausnet", "NASN12", "2027-03-31T17:00:00+11:00")
    first_off = current(seed_client, "ausnet", "NASN12", "2027-04-01T17:00:00+11:00")
    assert [c["rate"] for c in last_peak["demand_charges"]] == [11.473]
    assert [c["rate"] for c in first_off["demand_charges"]] == [2.862]


def test_a180_07_30_daylight_saving_is_off_peak(seed_client):
    # A180 runs 23:00-07:00 on standard time: 07:30 AEDT is 06:30 standard.
    body = current(seed_client, "jemena", "A180", "2026-11-11T07:30:00+11:00")
    assert (body["period"], body["rate"]) == ("off_peak", 0.04252)
    assert body["demand_charges"] == []


def test_a180_23_30_daylight_saving_is_none(seed_client):
    # 23:30 AEDT is 22:30 standard, before the window opens.
    body = current(seed_client, "jemena", "A180", "2026-11-11T23:30:00+11:00")
    assert (body["period"], body["rate"]) == ("none", None)


def test_a180_winter_unchanged(seed_client):
    morning = current(seed_client, "jemena", "A180", "2026-07-15T07:30:00+10:00")
    night = current(seed_client, "jemena", "A180", "2026-07-15T23:30:00+10:00")
    assert (morning["period"], morning["rate"]) == ("none", None)
    assert (night["period"], night["rate"]) == ("off_peak", 0.04252)


def test_a180_no_offset_is_local_clock(seed_client):
    # No offset reads as Melbourne's clock, 07:30 AEDT, before converting to standard.
    body = current(seed_client, "jemena", "A180", "2026-11-11T07:30:00")
    assert body["period"] == "off_peak"


# Evoenergy states every window in AEST (#68). 2026-11-11 is a Wednesday in daylight
# saving, when Canberra's clock (+11:00) runs one hour ahead of AEST: each bound moves
# one hour later on the clock.
@pytest.mark.parametrize(
    ("code", "clock", "period"),
    [
        ("017", "07:59", "off_peak"),  # 06:59 AEST
        ("017", "08:00", "peak"),  # 07:00 AEST
        ("017", "21:59", "peak"),  # 20:59 AEST
        ("017", "22:00", "off_peak"),  # 21:00 AEST
        ("023", "11:59", "off_peak"),  # 10:59 AEST
        ("023", "12:00", "solar_soak"),  # 11:00 AEST
        ("023", "15:59", "solar_soak"),  # 14:59 AEST
        ("023", "16:00", "off_peak"),  # 15:00 AEST
        ("060", "00:59", "anytime"),  # 23:59 AEST the day before: no bound to move
        ("060", "01:00", "anytime"),
        ("090", "07:59", "off_peak"),
        ("090", "08:00", "peak"),
        ("090", "17:59", "peak"),
        ("090", "18:00", "shoulder"),
        ("090", "22:59", "shoulder"),
        ("090", "23:00", "off_peak"),
        ("101", "07:59", "off_peak"),
        ("101", "08:00", "peak"),
        ("101", "17:59", "peak"),
        ("101", "18:00", "shoulder"),
    ],
)
def test_evoenergy_energy_on_standard_time(seed_client, code, clock, period):
    body = current(seed_client, "evoenergy", code, f"2026-11-11T{clock}:00+11:00")
    assert body["period"] == period


@pytest.mark.parametrize(
    ("code", "clock", "active"),
    [
        ("101", "07:59", {13.2651: False}),
        ("101", "08:00", {13.2651: True}),
        ("101", "17:59", {13.2651: True}),
        ("101", "18:00", {13.2651: False}),
        # 023 in November: low-season peak 17:00-21:00 and off-peak 21:00-09:00 AEST
        ("023", "17:59", {3.9249: False, 0.6228: False}),
        ("023", "18:00", {3.9249: True, 0.6228: False}),
        ("023", "21:59", {3.9249: True, 0.6228: False}),
        ("023", "22:00", {3.9249: False, 0.6228: True}),
        ("023", "09:59", {3.9249: False, 0.6228: True}),
        ("023", "10:00", {3.9249: False, 0.6228: False}),
    ],
)
def test_evoenergy_demand_on_standard_time(seed_client, code, clock, active):
    body = current(seed_client, "evoenergy", code, f"2026-11-11T{clock}:00+11:00")
    assert {c["rate"]: c["active"] for c in body["demand_charges"]} == active
    assert body["in_demand_window"] is any(active.values())


def test_evoenergy_winter_unchanged(seed_client):
    # Out of daylight saving the clock is AEST: 07:00 opens the 101 peak.
    before = current(seed_client, "evoenergy", "101", "2026-07-15T06:59:00+10:00")
    after = current(seed_client, "evoenergy", "101", "2026-07-15T07:00:00+10:00")
    assert (before["period"], before["in_demand_window"]) == ("off_peak", False)
    assert (after["period"], after["in_demand_window"]) == ("peak", True)


def test_christmas_ausgrid_ea302(seed_client):
    body = current(seed_client, "ausgrid", "EA302", "2026-12-25T17:00:00+11:00")
    assert body["period"] == "off_peak"
    assert body["in_demand_window"] is False
    # In season on the holiday, so listed, but its window does not apply.
    assert [c["active"] for c in body["demand_charges"]] == [False]


def test_christmas_powerwater_t5(seed_client):
    body = current(seed_client, "powerwater", "T5", "2026-12-25T17:00:00+09:30")
    assert body["in_demand_window"] is True


def test_melbourne_cup_citipower_not_ausgrid(seed_client):
    at = "2026-11-03T17:00:00+11:00"
    assert current(seed_client, "citipower", "CGTOU", at)["period"] == "off_peak"
    assert current(seed_client, "ausgrid", "EA302", at)["period"] == "peak"


def test_out_of_season_charge_not_listed(seed_client):
    body = current(seed_client, "ausgrid", "EA251", "2027-05-12T17:00:00+10:00")
    assert body["demand_charges"] == []
    assert body["in_demand_window"] is False


def test_sapn_bsr_summer_current_rate_unchanged(seed_client):
    # BSR is standard time (#68); its single anytime rate holds across the daylight saving day.
    # The 11 kWh/day export allowance boundary (00:00 ACST = 01:00 ACDT) is not exposed by the API.
    instants = ("2026-11-11T00:30+10:30", "2026-11-11T01:30+10:30", "2026-07-15T12:00+09:30")
    for instant in instants:
        body = current(seed_client, "sapn", "BSR", instant)
        assert (body["period"], body["rate"]) == ("anytime", 0.1914)
