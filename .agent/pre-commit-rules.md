# tariff-service Rules

Adds tariff-service rules to the org rules. The org rules are the root `CLAUDE.md` and
`governance/`. This file overrides an org rule only as listed in Overrides below. Any other
disagreement between this file and an org rule is a finding for Architecture, and the org
rule governs until it is resolved. This file does not restate an org rule; it links it.

Org rules that apply to this repo:

| Topic | Org rule |
|---|---|
| Branching, release branches, milestone releases (tag format: Overrides) | `governance/branching-strategy.md` |
| Release notes in `CHANGELOG.md` | `governance/branching-strategy.md#milestone-releases` |
| Licences | `governance/licensing-standards.md` |
| Security and PII review before a public push or release | `governance/adr/cross-project.md#2026-10-21-manual-security-and-pii-review-before-a-public-push`, `governance/security-standards.md`, `governance/security-privacy-principles.md` |
| Naming | `governance/naming-standards.md` |
| Tracker calls, findings, write signature | `governance/agent-workflow.md` |
| Writing: no em dashes, banned words, Mermaid for flows | root `CLAUDE.md`, Stream Rules |

## Overrides

| Org rule | Replaced here by |
|---|---|
| `branching-strategy.md#milestone-releases`: tag the merge commit `vX.Y.Z` | Tag `X.Y.Z` without `v`, continuing tags `0.5.0` to `0.6.1`. Founder exception: `governance/adr/cross-project.md#2026-10-21-tariff-service-keeps-xyz-tags` |

## Before every commit

- `ruff check .` passes.
- `pytest` passes, and new behaviour has a test.
- `README.md` is updated when endpoints, DNSPs or features change.
- `DATA_SOURCES.md` is updated when DNSP data changes: source, time windows, tariff codes.
- Seed values cite the knowledge entry they were checked against
  (`knowledge/documents/<dnsp>/` in the OEC root).
- A new dependency declares MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC or LGPL. Any
  other licence, or none, stops the work until the founder decides.
- Code copied from an external source carries a comment at the point of use citing the
  source and its licence.

## Commit messages

- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `security:`, `release:`.
- A seed data commit names the DNSP and the tariff count in its body.

## Versioning and deploy

- `VERSION` is the single source of the version; `VERSIONING.md` gives the bump rules.
- `deploy.yml` deploys on every push to `main`. Tags mark releases for rollback; they do
  not gate deploys.
- After a deploy, check the live API returns the expected data.
