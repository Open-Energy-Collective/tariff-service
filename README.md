# OEC Tariff Service

Open Energy Collective Tariff Data Service

## Overview

Public REST API serving curated Australian DNSP network tariff data. Free, unauthenticated, rate-limited. All data sourced from official AER-approved Network Price Lists.

## API

- **Base URL**: https://api.openenergy.org.au/api/v1/
- **Swagger UI**: https://api.openenergy.org.au/docs
- **OpenAPI spec**: https://api.openenergy.org.au/openapi.json

## Current DNSPs

| DNSP | State | Tariffs | Source |
|------|-------|---------|--------|
| Ausgrid | NSW | 16 | 2026-27 Network Price List |
| AusNet Services | VIC | 6 | 2026-27 Network Tariff Schedule |
| Endeavour Energy | NSW | 14 | 2026-27 NUOS Price List |
| Energex | QLD | 16 | 2026-27 Network Price List |
| Essential Energy | NSW | 9 | 2026-27 Price List & Explanatory Notes |
| Evoenergy | ACT | 5 | 2026-27 Schedule of Charges |
| Jemena | VIC | 6 | 2026-27 Network Tariff Schedule |
| Power and Water Corporation | NT | 7 | 2026-27 Network Tariffs |
| SA Power Networks | SA | 8 | 2026-27 Annual Pricing Proposal |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Service health check |
| GET | `/api/v1/dnsps` | List all DNSPs with tariff counts |
| GET | `/api/v1/tariffs/{dnsp}` | List all tariffs for a DNSP |
| GET | `/api/v1/tariffs/{dnsp}/{tariff}` | Get full tariff details |
| GET | `/api/v1/tariffs/{dnsp}/{tariff}/history` | Get tariff version history |
| GET | `/api/v1/calculate/current-rate` | Calculate active rate for a datetime |
| GET | `/api/v1/calculate/demand-surcharge` | Calculate demand surcharge for a peak kW |
| GET | `/api/v1/docs/demand-methodology` | Per-DNSP demand charge methodology |

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

## License

MIT
