"""API endpoint tests."""


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
    # 4.5 * 7.434 / 150 = 0.22302
    assert abs(data["surcharge_per_kwh"] - 0.22302) < 0.001


def test_demand_surcharge_high_demand(client):
    """Higher demand should produce proportionally higher surcharge."""
    response = client.get(
        "/api/v1/calculate/demand-surcharge",
        params={"dnsp": "energex", "tariff": "T12A", "peak_demand_kw": 10.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["peak_demand_kw"] == 10.0
    assert data["monthly_demand_charge"] == 74.34
    # 10 * 7.434 / 150 = 0.4956
    assert abs(data["surcharge_per_kwh"] - 0.4956) < 0.001


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
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2026-04-20T18:00:00+10:00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.05357


def test_ausgrid_off_peak_in_may(client):
    """May 17:00 is off-peak (May is shoulder month, no peak)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "ausgrid", "tariff": "EA025", "datetime": "2026-05-15T17:00:00+10:00"},
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
        params={"dnsp": "ausgrid", "tariff": "EA116", "datetime": "2026-04-20T18:00:00+10:00"},
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
# SA Power Networks — Solar Sponge + Peak 17:00-21:00
# ─────────────────────────────────────────────────────────────────────────────


def test_sapn_peak(client):
    """19:00 should be peak (17:00-21:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T19:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "peak"
    assert data["rate"] == 0.2133


def test_sapn_solar_sponge(client):
    """12:00 should be solar_sponge (10:00-15:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T12:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "solar_sponge"
    assert data["rate"] == 0.0535


def test_sapn_shoulder(client):
    """08:00 should be shoulder (06:00-10:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T08:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "shoulder"
    assert data["rate"] == 0.1067


def test_sapn_off_peak(client):
    """03:00 should be off-peak (01:00-06:00)."""
    response = client.get(
        "/api/v1/calculate/current-rate",
        params={"dnsp": "sapn", "tariff": "RTOU", "datetime": "2026-07-20T03:00:00+09:30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "off_peak"
    assert data["rate"] == 0.0535
