# Pre-Commit Checklist

Before committing and pushing any feature branch, verify ALL of the following:

## Documentation
- [ ] `README.md` — update if new endpoints, DNSPs, or features added
- [ ] `DATA_SOURCES.md` — update if new DNSP data added (include source URL, time windows, tariff codes)
- [ ] `VERSIONING.md` — bump `VERSION` file if MINOR or MAJOR change

## Code Quality
- [ ] `ruff check .` passes with no errors
- [ ] `pytest` passes (all tests green)
- [ ] New features have tests (or existing tests still cover the change)

## Commit Message
- Follow conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `security:`, `release:`
- Include DNSP name and tariff count in commit body when adding seed data

## Branch Strategy
- Always work on a feature branch (never commit directly to main)
- PR title should be concise (<70 chars)
- Squash merge to main

## Deploy
- After merge, manually deploy if GitHub Actions is down
- Verify the live API returns expected data after deploy
