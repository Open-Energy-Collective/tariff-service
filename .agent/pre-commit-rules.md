# Pre-Commit Checklist

Before committing and pushing any feature branch, verify ALL of the following:

## Documentation
- [ ] `README.md` — update if new endpoints, DNSPs, or features added
- [ ] `DATA_SOURCES.md` — update if new DNSP data added (include source URL, time windows, tariff codes)
- [ ] `VERSIONING.md` — bump `VERSION` file for any release-worthy change (MAJOR/MINOR/PATCH per its table)
- [ ] `CHANGELOG.md` — add an entry for the new version

## Release (whenever `VERSION` is bumped)
Added 2026-08-11 after finding this step had never actually happened despite
`VERSIONING.md` documenting it since `0.2.0` — zero tags existed until that day.
The missing step, not the doc, was the gap.
- [ ] `git tag X.Y.Z && git push --tags` after the bump lands on `main`
- [ ] Confirm the tag is on GitHub (`gh api repos/Open-Energy-Collective/tariff-service/tags`)
- Deploy is NOT tag-gated (`deploy.yml` deploys on every `main` push) — the tag is a
  historical/rollback marker, not a release trigger. Don't skip it because "it
  already deployed."

## Code Quality
- [ ] `ruff check .` passes with no errors
- [ ] `pytest` passes (all tests green)
- [ ] New features have tests (or existing tests still cover the change)

## Commit Message
- Follow conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `security:`, `release:`
- Include DNSP name and tariff count in commit body when adding seed data

## Branching Strategy
- Use **long-lived feature branches** for related work, named `feat/{version}` (e.g., `feat/0.5.0`)
- Multiple commits on the branch are fine — push as you go
- Only create a **single PR when the work is complete and tested**
- Do NOT rapid-fire multiple PRs in quick succession (triggers GitHub anti-abuse flags)
- **Squash merge** to main (clean single-commit history per release)
- Individual commit messages are preserved in the PR body on GitHub
- No `--admin` bypass unless absolutely necessary

## Deploy
- Can deploy manually from feature branch for testing before merge
- After merge to main, deploy (manually until GitHub Actions is restored)
- Verify the live API returns expected data after deploy

## Third-Party IP & License Compliance
- Before adding any new dependency: verify it declares one of the approved licenses
  (MIT, Apache-2.0, BSD-2/3-Clause, ISC, LGPL) — if its license is anything else,
  unclear, or missing, STOP and ask before adding it
- Before committing code copied from an external source (not a package dependency):
  add an attribution comment citing source + license at the point of use — no exceptions

## Security / PII scan before any release
This repo is real and public (`github.com/Open-Energy-Collective/tariff-service`) —
run `../.agent/scripts/security-scan.sh tariff-service` before cutting a release.
Process/checklist: `repos/.agent/security-scan.md`.
