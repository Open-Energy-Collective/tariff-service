# Build Session Status Log

## 2026-08-11 — Release process gap closed: VERSIONING.md's tagging step had never actually run

Founder asked directly why there was no release tag despite `VERSION` sitting at
`0.6.0` and `VERSIONING.md` documenting a tag-per-version process since `0.2.0`
(#9). Checked: `git tag -l` was completely empty, no GitHub Releases either — the
doc's step 4 (`git tag X.Y.Z && git push --tags`) had never once been executed,
for any version, in this repo's whole history. `VERSION` bumps themselves were
happening (bundled into unrelated feature PRs rather than the doc's own prescribed
dedicated `release: X.Y.Z` commit), just never followed by the tag.

**Fixed**: retroactively tagged `0.2.0` through `0.6.0` at the actual commits
where `VERSION` changed (reconstructed from git history, not guessed — see each
tag's commit). Added `CHANGELOG.md`, backfilled from real commit messages for the
same range. Added a "Release" section to `.agent/pre-commit-rules.md` so the
tagging step has an explicit checklist line going forward — the process was
already documented in `VERSIONING.md`, it just had nothing forcing it to actually
happen. Confirmed with the founder this stays additive: deploy remains continuous
(`deploy.yml` deploys on every `main` push, not tag-gated) — tags are a
historical/rollback marker only, not a release trigger. This session's own bug
fixes (below) are tagged `0.6.1`, the first tag created as part of a real release
rather than retroactively.

## 2026-08-10 — Two live bugs found in rate resolution (found from `ha-fleet-connect`), both fixed this session

Originally found while building an equivalent client-side rate resolver in
`ha-fleet-connect` (mirroring this repo's logic, same reasoning as its
`demand_window.py`), flagged here first without a code fix; picked back up the
same day for a real fix once the founder asked for it directly. Both confirmed
live against the public production API before fixing, not just read from source.

**1. `seed/ausgrid.json`'s `EA029` export entries were authored in the wrong
shape, and the loader had no check to catch it.** Correcting the original
"every export tariff, every DNSP is affected" read above: only `ausgrid.json`'s
`EA029` actually had this problem — `energex.json`'s `96200` (also `tou_export`)
was already seeded in the correct shape, so this was one DNSP's stale data, not
a systemic loader bug. `EA029`'s two `exports` entries used the same
`period_name`/`rate`/`start_time`/`end_time` shape as `rates`, not
`TariffExport`'s real `credit_rate`/`charge_rate` columns — `seed/build_db.py`'s
loader read the correct field names but they didn't exist in that entry, so
every value came back `None` with no error. Confirmed live before the fix:
`GET /api/v1/tariffs/ausgrid/EA029` returned `credit_rate: null, charge_rate:
null` in production. **Fixed**: `seed/ausgrid.json`'s `EA029` exports collapsed
into one entry in the correct shape, preserving the already-sourced values
(`0.01232` → `charge_rate`, `-0.03855` → `credit_rate`, sign-flipped to match
`credit_rate`'s "positive, paid to customer" convention — same sign the
`energex.json` entry already uses). Also added a loader-side guard
(`seed/build_db.py`): an `exports` entry with neither `credit_rate` nor
`charge_rate` present now raises at seed-build time instead of silently
producing an all-null row, so this class of shape mismatch can't recur
unnoticed for a future DNSP. Verified by rebuilding `data/tariffs.db` from seed
and querying `EA029` directly: `credit_rate=0.03855, charge_rate=0.01232`.

**2. `app/services/rate_calculator.py`'s `is_day_match()` only special-cased the
singular `"weekday"`/`"weekend"`, but real seeded data uses the plural
`"weekdays"`/`"weekends"`** (confirmed: `seed/powercor.json`, `seed/ausnet.json`) —
matching `TariffRateResponse.days`'s own documented values ("'all', 'weekdays', or
'weekends'"), just not what the matching code checked for. Since `is_day_match()`
defaulted to `return True` for anything unrecognized, a weekday-restricted rate on
an affected tariff matched every day, weekends included — e.g. Powercor's
`CG`-class business peak rate. Didn't affect any pilot member directly (Energex
3900 uses `"days": "all"` throughout). **Fixed**: `is_day_match()` now accepts
both singular and plural forms.

No unit tests existed for `rate_calculator.py` at all before this — added
`tests/test_rate_calculator.py` covering `is_day_match`/`is_in_time_window`/
`is_season_match` directly, including the plural-weekdays regression case. 59/59
tests passing (13 new), ruff clean.

## 2026-08-03 — Demand-charge schema gap found while seeding CitiPower/Powercor/United Energy

Seeding the 3 new VIC DNSPs (`feat/0.6.0`, not yet merged) surfaced a real schema
limitation — flagging for planning, not fixed here (a breaking API change isn't a
call this session makes unilaterally).

**The gap**: `Tariff.demand` (`app/models/tariff.py`) is a single nullable object
(`relationship(..., uselist=False)`), not a list. Several of these DNSPs' small/
medium business demand tariffs (CitiPower `CG`/`CMG`, Powercor `NDD`/`NDM`, United
Energy `LVMKW1R`/`UMBD`, and likely equivalents at other already-seeded DNSPs not
audited here) charge **two different demand rates depending on season** — e.g.
CitiPower's `CG`: $17.5084/kW/month in summer (Dec-Mar) vs $5.9467/kW/month
non-summer (Apr-Nov), same measurement window and method, different rate. One
`TariffDemand` row can only hold one rate — there's no way to represent "the
rate depends on which of two seasons you're in" without either picking one
season arbitrarily (wrong the other 8 months) or inventing a workaround.

**Why this session didn't seed those tariffs instead of trying to force a fit**:
presenting a single-season rate as *the* rate via a `verified_by:
official_price_list` record would be silently wrong for most of the year — worse
than not having the tariff at all. Left `CG`/`CMG`/`CMGO21`/`NDD`/`NDM`/`LVMKW1R`/
`UMBD`/`UMBO` and all large/HV/sub-transmission tariffs out of the new seed files
entirely; see `DATA_SOURCES.md`'s new CitiPower/Powercor/United Energy sections
for the full per-DNSP exclusion list.

**What would NOT need to change** (checked directly against the schema before
concluding this, not assumed): export/CER tariffs. `Tariff.rates` is already
`list[TariffRate]` with `season`/`season_months` fields already present (this is
exactly how Ausgrid's existing high/low-season rates are modeled), and
`Tariff.exports` is already `list[TariffExport]`, not a single object. A seasonal
two-rate import structure or two differently-seasoned export-credit windows are
both already representable with the current schema, no migration needed — the
CER tariffs (CitiPower `CRCER` etc.) were left unseeded purely because the AER
indicative-prices data source didn't carry their $ figures, not because the model
couldn't hold them. One minor, non-breaking asymmetry noted in passing:
`TariffExport` has `credit_season_months` but no `charge_season_months` — additive
fix if ever needed, not currently blocking anything.

**Proposed fix shape, not a decision**: `Tariff.demand` → `list[TariffDemand]`,
mirroring how `rates`/`exports` already work. This is a genuine breaking response-
shape change for every *already-seeded* demand tariff across all DNSPs (Energex
`3900`, Ausgrid `EA116`, etc. — not just the 3 new ones) — `TariffDetailResponse.demand`
goes from `TariffDemandResponse | None` to a list, and
`app/services/rate_calculator.py`'s `is_in_demand_window()`/
`calculate_demand_surcharge()` plus the `/calculate/demand-surcharge` endpoint all
currently assume exactly one demand object and would need real logic for
"which of N windows/seasons applies right now" — not a mechanical schema edit.
Worth a MAJOR version bump per `VERSIONING.md`'s own rule ("breaking API changes").
Flagging for planning to decide whether/when this is worth doing versus leaving
seasonal-demand tariffs permanently out of scope.

## 2026-08-10 — Security/PII scan pass: `.gitignore` gap closed (no working-tree or history leak found)

**Cross-repo security pass** (`repos/.agent/security-scan.md`, new repeatable
process this session, precedent `ha-tariff-au` commit `b5d2119`). Working tree,
tracked-files, and full git history all came back clean — the earlier `/home/our`
pickaxe hit was a false positive (`energex.com.au/home/our-services/...`, a real
public tariff-source URL, not a local path). One gap fixed: `.gitignore` was
missing `secrets.yaml`/`.claude/`/`.idea/`/`.vscode/` exclusions (had `.env`
already). This repo is real and public
(`github.com/Open-Energy-Collective/tariff-service`) — added a pointer to the new
scan process in `.agent/pre-commit-rules.md` so it's run before future releases.
