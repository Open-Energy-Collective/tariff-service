"""API endpoint tests."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine
from app.main import app
from app.models.tariff import Dnsp, Tariff, TariffDemand, TariffRate

# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# DNSPs
# ─────────────────────────────────────────────────────────────────────────────


def test_list_dnsps(client):
    response = client.get("/api/v1/dnsps")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    codes = {d["code"] for d in data}
    assert codes == {"energex", "ausgrid", "sapn"}


# ─────────────────────────────────────────────────────────────────────────────
# Tariffs
# ─────────────────────────────────────────────────────────────────────────────


def test_list_tariffs(client):
    response = client.get("/api/v1/tariffs/energex")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "T12A"
    assert data[0]["tariff_type"] == "tou_demand"


def test_list_tariffs_not_found(client):
    response = client.get("/api/v1/tariffs/nonexistent")
    assert response.status_code == 404


def test_get_tariff_detail(client):
    response = client.get("/api/v1/tariffs/energex/T12A")
    assert response.status_code == 200
    data = response.json()
    assert data["dnsp"] == "energex"
    assert data["code"] == "T12A"
    assert data["demand"]["rate"] == 7.434
    assert data["demand"]["window_start"] == "16:00"
    assert len(data["rates"]) == 3


def test_get_tariff_detail_has_all_fields(client):
    response = client.get("/api/v1/tariffs/energex/T12A")
    data = response.json()
    assert data["daily_supply_charge"] == 1.1282
    assert data["effective_from"] == "2026-07-01"
    assert data["effective_to"] is None
    assert data["export"] == []
    assert data["demand"]["measurement_method"] == "30min_avg"
    assert data["demand"]["days"] == "all"


def test_get_tariff_not_found(client):
    response = client.get("/api/v1/tariffs/energex/FAKE")
    assert response.status_code == 404


def test_get_tariff_wrong_dnsp(client):
    response = client.get("/api/v1/tariffs/ausgrid/T12A")
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Tariff History
# ─────────────────────────────────────────────────────────────────────────────


def test_tariff_history(client):
    response = client.get("/api/v1/tariffs/energex/T12A/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["code"] == "T12A"
    assert data[0]["demand"] is not None
    assert len(data[0]["rates"]) == 3


def test_tariff_history_not_found(client):
    response = client.get("/api/v1/tariffs/energex/FAKE/history")
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Current Rate — Happy Paths
# ─────────────────────────────────────────────────────────────────────────────


def test_current_rate_peak(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T17:30:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.02367
    assert data["in_demand_window"] is True


def test_current_rate_off_peak(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T10:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.00476
    assert data["in_demand_window"] is False


def test_current_rate_shoulder(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T22:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "shoulder"
    assert data["rate"] == 0.04868
    assert data["in_demand_window"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Current Rate — Boundary Times
# ─────────────────────────────────────────────────────────────────────────────


def test_current_rate_at_peak_start(client):
    """Exactly 16:00 should be peak (start of peak window)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T16:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["in_demand_window"] is True


def test_current_rate_at_peak_end(client):
    """Exactly 21:00 should be shoulder (end of peak window)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T21:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "shoulder"
    assert data["in_demand_window"] is False


def test_current_rate_at_midnight(client):
    """Midnight should be off-peak."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T00:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["in_demand_window"] is False


def test_current_rate_just_before_peak(client):
    """15:59 should still be off-peak."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T15:59:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["in_demand_window"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Current Rate — Datetime Parsing
# ─────────────────────────────────────────────────────────────────────────────


def test_current_rate_unencoded_plus(client):
    """Unencoded + in timezone offset (arrives as space) should still work."""
    response = client.get(
        "/api/v1/calculate/current-rate?dnsp=energex&tariff=T12A&datetime=2026-07-20T17:30:00 10:00"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"


def test_current_rate_negative_offset(client):
    """Negative UTC offset should parse correctly."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-19T21:30:00-06:00"},
    )
    assert response.status_code == 200
    # 03:30 UTC on 20 July is 13:30 in Brisbane.
    assert response.json()["period"] == "off_peak"


