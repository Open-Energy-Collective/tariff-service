# Versioning Strategy

This project uses [Semantic Versioning](https://semver.org/) (SemVer).

## Version Format

```
MAJOR.MINOR.PATCH
```

## When to Increment

| Change Type | Increment | Examples |
|-------------|-----------|----------|
| **MAJOR** | Breaking API changes | Removing endpoints, renaming fields, changing response shapes |
| **MINOR** | New features (backwards-compatible) | New endpoints, new DNSPs, new response fields |
| **PATCH** | Bug fixes, docs, infra | Fix calculations, update docs, CI changes |

## Single Source of Truth

The version lives in one place: the `VERSION` file at the repo root.

All other references read from it:
- `pyproject.toml` — uses hatchling's `version` directive
- `app/main.py` — reads `VERSION` file at import time
- `/api/v1/health` — returns the same version
- OpenAPI spec — shows the same version

## Release Process

1. Update `VERSION` file with the new version number
2. Commit: `release: vX.Y.Z`
3. Merge to `main`
4. Tag: `git tag vX.Y.Z && git push --tags`
5. Deploy happens automatically (or manually if CI is down)

## Pre-1.0 Convention

While the API is in development (`0.x.x`):
- MINOR bumps may include breaking changes
- Once the API contract is stable and documented, tag `1.0.0`

## Current Version

See `VERSION` file.
