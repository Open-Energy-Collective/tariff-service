# OEC Tariff Data Service

Public REST API serving curated Australian DNSP tariff data.

## Overview

Provides tariff rates, demand charges, time-of-use periods, and seasonal variations for Australian Distribution Network Service Providers (DNSPs). Free, unauthenticated, rate-limited.

**Live API:** `https://api.openenergy.org.au/api/v1/`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dnsps` | List all DNSPs |
| GET | `/api/v1/tariffs/{dnsp}/{code}` | Get full tariff detail |
| GET | `/api/v1/calculate/current-rate` | Get active rate for given time |
| GET | `/api/v1/calculate/demand-surcharge` | Calculate demand surcharge |
| GET | `/docs` | Swagger UI (interactive API docs) |
| GET | `/openapi.json` | OpenAPI spec (machine-readable) |

## Local Development

```bash
# Install
pip install -e ".[dev]"

# Build local database from seed data
python seed/build_db.py

# Run
uvicorn app.main:app --reload

# Tests
pytest

# Lint
ruff check .
```

## Architecture

- **Runtime:** AWS Lambda + API Gateway (serverless)
- **Database:** SQLite (bundled with deployment)
- **Framework:** FastAPI + Mangum
- **Cost:** ~$0/month (within AWS free tier)

## Data Updates

Tariff data is seeded from JSON files in `seed/`. To update:

1. Edit the relevant JSON file in `seed/`
2. Run `python seed/build_db.py`
3. Commit and push — CI/CD deploys automatically

## License

MIT — Open Energy Collective Pty Ltd (ACN 700 429 429)
# Test deploy trigger
