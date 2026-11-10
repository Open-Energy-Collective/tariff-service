---
scope: tariff-service
status: done
priority: now
depends_on: []
tracking: ["tariff-service#31", "tariff-service#56"]
---

# Demand Model and Time Basis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a tariff holds several demand charges, a time basis, public holiday rules and an expected price end date, and every calculated answer uses them, with no existing response field removed.

**Architecture:** `tariff_demand_charge` replaces `tariff_demand`, and `Tariff.demand` becomes a property returning the highest-rate charge, so existing readers keep working. One module, `window_match.py`, decides whether a window applies at an instant, using a `TariffClock` and a holiday lookup. Endpoints gain fields and lose none.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite seed, pytest, `holidays==0.108` (MIT, checked 2026-11-09).

**Spec:** `docs/superpowers/specs/2026-11-09-demand-model-and-time-basis-design.md`

## Global Constraints

- Run from `build/tariff-service` with `.venv/bin/`. Before every commit: `ruff check .` and `pytest` pass.
- No existing response field is removed or renamed in 0.9.0.
- Allowed values: `time_basis` `local|standard`; `public_holidays` `included|excluded`; `days` `all|weekdays|weekends`; `unit` `kW|kVA`; `peak_period` `month|rolling_12_months`; demand `period` `peak|shoulder|off_peak|anytime`; `free_threshold_period` `day|year`; `free_threshold_rollover` `none|billing_period|billing_period_like_days`.
- A seed data commit names the DNSP and the tariff count in its body. Changed seed values cite their `knowledge/documents/<dnsp>/` entry.
- Conventional commits, no Claude attribution, no em dashes. `Refs`, never `Closes`.
- Build does not push. Each push needs the security and PII review and the maintainer's go-ahead.

## Review Focus

1. A daylight saving changeover day on a `standard` tariff: no gap or doubled window. Test in Task 5.
2. An overnight window crossing into a public holiday: each date is judged alone, as today, so 03:00 on a holiday follows that date's marker. Test in Task 3.
3. A range crossing a tariff version change where the rate differs: windows do not merge across it. Test in Task 5.
4. A request with no offset on a `standard` tariff: read on the local clock, then converted. Test in Task 4.
5. A DNSP state the holiday library does not know: the seed load fails, not a request. Test in Task 2.

---

### Task 1: Data model and seed migration

**Files:**
- Modify: `app/models/tariff.py`, `seed/build_db.py`, `seed/*.json`, `app/services/rate_calculator.py`, `app/services/tariff_service.py`, `app/routers/tariffs.py`, `app/routers/docs.py`
- Modify tests that build `TariffDemand`: `tests/conftest.py`, `tests/test_api.py`, `tests/test_rate_calculator.py`, `tests/test_seed_data.py`, `tests/test_seed_integrity.py`, `tests/test_demand_windows.py`
- Create: `tests/test_demand_model.py`, `tests/fixtures/demand_0_8_0.json`

**Interfaces:**
- Produces: `TariffDemandCharge` with columns `tariff_id, period, rate, unit, start, end, days, public_holidays, months, measurement_method, peak_period`. `months` is JSON text, as `season_months` was.
- Produces: `Tariff.time_basis: str`, `Tariff.prices_expected_until: str | None`, `Tariff.demand_charges: list[TariffDemandCharge]`.
- Produces: `Tariff.demand -> TariffDemandCharge | None`, a property: highest `rate`, tie to earliest `start`.
- Produces: `public_holidays` on `TariffRate` and `TariffExport`; `free_threshold_period`, `free_threshold_rollover` on `TariffExport`.
- Produces: `validate_tariff_fields(seed_files: list[dict]) -> None` in `seed/build_db.py`.

- [ ] **Step 1: Capture the 0.8.0 responses, before any change.** With a throwaway script against the current code, write `tests/fixtures/demand_0_8_0.json`: `{"demand": {"<dnsp>/<code>": <the demand object or null>}, "methodology": <the /api/v1/docs/demand-methodology response>}` for every seeded tariff.

- [ ] **Step 2: Write the failing tests in `tests/test_demand_model.py`**

