# tariff-service, Repo Context

Points at this repo's data, rules and tracker. Adds to the org rules (root `CLAUDE.md` and
`governance/`), overriding one only as listed in `.agent/pre-commit-rules.md`, Overrides.

## Data and sources

- Seed data: `seed/*.json`, built into SQLite by `seed/build_db.py`.
- Source per DNSP: `DATA_SOURCES.md`.
- The 2026-27 DNSP price lists are captured in the OEC knowledge base under
  `knowledge/documents/<dnsp>/`. Known seed errors and schema gaps:
  `knowledge/findings/2026-10-21-tariff-service-seed-audit-2026-27.md`.
- Repo rules: `.agent/pre-commit-rules.md`. Build state: `.agent/status.md`.

## Work tracking

GitHub milestones `feat/X.Y.Z` and issues on `Open-Energy-Collective/tariff-service`, plus
`BACKLOG.md` at the OEC root. `/next-build` reads both. Tracker calls go through
`tooling/github-api`.

## Remote

`https://github.com/Open-Energy-Collective/tariff-service` (public). Every push needs the
manual security and PII review (`.agent/pre-commit-rules.md`) and the founder's go-ahead.
The `oec-agent` token cannot push changes under `.github/workflows/`; the founder pushes
those with their own token.
