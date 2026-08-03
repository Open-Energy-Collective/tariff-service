# Build Session Status Log

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
