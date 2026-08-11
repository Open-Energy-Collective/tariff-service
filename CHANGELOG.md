# Changelog

All notable changes to this project are documented here. Versioning follows
[VERSIONING.md](VERSIONING.md) (SemVer, pre-1.0). Retroactively reconstructed
2026-08-11 from git history for versions 0.2.0–0.6.0 — no tags existed before
that date (see `.agent/status.md`'s 2026-08-11 entry).

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
