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