@pytest.mark.parametrize(
    "dt", ["2026-07-20T17:30:00+10:00", "2026-07-20T07:30:00+00:00", "2026-07-20T02:30:00-05:00"]
)
def test_current_rate_resolves_in_dnsp_time_zone(client, dt):
    """One instant (17:30 Brisbane) gives one answer in any offset (#39)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": dt},
    )
    assert response.status_code == 200
    data = response.json()
    assert (data["period"], data["in_demand_window"]) == ("peak", True)


def test_current_rate_naive_datetime_is_dnsp_local(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "2026-07-20T17:30:00"},
    )
    assert response.status_code == 200
    assert response.json()["in_demand_window"] is True


def test_current_rate_invalid_datetime(client):
    """Invalid datetime format should return 400."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "not-a-date"},
    )
    assert response.status_code == 400
    assert "Invalid datetime format" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Current Rate — Error Cases
# ─────────────────────────────────────────────────────────────────────────────


def test_current_rate_missing_params(client):
    """Missing required params should return 422."""
    response = client.get("/api/v1/calculate/current-rate")
    assert response.status_code == 422


def test_current_rate_missing_datetime(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A"},
    )
    assert response.status_code == 422


def test_current_rate_invalid_dnsp(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "fake", "tariff": "T12A", "datetime": "2026-07-20T17:30:00+10:00"},
    )
    assert response.status_code == 404


def test_current_rate_invalid_tariff(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "FAKE", "datetime": "2026-07-20T17:30:00+10:00"},
    )
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Demand Surcharge — Happy Path
# ─────────────────────────────────────────────────────────────────────────────


def test_demand_surcharge(client):
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "T12A", "peak_demand_kw": 4.5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["demand_rate"] == 7.434
    assert data["peak_demand_kw"] == 4.5
    assert data["monthly_demand_charge"] == 33.45
    assert data["demand_window_hours_per_month"] == 150.0
    # 33.45 / (4.5 * 150) = 7.434 / 150 = 0.04956 (#33)
    assert abs(data["surcharge_per_kwh"] - 0.04956) < 0.00001


def test_demand_surcharge_high_demand(client):
    """Higher demand raises the monthly charge proportionally; the per-kWh
    surcharge stays rate / window hours (#33)."""
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "T12A", "peak_demand_kw": 10.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["peak_demand_kw"] == 10.0
    assert data["monthly_demand_charge"] == 74.34
    # 74.34 / (10 * 150) = 0.04956
    assert abs(data["surcharge_per_kwh"] - 0.04956) < 0.00001


def test_demand_surcharge_zero_demand(client):
    """Zero demand should produce zero surcharge."""
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "T12A", "peak_demand_kw": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_demand_charge"] == 0.0
    assert data["surcharge_per_kwh"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Demand Surcharge — Error Cases
# ─────────────────────────────────────────────────────────────────────────────


def test_demand_surcharge_missing_params(client):
    """Missing required params should return 422."""
    response = client.get("/api/v1/calculate/demand-surcharge")
    assert response.status_code == 422


def test_demand_surcharge_invalid_dnsp(client):
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "fake", "tariff": "T12A", "peak_demand_kw": 5.0},
    )
    assert response.status_code == 404


def test_demand_surcharge_invalid_tariff(client):
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "FAKE", "peak_demand_kw": 5.0},
    )
    assert response.status_code == 404


def test_demand_surcharge_non_numeric(client):
    """Non-numeric peak_demand_kw should return 422."""
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "T12A", "peak_demand_kw": "abc"},
    )
    assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────────────────────


def test_cors_headers(client):
    """OPTIONS request should return CORS headers."""
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI / Docs
# ─────────────────────────────────────────────────────────────────────────────


