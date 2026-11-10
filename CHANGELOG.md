# Changelog

All notable changes to this project are documented here. Versioning follows
[VERSIONING.md](VERSIONING.md) (SemVer, pre-1.0). Retroactively reconstructed
2026-08-11 from git history for versions 0.2.0–0.6.0 — no tags existed before
that date (see `tariff-service@2486cff:.agent/status.md`'s 2026-08-11 entry).

## [0.9.1] - Unreleased

### Fixed
- 12 CitiPower, Powercor and United Energy tariffs (C1R, CDS, CGTOU, C1G, D1, DD1, NDTOU, ND1,
  LVS1R, LVDed, LVM1R, LVTOU) carry their approved 2026-27 rates and daily charges, replacing the
  January 2025 AER indicative figures. CitiPower C1R anytime is now 0.0909 $/kWh, was 0.087583.
  Windows are unchanged (#73).

## [0.9.0] - 2026-11-10

### Added
- Tariff detail: `demand_charges` (every demand charge, with seasons, `unit` kW or kVA and `peak_period`),
  `time_basis`, `prices_expected_until`, `public_holidays` on `rates` and `export`, and
  `free_threshold_period` and `free_threshold_rollover` on `export` (#31).
- `/api/v1/calculate/current-rate` returns `demand_charges`, each with `active`.
- `/api/v1/calculate/demand-windows` returns a `rate` on each window.
- Tariff detail `demand` gains `unit` (`kW` or `kVA`), the unit of the charge it is built from, and
  `/api/v1/calculate/demand-surcharge` gains `demand_unit`, the unit of `demand_rate`. `peak_demand_kw`
  keeps its name and is read in that unit (#71).

### Changed
- `/api/v1/calculate/current-rate` and `/api/v1/calculate/demand-windows` follow public holidays by the
  distributor's state where the tariff's windows exclude holidays (#56).
- Both endpoints judge windows on the tariff's `time_basis`. Jemena A180 is now correct during daylight saving (#56).
- `/api/v1/calculate/demand-windows` returns every demand charge in force, with higher rates taking overlaps.
  AusNet NASN12 now has its April to November rate of 2.862 $/kW/month.
- `/api/v1/docs/demand-methodology` `rate_unit` follows the tariff: `$/kVA/month` for a kVA tariff
  and `$/kW/month` for a kW tariff. Essential, Power and Water and SA Power Networks now read `$/kVA/month`,
  from the one tariff each DNSP's entry describes (#71).
- `/api/v1/docs/demand-methodology` words `measurement_explanation` by the tariff's unit: maximum apparent power
  (kVA) for a kVA tariff, unchanged for a kW tariff. The description says demand is measured in kW or kVA,
  as each tariff states (#77).
- `/api/v1/docs/demand-methodology` words `window` by the tariff's `time_basis`: `(local time)` for a `local`
  tariff, and the zone's standard time for a `standard` one. Evoenergy now reads `(AEST, standard time)` (#68).
- No field is removed or renamed. `demand` keeps its 0.8.0 fields and is due for removal in a later release. Read
  `demand_charges` instead.

### Fixed
- Every seeded demand charge is checked against its 2026-27 source. Endeavour's seven demand tariffs,
  Evoenergy 023 and Power and Water T5 and T6 gain their low-season or off-season charge, Evoenergy 023
  its 21:00-09:00 off-peak charge and SA Power Networks LBAD its anytime charge, so `in_demand_window`
  is true in those windows (#62).
- Ausgrid EA305, EA310, EA370 and EA390, Endeavour N19, N29 and N39, Energex 8300, Essential's five
  demand tariffs, Evoenergy 101, Power and Water T5 and T6 and SA Power Networks MBTOUD and LBAD are
  priced per kVA. Ausgrid EA302 to EA390, Jemena A230 and SA Power Networks MBTOUD and LBAD charge on
  the peak of the last 12 months. `demand` is unchanged for every tariff.
- CitiPower CRSTOU, Powercor PRSTOU and United Energy URSTOU carry their approved 2026-27 rates and
  daily charges, replacing the January 2025 AER indicative figures, and gain a `saver` period
  11:00-16:00 every day at 1.00 c/kWh. Off-peak is now 21:00-11:00 (#46).
- `/api/v1/calculate/demand-windows` agrees with `in_demand_window` when a window bound falls in the hour
  a daylight saving change skips or repeats. On a local clock a skipped time is in no window and a
  repeated time is in the window both times. No seeded window has such a bound, so no result changes (#63).
- Evoenergy 017, 023, 060, 090 and 101 run on standard time, as the 2026-27 schedule states its times in AEST.
  In daylight saving each window is one hour later on the Canberra clock: 101's peak and demand window is
  08:00-18:00 AEDT. SA Power Networks BSR also runs on standard time (Table 4: accumulation meter structures are based on ACST), so its 11 kWh/day free export allowance resets at 01:00 ACDT in daylight saving. Every other DNSP's source was checked and its remaining tariffs stay `local` (#68).

### Security
- `deploy.yml`'s test job runs with a read-only token (`contents: read`) (#74).

## [0.8.0] - 2026-11-09

### Breaking
- `/api/v1/calculate/current-rate`: `rate` can now be `null`, with `period` set to `none`, when no single
  rate is in force. This applies outside a tariff's rate windows (Jemena A180), to a tariff with no energy
  rates (Ausgrid EA029), and when the rate depends on consumption (Endeavour N90). These cases previously
  returned a rate that was not in force, or zero.
- `/api/v1/calculate/current-rate` uses the tariff version in force on the requested date, and returns 404
  for a date before a tariff's first version. It previously used today's version for every date.
- `/api/v1/calculate/demand-windows` uses the tariff version in force on each date in the range, and returns
  404 when any date in the range has no version.

### Fixed
- AusNet NASN12: the energy rate is now 16.796 c/kWh, replacing another tariff's value.
- AusNet RCER11 and seven SA Power Networks tariffs now include their export terms.
- `/api/v1/tariffs/{dnsp}` lists each tariff once when a newer version has started.

## [0.7.1] - 2026-10-24

### Changed
- Deployment pipeline updated; the API is unchanged.

## [0.7.0] - 2026-10-24

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