```python
def test_demand_object_matches_0_8_0_for_every_tariff(seed_client): ...
    # every tariff's /tariffs response "demand" == fixture, no exceptions
def test_demand_methodology_matches_0_8_0(seed_client): ...
def test_demand_object_is_highest_rate_charge_tie_to_earliest_start(): ...
def test_nasn12_has_both_seasons(seed_session):
    # months [12,1,2,3] rate 11.473; months [4..11] rate approx(2.862, abs=0.001)
def test_a180_is_standard_time(seed_session): ...
def test_prices_expected_until_on_every_last_version(seed_session):
    # every tariff's last version == "2027-07-01"
@pytest.mark.parametrize("mutation, message", [...])
def test_seed_load_rejects(mutation, message):
    # no time_basis; no public_holidays where days != all; unknown days;
    # kW and kVA in one tariff; threshold with no free_threshold_period
```

- [ ] **Step 3: Run them.** `.venv/bin/pytest tests/test_demand_model.py -q`. Expected: FAIL, `demand_charges` not defined.

- [ ] **Step 4: Change the models.** Delete `TariffDemand`. Keep `Tariff.demand` as the property above and add a `demand_charges` relationship. Replace `joinedload(Tariff.demand)` with `joinedload(Tariff.demand_charges)`. Point `rate_calculator`, `routers/tariffs.py` and `routers/docs.py` at the new names (`start`, `end`, `months`), with no behaviour change. In `routers/docs.py` join `TariffDemandCharge`.

- [ ] **Step 5: Migrate the seeds with a throwaway script, using the spec's Seed migration table.** `demand` becomes a one-entry `demand_charges`, or `[]` for null. `public_holidays` is written where `days` is not `all`. `prices_expected_until` is set on tariffs with no `effective_to`. Remove the file-level `metadata.effective_to`. Add NASN12's April to November charge, citing `knowledge/documents/ausnet/2026-10-21-network-tariff-schedule-2026-27`, and remove its schema gap `notes` text. Set A180 to `standard`.

- [ ] **Step 6: Update `populate` and add `validate_tariff_fields`,** called wherever `validate_tariff_versions` is. Update the tests that build `TariffDemand` to `TariffDemandCharge`.

- [ ] **Step 7: Run everything.** `.venv/bin/ruff check . && .venv/bin/pytest -q`. Expected: pass. `test_demand_tariff_schema_gap` for NASN12 stays xfail until Task 4.

- [ ] **Step 8: Commit** with `feat: store demand charges, time basis and expected price end date`, body naming every DNSP and the tariff count (102), `Refs #31, #56, #61`.

### Task 2: Public holiday lookup

**Files:**
- Create: `app/services/public_holidays.py`, `tests/test_public_holidays.py`
- Modify: `pyproject.toml`, `requirements.txt`, `seed/build_db.py`

**Interfaces:**
- Produces: `is_public_holiday(state: str, day: date) -> bool`, cached per state and year.
- Produces: `is_known_state(state: str) -> bool`, used by `validate_tariff_fields`.

- [ ] **Step 1: Write the failing tests**

```python
def test_christmas_every_seeded_state(): ...  # NSW VIC QLD SA ACT NT, date(2026,12,25)
def test_melbourne_cup_is_victoria_only():
    assert is_public_holiday("VIC", date(2026, 11, 3)) is True
    assert is_public_holiday("NSW", date(2026, 11, 3)) is False
def test_ordinary_day_is_not_a_holiday(): ...
def test_seed_load_rejects_unknown_state(): ...
```

- [ ] **Step 2: Run them.** Expected: FAIL, module not found.

- [ ] **Step 3: Implement with `holidays.country_holidays("AU", subdiv=state, years=day.year)`.** Add `holidays==0.108` to `pyproject.toml` dependencies and `requirements.txt`. Confirm the licence reads MIT.

- [ ] **Step 4: Run all tests.** Expected: pass.

- [ ] **Step 5: Commit** with `feat: look up public holidays by DNSP state`, `Refs #31`.

### Task 3: One window matching routine

**Files:**
- Create: `app/services/window_match.py`, `tests/test_window_match.py`
- Modify: `app/services/rate_calculator.py` (remove the "unrecognised means every day" return from `is_day_match`, and the singular day forms)