def test_openapi_spec(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Tariff Data Service"


def test_swagger_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Ausgrid — Seasonal Peak (only Jun-Aug & Nov-Mar)
# ─────────────────────────────────────────────────────────────────────────────


def test_ausgrid_peak_in_high_season(client):
    """July 18:00 is peak (high season, within 15:00-21:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2026-07-20T18:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.32516


def test_ausgrid_off_peak_in_high_season(client):
    """July 10:00 is off-peak (high season but outside 15:00-21:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2026-07-20T10:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.05357


def test_ausgrid_off_peak_in_shoulder_month(client):
    """April 18:00 is off-peak (shoulder month, no peak applies)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2027-04-19T18:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.05357


def test_ausgrid_off_peak_in_may(client):
    """May 17:00 is off-peak (May is shoulder month, no peak)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2027-05-14T17:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"


def test_ausgrid_peak_in_november(client):
    """November 16:00 is peak (summer high season starts)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2026-11-15T16:00:00+11:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.32516


def test_ausgrid_demand_window_high_season(client):
    """July 18:00 — demand window active (high season)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA116", "datetime": "2026-07-20T18:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_demand_window"] is True


def test_ausgrid_demand_window_shoulder_month(client):
    """April 18:00 — demand window NOT active (shoulder month)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA116", "datetime": "2027-04-19T18:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_demand_window"] is False


def test_ausgrid_demand_window_outside_hours(client):
    """July 10:00 — demand window NOT active (outside 15:00-21:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA116", "datetime": "2026-07-20T10:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_demand_window"] is False


# ─────────────────────────────────────────────────────────────────────────────
# SA Power Networks: solar sponge, off-peak, peak all other times
# ─────────────────────────────────────────────────────────────────────────────


def test_sapn_peak(client):
    """19:00 is peak, the catch-all."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T19:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.2133


def test_sapn_solar_sponge(client):
    """12:00 is solar_sponge (10:00-16:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T12:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "solar_sponge"
    assert data["rate"] == 0.0535


def test_sapn_morning_is_peak(client):
    """08:00 falls in no listed window, so the peak catch-all applies. RTOU has no shoulder."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T08:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.2133


def test_sapn_off_peak(client):
    """03:00 is off-peak (00:00-06:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T03:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.1067


# ─────────────────────────────────────────────────────────────────────────────
# All-day (00:00-00:00) catch-all window — regression coverage
# ─────────────────────────────────────────────────────────────────────────────
# Real seed data (Ausgrid EA025 off_peak, Jemena A230, Energex 8300, AusNet
# NASN12 demand windows) uses start_time == end_time == "00:00" to mean
# "applies at all other times" / "all day". This used to (a) never match in
# is_in_time_window (empty window), silently falling back to whichever rate
# SQLAlchemy happened to return first, and (b) divide by zero in
# calculate_demand_surcharge's window-hours calculation for demand windows
# using the same convention.


def test_demand_surcharge_all_day_window(client):
    """All-day (00:00-00:00) demand window must not divide by zero and must
    treat the window as the full 24 hours."""
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "ausgrid", "tariff": "EA117", "peak_demand_kw": 5.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["demand_window_hours_per_month"] == 24.0 * 30
    # 11.473 / 720 = 0.01593...
    assert abs(data["surcharge_per_kwh"] - 0.01593) < 0.00001


def test_current_rate_resolution_is_order_independent():
    """get_current_rate must resolve a specific window over the all-day
    catch-all regardless of the order rates are returned in — the previous
    behavior silently depended on unspecified relationship/query ordering."""
    from datetime import datetime
    from types import SimpleNamespace

    from app.services.rate_calculator import get_current_rate

    specific = SimpleNamespace(
        period_name="peak",
        rate=0.32516,
        start_time="15:00",
        end_time="21:00",
        days="all",
        season_months=None,
    )
    catchall = SimpleNamespace(
        period_name="off_peak",
        rate=0.05357,
        start_time="00:00",
        end_time="00:00",
        days="all",
        season_months=None,
    )
    at_peak_time = datetime.fromisoformat("2026-07-20T18:00:00+10:00")

    # Catch-all listed first...
    tariff_a = SimpleNamespace(rates=[catchall, specific])
    # ...and specific window listed first.
    tariff_b = SimpleNamespace(rates=[specific, catchall])

    assert get_current_rate(tariff_a, at_peak_time) == ("peak", 0.32516)
    assert get_current_rate(tariff_b, at_peak_time) == ("peak", 0.32516)


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting
# ─────────────────────────────────────────────────────────────────────────────


def test_rate_limit_enforced_per_ip():
    """21st request within a minute from the same IP is rejected with 429."""
    with TestClient(app) as limited_client:
        for _ in range(20):
            response = limited_client.get("/api/v1/health")
            assert response.status_code == 200

        response = limited_client.get("/api/v1/health")
        assert response.status_code == 429
        assert "retry-after" in {k.lower() for k in response.headers}


# ─────────────────────────────────────────────────────────────────────────────
# Demand windows (#36)
# ─────────────────────────────────────────────────────────────────────────────

DEMAND_WINDOWS = "/api/v1/calculate/demand-windows"
DAY_3800 = [{"start": "2026-10-23T17:00:00+10:00", "end": "2026-10-23T20:00:00+10:00"}]


@pytest.fixture
def energex_3800():
    """Energex 3800 with the seed's demand object (seed/energex.json)."""
    with Session(engine) as session:
        energex = session.query(Dnsp).filter_by(code="energex").one()
        tariff = Tariff(
            dnsp_id=energex.id,
            code="3800",
            name="Small Business Demand",
            tariff_type="tou_demand",
            effective_from="2026-07-01",
            effective_to=None,
            daily_supply_charge=0.0,
        )
        session.add(tariff)
        session.flush()
        session.add(
            TariffDemand(
                tariff_id=tariff.id,
                rate=7.0,
                window_start="17:00",
                window_end="20:00",
                measurement_method="30min_avg",
                days="weekdays",
                season_months=None,
            )
        )
        session.commit()


def windows(client, dnsp="energex", tariff="3800", start="2026-10-23T00:00:00+10:00",
            end="2026-10-24T00:00:00+10:00"):
    return client.get(
        DEMAND_WINDOWS, params={"dnsp": dnsp, "tariff": tariff, "start": start, "end": end}
    )


def test_demand_windows(client, energex_3800):
    r = windows(client)
    assert r.status_code == 200
    assert r.json() == {
        "dnsp": "energex",
        "tariff": "3800",
        "start": "2026-10-23T00:00:00+10:00",
        "end": "2026-10-24T00:00:00+10:00",
        "windows": DAY_3800,
    }


def test_demand_windows_unknown_tariff_404(client, energex_3800):
    r = windows(client, tariff="nope")
    assert r.status_code == 404
    assert r.json()["detail"] == "Tariff 'nope' not found for DNSP 'energex'"


def test_demand_windows_no_demand_is_empty(client):
    r = windows(client, dnsp="ausgrid", tariff="EA025")
    assert r.status_code == 200
    assert r.json()["windows"] == []


def test_demand_windows_end_not_after_start_400(client, energex_3800):
    r = windows(client, end="2026-10-23T00:00:00+10:00")
    assert r.status_code == 400
    assert "after start" in r.json()["detail"]


def test_demand_windows_range_over_31_days_400(client, energex_3800):
    r = windows(client, end="2026-11-23T00:01:00+10:00")
    assert r.status_code == 400
    assert "31 days" in r.json()["detail"]
    assert windows(client, end="2026-11-23T00:00:00+10:00").status_code == 200


@pytest.mark.parametrize("field", ["start", "end"])
def test_demand_windows_naive_datetime_400(client, energex_3800, field):
    r = windows(client, **{field: "2026-10-23T12:00:00"})
    assert r.status_code == 400
    assert "offset" in r.json()["detail"]


def test_demand_windows_invalid_datetime_400(client, energex_3800):
    r = windows(client, start="not-a-date")
    assert r.status_code == 400


def test_demand_windows_unencoded_plus(client, energex_3800):
    r = client.get(
        f"{DEMAND_WINDOWS}?dnsp=energex&tariff=3800"
        "&start=2026-10-23T00:00:00+10:00&end=2026-10-24T00:00:00+10:00"
    )
    assert r.status_code == 200
    assert r.json()["windows"] == DAY_3800


def test_demand_windows_mixed_offsets(client, energex_3800):
    r = windows(client, end="2026-10-24T01:00:00+11:00")
    assert r.status_code == 200
    assert r.json()["windows"] == DAY_3800


def test_openapi_documents_demand_windows(client):
    spec = client.get("/openapi.json").json()
    op = spec["paths"][DEMAND_WINDOWS]["get"]
    assert "31 days" in op["description"]
    for name in ("DemandWindowsResponse", "DemandWindow"):
        props = spec["components"]["schemas"][name]["properties"]
        assert all(p.get("description") for p in props.values()), name


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("9999-12-30T00:00:00+00:00", "9999-12-31T00:00:00+00:00"),
        ("0001-01-01T00:00:00+10:00", "0001-01-02T00:00:00+10:00"),
    ],
)
def test_demand_windows_out_of_range_year_400(client, start, end):
    r = windows(client, dnsp="energex", tariff="T12A", start=start, end=end)
    assert r.status_code == 400


def test_current_rate_out_of_range_year_400(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "T12A", "datetime": "9999-12-31T23:00:00+00:00"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("path", ["current-rate", "demand-surcharge", "demand-windows"])
def test_openapi_documents_calculate_errors(client, path):
    """The 400 and 404 responses are in the schema consumers vendor (#40)."""
    spec = client.get("/openapi.json").json()
    responses = spec["paths"][f"/api/v1/calculate/{path}"]["get"]["responses"]
    for code in ("400", "404"):
        assert responses[code]["description"], code
        assert responses[code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
    detail = spec["components"]["schemas"]["ErrorResponse"]["properties"]["detail"]
    assert detail["description"]


# ─────────────────────────────────────────────────────────────────────────────
# Tariff version selection (#51)
# ─────────────────────────────────────────────────────────────────────────────

OLD, CURRENT, FUTURE = 1.0, 2.0, 3.0


@pytest.fixture
def versioned_tariff():
    """Energex V1: three versions told apart by their supply charge and energy rate."""
    with Session(engine) as session:
        energex = session.query(Dnsp).filter_by(code="energex").one()
        for supply, start, end in [
            (OLD, "2025-07-01", "2026-07-01"),
            (CURRENT, "2026-07-01", None),
            (FUTURE, "2027-07-01", None),
        ]:
            tariff = Tariff(
                dnsp_id=energex.id,
                code="V1",
                name="Versioned",
                tariff_type="flat",
                effective_from=start,
                effective_to=end,
                daily_supply_charge=supply,
            )
            session.add(tariff)
            session.flush()
            session.add(
                TariffRate(
                    tariff_id=tariff.id,
                    period_name="anytime",
                    rate=supply,
                    start_time="00:00",
                    end_time="00:00",
                    days="all",
                    season="all",
                )
            )
        session.commit()


def set_today(monkeypatch, today: date) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr("app.services.tariff_service.date", FixedDate)


@pytest.mark.parametrize(
    ("today", "supply"),
    [
        (date(2026, 6, 30), OLD),  # last day of the old version
        (date(2026, 7, 1), CURRENT),  # effective_to is exclusive, effective_from inclusive
        (date(2027, 6, 30), CURRENT),
        (date(2027, 7, 1), FUTURE),  # two versions in force: the newest wins
    ],
)
def test_detail_selects_the_version_in_force(client, versioned_tariff, monkeypatch, today, supply):
    set_today(monkeypatch, today)
    response = client.get("/api/v1/tariffs/energex/V1")
    assert response.status_code == 200
    assert response.json()["daily_supply_charge"] == supply


def test_detail_404_before_the_first_version(client, versioned_tariff, monkeypatch):
    set_today(monkeypatch, date(2025, 6, 30))
    assert client.get("/api/v1/tariffs/energex/V1").status_code == 404


def test_list_shows_only_the_version_in_force(client, versioned_tariff, monkeypatch):
    set_today(monkeypatch, date(2026, 8, 1))
    listed = [t for t in client.get("/api/v1/tariffs/energex").json() if t["code"] == "V1"]
    assert [t["effective_from"] for t in listed] == ["2026-07-01"]


def test_history_returns_every_version_newest_first(client, versioned_tariff):
    history = client.get("/api/v1/tariffs/energex/V1/history").json()
    assert [t["effective_from"] for t in history] == ["2027-07-01", "2026-07-01", "2025-07-01"]


def test_current_rate_uses_the_version_in_force_at_the_requested_time(
    client, versioned_tariff, monkeypatch
):
    set_today(monkeypatch, date(2026, 8, 1))
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "V1", "datetime": "2026-01-15T12:00:00+10:00"},
    )
    assert response.json()["rate"] == OLD


@pytest.mark.parametrize(
    ("at", "rate"),
    [
        # 23:59 on 30 June and 00:30 on 1 July in Brisbane, each given in another offset.
        ("2026-06-30T13:59:00+00:00", OLD),
        ("2026-06-30T14:30:00+00:00", CURRENT),
        ("2026-07-01T00:30:00", CURRENT),  # no offset: DNSP local time
        ("2027-07-15T12:00:00+10:00", FUTURE),
    ],
)
def test_current_rate_selects_version_on_the_dnsp_local_date(client, versioned_tariff, at, rate):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "V1", "datetime": at},
    )
    assert response.status_code == 200
    assert response.json()["rate"] == rate


def test_current_rate_404_before_the_first_version(client, versioned_tariff):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "energex", "tariff": "V1", "datetime": "2025-06-30T12:00:00+10:00"},
    )
    assert response.status_code == 404


