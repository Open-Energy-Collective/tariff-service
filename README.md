# OEC Tariff Service

Open Energy Collective Tariff Data Service

## Overview

This service provides API access to electricity network tariff data from Australian Distribution Network Service Providers (DNSPs).

## API

- **Base URL**: https://api.openenergy.org.au/api/v1/
- **Current DNSPs**: Energex (QLD)

## Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/dnsps` - List DNSPs
- `GET /api/v1/tariffs/{dnsp}` - List tariffs for a DNSP
- `GET /api/v1/tariffs/{dnsp}/{tariff}` - Get tariff details
- `GET /api/v1/tariffs/{dnsp}/{tariff}/history` - Get tariff history
- `POST /api/v1/calculate/current-rate` - Calculate current rate
- `POST /api/v1/calculate/demand-surcharge` - Calculate demand surcharge

## Data Sources

See `DATA_SOURCES.md` for authoritative tariff data sources.

## Deployment

Deployed via GitHub Actions on push to `main`.

## License

MIT
