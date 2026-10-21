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
- `pyproject.toml`. Uses hatchling's `version` directive.
- `app/main.py`. Reads the `VERSION` file at import time.
- `/api/v1/health`. Returns the same version.
- OpenAPI spec. Shows the same version.

## Release Process

Each release is a GitHub milestone `feat/X.Y.Z` worked on its own release branch of the
same name.

1. Cut `feat/X.Y.Z` from `main` at the previous release's merge commit.
2. Commit work directly to `feat/X.Y.Z`. CI runs the tests on every push.
3. On the release branch, set `VERSION` to `X.Y.Z` and add the `X.Y.Z` section to
   `CHANGELOG.md`. The maintainer approves the release notes before they are pushed.
4. Close the milestone's issues and the milestone.
5. Merge `feat/X.Y.Z` into `main` with one pull request. The push to `main` deploys.
6. Tag the merge commit and push the tag:
   ```bash
   git tag -a X.Y.Z <merge-commit> -m "feat/X.Y.Z: <capability>"
   git push origin X.Y.Z
   ```
7. Cut the next release branch from `main` at that merge commit.

Tags have no `v` prefix (`0.6.1`, `0.7.0`). Tags mark releases for rollback; `deploy.yml`
deploys on every push to `main` and is not tag-gated.

## Pre-1.0 Convention

While the API is in development (`0.x.x`):
- MINOR bumps may include breaking changes
- Once the API contract is stable and documented, tag `1.0.0`

## Current Version

See `VERSION` file.
