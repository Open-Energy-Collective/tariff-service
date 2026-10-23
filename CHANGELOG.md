# Changelog

All notable changes to this project are documented here. Versioning follows
[VERSIONING.md](VERSIONING.md) (SemVer, pre-1.0). Retroactively reconstructed
2026-08-11 from git history for versions 0.2.0–0.6.0 — no tags existed before
that date (see `tariff-service@2486cff:.agent/status.md`'s 2026-08-11 entry).

## [0.7.0] - Unreleased

### Added
- `GET /api/v1/calculate/demand-windows`: the times a tariff's demand charge applies over a range of up
  to 31 days, in the distributor's local time.
- The API documentation lists the error responses of the calculate endpoints.

### Changed
- CitiPower, Powercor and United Energy tariffs name the AER indicative prices as their source.
- Tariffs with charges the service cannot yet represent (kVA demand, rolling 12-month peaks, a second
  seasonal rate, an extra demand charge) say so in their notes.

### Fixed
- `/api/v1/calculate/demand-surcharge`: `surcharge_per_kwh` now follows its documented formula,
  `demand_rate / demand_window_hours_per_month`, and no longer grows with peak demand. Window hours count
  only the days the window applies (a weekday-only window counts 5 days in 7). Reported values are
  lower, so a threshold set on the old figures needs resetting. `monthly_demand_charge` is unchanged.
- `/api/v1/calculate/current-rate` gives the same answer for the same moment in any UTC offset. Times are
  matched in the distributor's local time.
- 2026-27 prices and time windows corrected against the distributors' published price lists:
  - Ausgrid: EA302, EA305, EA310, EA370 and EA390 capacity charges apply on working weekdays all year.
  - AusNet: NASN12 demand window is 3pm to 9pm on weekdays, December to March.
  - CitiPower, Powercor, United Energy: business time-of-use off-peak covers weekends.
  - Energex: 3800, 3900, 6900 and 7200 time windows.
  - Essential Energy: demand tariffs' peak and demand window is 5pm to 8pm on weekdays.
  - Evoenergy: 101 off-peak and 060 controlled load rates.
  - Jemena: A180 rate and window; A10E export charge and reward.
  - Power and Water: T5 and T6 demand rates per month.
  - SA Power Networks: RTOU, SBTOU, RESELE and SBELE time periods and rates; MBTOUD and LBAD demand
    windows.

## [0.6.1] — 2026-08-11

### Fixed
- `seed/ausgrid.json`'s `EA029` export tariff was seeded in the wrong shape
  (matching `rates`' fields instead of `TariffExport`'s real `credit_rate`/
  `charge_rate` columns), so every field loaded as `null` in production.
  Corrected the entry, preserving the originally-sourced values.
- `app/services/rate_calculator.py`'s `is_day_match()` only recognized the
  singular `"weekday"`/`"weekend"`; real seed data uses the plural
  `"weekdays"`/`"weekends"`, so weekday-restricted rates on affected tariffs
  (e.g. Powercor's `CG` business peak rate) silently matched every day,
  weekends included.

### Added
- Loader-side guard in `seed/build_db.py`: an `exports` entry with neither
  `credit_rate` nor `charge_rate` now raises at seed-build time instead of
  silently producing an all-null row.
- `tests/test_rate_calculator.py` — no unit tests existed for
  `rate_calculator.py` before this.

## [0.6.0] — 2026-08-03

### Added
- CitiPower, Powercor, United Energy (VIC) DNSPs — 15 tariffs.

## [0.5.0] — 2026-07-27

### Added
- Swagger/OpenAPI examples, seasonal peak tests, 20 req/min per-IP rate limit.

### Changed
- Product rename; IP/license steering docs.

### Fixed
- All-day (`00:00`–`00:00`) window matching and a demand-surcharge
  division-by-zero.

## [0.4.0] — 2026-07-22

### Added
- Jemena + AusNet Services (VIC) DNSPs.

### Changed
- Docs cleanup.

## [0.3.0] — 2026-07-21

### Added
- Evoenergy (ACT) + Power and Water (NT) DNSPs.

## [0.2.0] — 2026-07-20

### Added
- Endeavour Energy + Essential Energy DNSPs.
- SA Power Networks DNSP.
- SemVer versioning strategy (`VERSION` file as single source of truth).
