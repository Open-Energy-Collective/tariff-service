# Tariff Data Service

Open Energy Collective Tariff Data Service

## Overview

Public REST API serving curated Australian DNSP network tariff data, including time-of-use rates and per-DNSP demand charge calculations. Free, unauthenticated, rate-limited. All data sourced from official AER-approved Network Price Lists.

## API

- **Base URL**: https://api.openenergy.org.au/api/v1/
- **Swagger UI**: https://api.openenergy.org.au/docs
- **OpenAPI spec**: https://api.openenergy.org.au/openapi.json

## Current DNSPs

| DNSP | State | Tariffs | Source |
|------|-------|---------|--------|
| Ausgrid | NSW | 16 | 2026-27 Network Price List |
| AusNet Services | VIC | 6 | 2026-27 Network Tariff Schedule |
| CitiPower | VIC | 5 | 2026-27 Pricing + Tariff Summary |
| Endeavour Energy | NSW | 14 | 2026-27 NUOS Price List |
| Energex | QLD | 16 | 2026-27 Network Price List |
| Essential Energy | NSW | 9 | 2026-27 Price List & Explanatory Notes |
| Evoenergy | ACT | 5 | 2026-27 Schedule of Charges |
| Jemena | VIC | 6 | 2026-27 Network Tariff Schedule |
| Powercor | VIC | 5 | 2026-27 Pricing + Tariff Summary |
| Power and Water Corporation | NT | 7 | 2026-27 Network Tariffs |
| SA Power Networks | SA | 8 | 2026-27 Annual Pricing Proposal |
| United Energy | VIC | 5 | 2026-27 Pricing + AER SCS Pricing Model |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/dnsps` | List all DNSPs with tariff counts |
| GET | `/api/v1/tariffs/{dnsp}` | List all tariffs for a DNSP |
| GET | `/api/v1/tariffs/{dnsp}/{tariff}` | Get full tariff details |
| GET | `/api/v1/tariffs/{dnsp}/{tariff}/history` | Get tariff version history |
| GET | `/api/v1/calculate/current-rate` | Calculate active rate for a datetime |
| GET | `/api/v1/calculate/demand-surcharge` | Calculate demand surcharge for a peak demand in the tariff's unit (kW or kVA) |
| GET | `/api/v1/calculate/demand-windows` | Demand windows of a tariff over a time range (at most 31 days) |
| GET | `/api/v1/docs/demand-methodology` | Per-DNSP demand charge methodology |

`/api/v1/calculate/current-rate` returns `period: "none"` and `rate: null` when no single rate is
in force: the time is outside the tariff's rate windows, the tariff has no energy rates, or the
rate depends on consumption.

### Tariff detail fields

`GET /api/v1/tariffs/{dnsp}/{tariff}` returns these fields in addition to the rates and export terms:

| Field | Meaning |
|---|---|
| `demand_charges` | Every demand charge of the tariff. Each has `period`, `rate` ($ per `unit` per month), `unit` (`kW` or `kVA`), `start`, `end`, `days`, `public_holidays`, `months` (null is all year), `measurement_method` and `peak_period` (`month` or `rolling_12_months`). Empty when the tariff has none |
| `demand` | The highest-rate charge, a tie going to the earliest start, with that charge's `unit` (`kW` or `kVA`). Null when the tariff has no demand charge. Its 0.8.0 fields are unchanged and a later release removes it. Read `demand_charges` instead |
| `time_basis` | `local` (daylight saving applies) or `standard` (standard time all year). Applies to every energy, demand and export window of the tariff |
| `prices_expected_until` | Date until which the prices are expected to hold, or null. Informational. It does not change which version is in force |
| `rates[].public_holidays`, `export[].public_holidays` | `included` or `excluded`, or null for an all-days window. Whether a weekday or weekend window applies on a public holiday |
| `export[].free_threshold_period`, `export[].free_threshold_rollover` | The period the free export allowance is counted over (`day` or `year`), and whether unused allowance carries over (`none`, `billing_period`, `billing_period_like_days`). Both are null when there is no allowance |

`tariff_type` does not indicate exports. Read the `export` list. The service describes export
allowances and does not calculate export charges in dollars.

`/api/v1/calculate/current-rate` also returns `demand_charges`: every charge whose `months` cover the
date, each with `period`, `rate`, `unit`, `peak_period` and `active`. `active` is true only inside the
charge's window, and `in_demand_window` is true when any entry is active.

`/api/v1/calculate/demand-surcharge` reads `peak_demand_kw` in the tariff's demand unit and returns
`demand_unit` (`kW` or `kVA`), the unit of `demand_rate`. The parameter keeps its name. A tariff with
no demand charge returns 400. `/api/v1/docs/demand-methodology` gives `rate_unit` as `$/kW/month` or
`$/kVA/month`, following the tariff it describes.

`/api/v1/calculate/demand-windows` returns every demand charge in force, and each window has a `rate`.
Where charges overlap, the higher rate takes the stretch. Adjacent stretches merge only at an equal rate.
Each date uses the version in force that date.

Windows, months and public holidays are judged on the tariff's `time_basis` clock. A request with no UTC
offset is read on the distributor's local clock.

## Data Sources

See `DATA_SOURCES.md` for authoritative tariff data sources and methodology notes.

## Tech Stack

- **Runtime**: Python 3.12, FastAPI, SQLAlchemy, SQLite
- **Infrastructure**: AWS Lambda, API Gateway (HTTP API), SAM
- **CI/CD**: GitHub Actions (test on PR, deploy on merge to main)
- **Secrets**: JWT secret in AWS SSM Parameter Store

## Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Build database from seed data
python seed/build_db.py

# Run tests
pytest --cov=app

# Run locally
uvicorn app.main:app --reload
```

## Deployment

Deployed via GitHub Actions on push to `main`. Manual deploy:

```bash
python seed/build_db.py
sam build --template-file infra/template.yaml
sam deploy --template-file .aws-sam/build/template.yaml \
  --stack-name oec-tariff-service \
  --region ap-southeast-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset
```

A non-live stack for testing deploy changes takes `Environment=trial`: no custom domain,
certificate or DNS records, and an alarm named after the stack. Remove it when done.

```bash
sam deploy --template-file .aws-sam/build/template.yaml \
  --stack-name oec-tariff-service-trial \
  --parameter-overrides Environment=trial \
  --region ap-southeast-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
sam delete --stack-name oec-tariff-service-trial --region ap-southeast-2
```

## License

MIT
