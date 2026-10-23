---
scope: tariff-service
status: approved
priority: now
depends_on: []
tracking: ["tariff-service#36"]
---

# Demand Windows Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `GET /api/v1/calculate/demand-windows` returns a tariff's resolved demand windows for a time range, so no consumer interprets the `demand` object.

**Architecture:** One pure function in `app/services/rate_calculator.py` walks the local dates of the range and, for each date, emits the parts of that date where `is_in_demand_window` is true, using the same day, season and time rules. The router validates the range, loads the tariff and its DNSP's time zone, and serialises the merged windows.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pydantic, `zoneinfo`, pytest.

**Spec:** `OEC/governance/specs/2026-10-23-tariff-semantics-in-tariff-service-design.md`, section 1.

## Global Constraints

- Branch `feat/0.7.0`. Independent of #32, #24 and #22. No push without the security and PII review and the go-ahead (`.agent/context.md`, Remote).
- Range: `end > start`, `end - start <= 31 days`; both ISO 8601 with an offset.
- Windows are half-open `[start, end)`, clipped to the range, sorted, merged when adjacent or overlapping, in the DNSP's local offset.
- A tariff with no `demand` returns `windows: []`. Unknown tariff 404, as `/calculate/current-rate`.
- Window membership equals `is_in_demand_window` at every instant. That function is the single definition; the new function must not restate its rules.
- Tests use seed demand objects only (`seed/*.json`), loaded as `tests/test_seed_data.py` loads them.
- Before every commit: `ruff check .` and `pytest` pass (`.agent/pre-commit-rules.md`).

## Review Focus

- A range that starts or ends inside a window (17:30 to 18:30 in a 17:00 to 20:00 window): the window is clipped, not dropped. Test in Task 1.
- A range starting at a window's exact end instant: that window is absent (half-open). Test in Task 1.
- A naive datetime (no offset) in `start` or `end`: 400, not a server error. Test in Task 2.
- `start` and `end` with different offsets (`+10:00` and `+11:00`): compared as instants. Test in Task 2.
- A DNSP observing DST with an all-day window across the transition: one merged span whose end offset differs from its start offset. Test in Task 1.

---

### Task 1: `demand_windows` function

**Files:**
- Modify: `app/services/rate_calculator.py` (new function after `is_in_demand_window`)
- Create: `tests/test_demand_windows.py`

**Interfaces:**
- Consumes: `is_in_demand_window(demand, dt)`, `is_day_match`, `is_season_match`, `parse_time` (same module); `load_tariff(dnsp_file, code)` from `tests/test_seed_data.py`.
- Produces: `demand_windows(demand: TariffDemand | None, tz: ZoneInfo, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]`. Aware datetimes in `tz`, sorted, merged, clipped to `[start, end)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_demand_windows.py`, importing `load_tariff` from `tests.test_seed_data`. `BNE = ZoneInfo("Australia/Brisbane")`, `MEL = ZoneInfo("Australia/Melbourne")`.

```python
def test_weekday_window_skips_the_weekend():
    # Energex 3800: 17:00-20:00 weekdays, all months. 2026-10-23 is a Friday.
    d = load_tariff("energex", "3800").demand
    got = demand_windows(d, BNE, datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 27, tzinfo=BNE))
    assert got == [
        (datetime(2026, 10, 23, 17, tzinfo=BNE), datetime(2026, 10, 23, 20, tzinfo=BNE)),
        (datetime(2026, 10, 26, 17, tzinfo=BNE), datetime(2026, 10, 26, 20, tzinfo=BNE)),
    ]

def test_all_day_window_merges_into_one_span():
    # Energex 8300: 00:00-00:00 all.
    d = load_tariff("energex", "8300").demand
    s, e = datetime(2026, 10, 23, tzinfo=BNE), datetime(2026, 10, 30, tzinfo=BNE)
    assert demand_windows(d, BNE, s, e) == [(s, e)]

def test_season_months_exclude_out_of_season_days():
    # Evoenergy 023: 17:00-21:00 all, [6, 7, 8]. 31 Aug to 2 Sep.
    d = load_tariff("evoenergy", "023").demand
    syd = ZoneInfo("Australia/Sydney")
    got = demand_windows(d, syd, datetime(2026, 8, 31, tzinfo=syd), datetime(2026, 9, 2, tzinfo=syd))
    assert got == [(datetime(2026, 8, 31, 17, tzinfo=syd), datetime(2026, 8, 31, 21, tzinfo=syd))]

def test_range_inside_a_window_is_clipped():
    d = load_tariff("energex", "3800").demand
    s, e = datetime(2026, 10, 26, 17, 30, tzinfo=BNE), datetime(2026, 10, 26, 18, 30, tzinfo=BNE)
    assert demand_windows(d, BNE, s, e) == [(s, e)]

def test_range_starting_at_a_window_end_excludes_it():
    d = load_tariff("energex", "3800").demand
    s = datetime(2026, 10, 26, 20, tzinfo=BNE)
    assert demand_windows(d, BNE, s, s + timedelta(hours=2)) == []

def test_no_demand_is_empty():
    s = datetime(2026, 10, 23, tzinfo=BNE)
    assert demand_windows(None, BNE, s, s + timedelta(days=1)) == []

def test_dst_start_all_day_span_changes_offset():
    # Jemena A230: 00:00-00:00 all. Melbourne DST starts 2026-10-04 02:00.
    d = load_tariff("jemena", "A230").demand
    s, e = datetime(2026, 10, 1, tzinfo=MEL), datetime(2026, 10, 8, tzinfo=MEL)
    ((ws, we),) = demand_windows(d, MEL, s, e)
    assert ws.isoformat() == "2026-10-01T00:00:00+10:00"
    assert we.isoformat() == "2026-10-08T00:00:00+11:00"
```