def test_current_rate_unknown_dnsp_is_404(client):
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "nope", "tariff": "T12A", "datetime": "2026-07-20T12:00:00+10:00"},
    )
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Demand windows use the version in force on each local date (#55)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def demand_versions():
    """Energex DW has 17:00-20:00 to 30 June 2026, then 18:00-21:00. DA is all day in both."""
    with Session(engine) as session:
        energex = session.query(Dnsp).filter_by(code="energex").one()
        for code, start, end, window_start, window_end in [
            ("DW", "2025-07-01", "2026-07-01", "17:00", "20:00"),
            ("DW", "2026-07-01", None, "18:00", "21:00"),
            ("DA", "2025-07-01", "2026-07-01", "00:00", "00:00"),
            ("DA", "2026-07-01", None, "00:00", "00:00"),
        ]:
            tariff = Tariff(
                dnsp_id=energex.id,
                code=code,
                name="Versioned demand",
                tariff_type="demand",
                effective_from=start,
                effective_to=end,
                daily_supply_charge=1.0,
            )
            session.add(tariff)
            session.flush()
            session.add(
                TariffDemand(
                    tariff_id=tariff.id,
                    rate=10.0,
                    window_start=window_start,
                    window_end=window_end,
                    measurement_method="peak_kw",
                )
            )
        session.commit()


def demand_windows_for(client, tariff: str, start: str, end: str):
    return client.get(
        "/api/v1/calculate/demand-windows",
        params={
            "dnsp": "energex",
            "tariff": tariff,
            "start": f"{start}T00:00:00+10:00",
            "end": f"{end}T00:00:00+10:00",
        },
    )


def window(day: str, start: str, end: str) -> dict:
    return {"start": f"{day}T{start}:00+10:00", "end": f"{day}T{end}:00+10:00"}


def test_demand_windows_use_the_version_of_the_requested_range(
    client, demand_versions, monkeypatch
):
    set_today(monkeypatch, date(2026, 8, 1))
    response = demand_windows_for(client, "DW", "2026-06-15", "2026-06-16")
    assert response.status_code == 200
    assert response.json()["windows"] == [window("2026-06-15", "17:00", "20:00")]


def test_demand_windows_use_a_version_not_yet_in_force_today(client, demand_versions, monkeypatch):
    set_today(monkeypatch, date(2026, 6, 1))
    response = demand_windows_for(client, "DW", "2026-08-03", "2026-08-04")
    assert response.json()["windows"] == [window("2026-08-03", "18:00", "21:00")]


def test_demand_windows_range_across_two_versions_uses_each_days_version(client, demand_versions):
    response = demand_windows_for(client, "DW", "2026-06-30", "2026-07-02")
    assert response.json()["windows"] == [
        window("2026-06-30", "17:00", "20:00"),
        window("2026-07-01", "18:00", "21:00"),
    ]


def test_demand_windows_merge_across_a_version_boundary(client, demand_versions):
    response = demand_windows_for(client, "DA", "2026-06-30", "2026-07-02")
    assert response.json()["windows"] == [
        {"start": "2026-06-30T00:00:00+10:00", "end": "2026-07-02T00:00:00+10:00"}
    ]


def test_demand_windows_404_when_no_version_covers_the_range(client, demand_versions):
    response = demand_windows_for(client, "DW", "2025-06-01", "2025-06-02")
    assert response.status_code == 404


def test_demand_windows_skip_days_before_the_first_version(client, demand_versions):
    response = demand_windows_for(client, "DW", "2025-06-30", "2025-07-02")
    assert response.json()["windows"] == [window("2025-07-01", "17:00", "20:00")]


def test_demand_windows_404_when_the_range_ends_as_the_first_version_starts(
    client, demand_versions
):
    assert demand_windows_for(client, "DW", "2025-06-20", "2025-07-01").status_code == 404


def test_demand_windows_unknown_tariff_is_404_before_bad_dates_are_400(client, demand_versions):
    response = client.get(
        "/api/v1/calculate/demand-windows",
        params={"dnsp": "energex", "tariff": "NOPE", "start": "bad", "end": "bad"},
    )
    assert response.status_code == 404
