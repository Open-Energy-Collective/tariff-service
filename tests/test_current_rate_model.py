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