**Interfaces:**
- Consumes: `is_public_holiday`.
- Produces: `TariffClock(zone: ZoneInfo, basis: str, state: str)`, a frozen dataclass, with `TariffClock.wall(instant: datetime) -> datetime` (naive time on the tariff's clock; the instant must be aware) and `TariffClock.instant(day: date, t: time) -> datetime` (aware, UTC).
- Produces: `day_applies(days: str, public_holidays: str | None, day: date, state: str) -> bool`.
- Produces: `window_applies(start: str, end: str, days: str, public_holidays: str | None, months: list[int] | None, clock: TariffClock, instant: datetime) -> bool`.

`standard` uses `zone.utcoffset(d) - zone.dst(d)` as a fixed offset.

- [ ] **Step 1: Write the failing tests**

```python
MELB_STD = TariffClock(ZoneInfo("Australia/Melbourne"), "standard", "VIC")
MELB_LOCAL = TariffClock(ZoneInfo("Australia/Melbourne"), "local", "VIC")

def test_standard_clock_is_an_hour_behind_in_daylight_saving():
    i = datetime(2026, 11, 11, 7, 30, tzinfo=timezone(timedelta(hours=11)))
    assert MELB_STD.wall(i).time() == time(6, 30)
def test_standard_and_local_agree_in_winter(): ...
def test_standard_date_comes_from_the_standard_clock():
    # 00:30+11:00 on 12 Nov is 23:30 on 11 Nov standard
def test_queensland_standard_matches_local(): ...
def test_excluded_weekday_window_off_on_holiday(): ...
def test_included_weekday_window_on_on_holiday(): ...
def test_all_days_window_ignores_marker(): ...
def test_overnight_window_judges_each_date_alone():
    # 23:00-07:00 weekdays excluded: 03:00 on Christmas Day 2026 (Fri) False,
    # 23:30 on 24 Dec (Thu) True
def test_unknown_days_raises_value_error(): ...
```

- [ ] **Step 2: Run them.** Expected: FAIL, module not found.

- [ ] **Step 3: Implement.** Time matching reuses `is_in_time_window`.

- [ ] **Step 4: Run all tests.** Expected: pass.

- [ ] **Step 5: Commit** with `feat: match every window on the tariff's clock with public holidays`, `Refs #31, #56`.

### Task 4: `/calculate/current-rate`

**Files:**
- Modify: `app/services/rate_calculator.py`, `app/routers/calculate.py`, `app/schemas/tariff.py`, `tests/test_demand_tariffs.py`, `tests/test_rate_calculator.py`
- Test: `tests/test_current_rate_model.py`

**Interfaces:**
- Consumes: `TariffClock`, `window_applies`.
- Produces: `clock_for(tariff: Tariff) -> TariffClock` in `window_match.py`.
- Produces: `get_current_rate(tariff: Tariff, instant: datetime) -> tuple[str, float | None]`, instant aware.
- Produces: `demand_charges_at(tariff: Tariff, instant: datetime) -> list[tuple[TariffDemandCharge, bool]]`, every charge in season with whether it is active.
- Produces: schema `DemandChargeInForce(period, rate, unit, peak_period, active)`. `CurrentRateResponse.demand_charges: list[DemandChargeInForce]`.

`is_in_demand_window` is deleted. `in_demand_window` is `any(active)`. In the router a naive datetime gets the DNSP zone attached before any conversion. The version is still chosen by the DNSP's local date.

- [ ] **Step 1: Write the failing tests**

```python
# NASN12, Melbourne: 2026-11-11 is a Wednesday
@pytest.mark.parametrize("when, rate, active", [
    ("2026-11-11T10:00:00+11:00", 2.862, False),
    ("2026-11-11T17:00:00+11:00", 2.862, True),
    ("2026-12-09T17:00:00+11:00", 11.473, True),
])
def test_nasn12_charge_in_force(seed_client, when, rate, active): ...
def test_nasn12_season_boundary(seed_client): ...  # 31 March 11.473, 1 April 2.862
def test_a180_07_30_daylight_saving_is_off_peak(seed_client):
    # 2026-11-11T07:30:00+11:00 -> off_peak, 0.04252
def test_a180_23_30_daylight_saving_is_none(seed_client):
    # 2026-11-11T23:30:00+11:00 -> none, null
def test_a180_winter_unchanged(seed_client): ...
def test_a180_no_offset_is_local_clock(seed_client):
    # 2026-11-11T07:30:00 -> off_peak
def test_christmas_ausgrid_ea302(seed_client):
    # 2026-12-25T17:00:00+11:00 -> off_peak, in_demand_window False
def test_christmas_powerwater_t5(seed_client):
    # 2026-12-25T17:00:00+09:30 -> in_demand_window True
def test_melbourne_cup_citipower_not_ausgrid(seed_client):
    # 2026-11-03T17:00:00+11:00: CGTOU off_peak; Ausgrid EA302 peak
def test_out_of_season_charge_not_listed(seed_client):
    # EA251 in May -> demand_charges == []
```

- [ ] **Step 2: Run them.** Expected: FAIL, no `demand_charges` key.

- [ ] **Step 3: Implement.** Remove the xfail from the NASN12 case. Re-point the other six `schema_gap` reasons from `#31:` to `#62:`, as the model now holds them and the data does not.

- [ ] **Step 4: Run all tests.** Expected: pass, 9 xfailed.

- [ ] **Step 5: Commit** with `feat: report demand charges in force and resolve rates on the tariff's clock`, `Refs #31, #56`.

### Task 5: `/calculate/demand-windows`

**Files:**
- Modify: `app/services/rate_calculator.py`, `app/services/tariff_service.py`, `app/routers/calculate.py`, `app/schemas/tariff.py`, `tests/test_demand_windows.py`

**Interfaces:**
- Consumes: `TariffClock`, `clock_for`, `window_applies`, `day_applies`.
- Produces: `demand_windows(tariff: Tariff, start: datetime, end: datetime) -> list[tuple[datetime, datetime, float]]`, returning `(start, end, rate)`, aware, half-open, clipped, sorted.
- Produces: `demand_windows_in_force` returns the same triple. `DemandWindow.rate: float`.

Each day on the tariff's clock produces each charge's parts. Sweep the sorted boundaries, give each stretch the highest rate covering it, then merge neighbours at an equal rate, across version boundaries too. A charge with `start` equal to `end` is the whole day.

- [ ] **Step 1: Write the failing tests.** Update `test_matches_is_in_demand_window_every_minute` to compare with `any(active)` from `demand_charges_at`, and add a standard-time case.

```python
def test_peak_over_shoulder_splits_into_three_stretches(): ...
    # synthetic: shoulder 07-22 at 3.0, peak 17-20 at 9.0
    # -> (07,17,3.0), (17,20,9.0), (20,22,3.0)
def test_anytime_under_peak_splits_the_day(): ...
def test_adjacent_equal_rates_merge(): ...
def test_nasn12_has_windows_in_both_seasons(seed_client): ...
def test_standard_tariff_on_changeover_day_has_no_gap_or_double():
    # synthetic standard 23:00-07:00, Melbourne, 2026-10-03 to 2026-10-05
def test_version_change_with_new_rate_does_not_merge(): ...
def test_uncovered_date_still_404(seed_client): ...
```

- [ ] **Step 2: Run them.** Expected: FAIL.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run all tests.** Expected: pass.

- [ ] **Step 5: Commit** with `feat: return every demand charge's windows with their rates`, `Refs #31, #56`.

### Task 6: Tariff detail response

**Files:**
- Modify: `app/schemas/tariff.py`, `app/routers/tariffs.py`, `tests/test_api.py`

**Interfaces:**
- Produces: schema `DemandChargeResponse` with the spec's fields, `months` as a list.
- Produces on `TariffDetailResponse`: `demand_charges`, `time_basis`, `prices_expected_until`. On `TariffRateResponse` and `TariffExportResponse`: `public_holidays`. On `TariffExportResponse`: `free_threshold_period`, `free_threshold_rollover`.

- [ ] **Step 1: Write the failing tests**

```python
def test_detail_has_demand_charges_and_keeps_demand(seed_client): ...  # NASN12
def test_detail_time_basis_and_prices_expected_until(seed_client): ...
def test_export_rollover(seed_client):
    # sapn RSR billing_period; SBTOU billing_period_like_days; ausnet RCER11 none; all period day
def test_changing_prices_expected_until_keeps_version_in_force(): ...
def test_tariff_type_description_says_read_export(): ...
```

- [ ] **Step 2: Run them.** Expected: FAIL.

- [ ] **Step 3: Implement,** and state in the `tariff_type` descriptions that it does not indicate exports.

- [ ] **Step 4: Run all tests.** Expected: pass.

- [ ] **Step 5: Commit** with `feat: publish demand charges, time basis and export allowance terms`, `Refs #31, #56, #61`.

### Task 7: Documentation

**Files:**
- Modify: `README.md`, `DATA_SOURCES.md`, `CHANGELOG.md`

- [ ] **Step 1: Update `README.md`** with the new response fields and `demand-windows` `rate`. Update `DATA_SOURCES.md` with the time basis, NASN12's two seasons and the public holiday source.

- [ ] **Step 2: Add to the 0.9.0 `CHANGELOG.md` section,** under Changed, the three behaviour changes in the spec's Rollout. State that no field is removed and that `demand` is due for removal in a later release.

- [ ] **Step 3: Verify.** `.venv/bin/ruff check . && .venv/bin/pytest -q`. Expected: pass, 9 xfailed.

- [ ] **Step 4: Commit** with `docs: describe the demand model and time basis`, `Refs #31, #56`.
