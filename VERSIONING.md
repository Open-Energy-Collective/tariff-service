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
2. Commit: `release: X.Y.Z`
3. Merge to `main`
4. Tag: `git tag X.Y.Z && git push --tags`
5. Deploy happens automatically (or manually if CI is down)

Tags are a historical/rollback marker, not a deploy gate — `deploy.yml` deploys
on every push to `main` regardless of tags, deliberately kept simple rather than
tag-gated. Every version bump should still get a tag (step 4): this was written
from the start but not actually followed in practice until 2026-08-11 (`0.2.0`
through `0.6.0` were tagged retroactively that day, reconstructed from
`VERSION`-bump commits in git history — see `CHANGELOG.md`).

## Pre-1.0 Convention

While the API is in development (`0.x.x`):
- MINOR bumps may include breaking changes
- Once the API contract is stable and documented, tag `1.0.0`

## Current Version

See `VERSION` file.