Plus `test_matches_is_in_demand_window_every_minute`, parametrised over every `(dnsp_file, code)` in `seed/*.json` whose tariff has `demand`, with that DNSP's `timezone` from the seed file: for every minute `t` of `[2026-12-01, 2027-01-01)` local, `any(ws <= t < we for ws, we in windows) == is_in_demand_window(d, t)`. Repeat for `[2026-06-01, 2026-07-01)` so both seasons are covered.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_demand_windows.py -q`
Expected: FAIL, `ImportError: cannot import name 'demand_windows'`.

- [ ] **Step 3: Implement `demand_windows` in `app/services/rate_calculator.py`**

For each local date from `start.astimezone(tz).date()` to `end.astimezone(tz).date()` inclusive, skip the date unless `is_day_match` and `is_season_match` hold for it. Then take the date's in-window time ranges: `[00:00, next 00:00)` when `window_start == window_end`; `[ws, we)` when `ws < we`; `[00:00, we)` and `[ws, next 00:00)` when `ws > we`. Build each bound with `datetime.combine(date, t, tzinfo=tz)`; the next 00:00 is the following date's. Clip to `[start, end)`, drop empties, merge where one end equals or passes the next start. Docstring: membership equals `is_in_demand_window`.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_demand_windows.py -q && ruff check .`
Expected: all pass, `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add app/services/rate_calculator.py tests/test_demand_windows.py
git commit -m "feat: demand_windows resolves a tariff's demand windows over a range (#36)"
```

### Task 2: `/calculate/demand-windows` endpoint

**Files:**
- Modify: `app/schemas/tariff.py` (after `DemandSurchargeResponse`)
- Modify: `app/routers/calculate.py`
- Modify: `tests/test_api.py`
- Modify: `README.md` (endpoint table, lines 41-42), `CHANGELOG.md` (0.7.0 section, `### Added`)

**Interfaces:**
- Consumes: `demand_windows` (Task 1); `get_tariff_detail(db, dnsp, tariff)`; `Tariff.dnsp.timezone`.
- Produces, in `app/schemas/tariff.py`:
  - `DemandWindow(BaseModel)`: `start: str`, `end: str` (ISO 8601 with the DNSP's local offset), each with a `Field(description=...)`.
  - `DemandWindowsResponse(BaseModel)`: `dnsp: str`, `tariff: str`, `start: str`, `end: str` (as requested), `windows: list[DemandWindow]`.
- Route: `GET /api/v1/calculate/demand-windows`, query `dnsp`, `tariff`, `start`, `end` (all required), `response_model=DemandWindowsResponse`.

- [ ] **Step 1: Write the failing tests** in `tests/test_api.py`. The conftest fixture's Energex `T12A` demand object is not a seed shape, so these tests add the seed's Energex 3800 demand object (17:00-20:00, `weekdays`, `30min_avg`, rate 7.0) as a tariff `3800` in a local fixture.

```python
def test_demand_windows(client):
    r = client.get("/api/v1/calculate/demand-windows", params={
        "dnsp": "energex", "tariff": "3800",
        "start": "2026-10-23T00:00:00+10:00", "end": "2026-10-24T00:00:00+10:00"})
    assert r.status_code == 200
    assert r.json()["windows"] == [
        {"start": "2026-10-23T17:00:00+10:00", "end": "2026-10-23T20:00:00+10:00"}]

def test_demand_windows_unknown_tariff_404(client): ...      # tariff "nope" -> 404
def test_demand_windows_no_demand_is_empty(client): ...      # a fixture tariff without demand -> 200, []
def test_demand_windows_end_not_after_start_400(client): ... # start == end -> 400
def test_demand_windows_range_over_31_days_400(client): ...  # 31 days + 1 minute -> 400; exactly 31 days -> 200
def test_demand_windows_naive_datetime_400(client): ...      # "2026-10-23T00:00:00" -> 400
def test_demand_windows_mixed_offsets(client): ...           # start +10:00, end 2026-10-24T01:00:00+11:00 -> same windows as above
def test_openapi_documents_demand_windows(client): ...       # /openapi.json has the path; every DemandWindowsResponse property has a description
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_api.py -q -k demand_windows`
Expected: FAIL, 404 on the route.

- [ ] **Step 3: Add the schemas and the route.** Parse with `datetime.fromisoformat(value.replace(" ", "+"))`, as `current_rate` does. 400 when either value is invalid or has no `tzinfo`, when `end <= start`, or when `end - start > timedelta(days=31)`; each with a `detail` naming the rule. 404 text as `current_rate`'s. Windows serialised with `.isoformat()`. The route docstring states the half-open, clipped, merged form and the 31-day limit.

- [ ] **Step 4: Update the docs.** In `README.md`, add the row `| GET | /api/v1/calculate/demand-windows | Demand windows of a tariff over a time range |`. In `CHANGELOG.md`'s 0.7.0 section under `### Added`, add one line naming the endpoint and the 31-day limit.

- [ ] **Step 5: Run to verify pass**

Run: `pytest -q && ruff check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/tariff.py app/routers/calculate.py tests/test_api.py README.md CHANGELOG.md
git commit -m "feat: GET /calculate/demand-windows (#36)"
```
