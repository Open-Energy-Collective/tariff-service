# Data Sources

Metadata file tracking where tariff data comes from. Updated as new sources are found.

## Ausgrid (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Ausgrid Network Price List 2026-27 (AUTHORITATIVE)** | https://aopt-p-001.sitecorecontenthub.cloud/api/public/content/a6b7b18dc0e84cda9ab067f61a6bbab7?v=21f13674 | Official AER-approved network tariff schedule. PDF. Ex GST. Effective 1 Jul 2026. Updated Apr 27, 2026. |
| Ausgrid network prices page (links to above) | https://www.ausgrid.com.au/prices | Landing page where price list is published. Check annually for updates. |
| Ausgrid ToU pricing explainer | https://www.ausgrid.com.au/your-energy-use/smarter-energy-use/understanding-network-tariffs/time-of-use-pricing | Official peak/off-peak window definitions. |
| Ausgrid demand pricing explainer | https://ausgrid.com.au/your-energy-use/smarter-energy-use/understanding-network-tariffs/demand-pricing | Official demand measurement methodology. |

### Tariff Codes (Ausgrid)

Ausgrid uses codes prefixed with "EA" (e.g., EA025, EA116).

#### Residential

| Code | Name | Type |
|------|------|------|
| EA010 | Residential Flat (closed) | flat |
| EA025 | Residential ToU | tou |
| EA111 | Residential Demand (Introductory) | tou_demand |
| EA116 | Residential Demand | tou_demand |
| EA029 | Small Customer Export Tariff | tou_export |
| EA030 | Controlled Load 1 | controlled_load |
| EA040 | Controlled Load 2 | controlled_load |

#### Business

| Code | Name | Type |
|------|------|------|
| EA050 | Small Business Flat (closed) | flat |
| EA225 | Small Business ToU | tou |
| EA251 | Small Business Demand (Introductory) | tou_demand |
| EA256 | Small Business Demand | tou_demand |
| EA302 | LV 100-160 MWh | tou_demand |
| EA305 | LV 160-750 MWh (System) | tou_demand |
| EA310 | LV > 750 MWh (System) | tou_demand |
| EA370 | HV Connection (System) | tou_demand |
| EA390 | ST Connection (System) | tou_demand |

### Time Windows (Ausgrid)

Ausgrid uses **seasonal** peak pricing (no shoulder period):
- **Peak**: 3pm–9pm (15:00–21:00)
  - Residential: all days
  - Small business: working weekdays only
- **Off-peak**: All other times
- **High season**: June–August (winter) and November–March (summer)
- **No peak**: April, May, September, October (all off-peak)
- **Demand window**: Same as peak (15:00–21:00, high season only) for EA111, EA116, EA251, EA256
- **Capacity window (EA302, EA305, EA310, EA370, EA390)**: 15:00–21:00 working weekdays, all year; their peak energy rate stays high season only. Source: the revised TSS explanatory statement 2024-29, Table 11 note, p. 40 (`knowledge/documents/ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.md` in the OEC root)
- **Capacity unit and peak period**: EA302 is priced per kW, and EA305, EA310, EA370 and EA390 per kVA (c/kVA/day x 30 / 100, `unit` `kVA`). All five charge on the highest peak-window demand of the prior 12 months (`peak_period` `rolling_12_months`)
- **Demand measurement**: Maximum 30-minute interval in the peak window. The price list and TSS state no interval, so the seeded `30min_max` stands

---

## Endeavour Energy (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Endeavour Energy Network Price List 2026-27 (AUTHORITATIVE)** | https://www.endeavourenergy.com.au/about/corporate-information/how-were-regulated/information-for-retailers | Official AER-approved NUOS price list. PDF. Ex GST. Effective 1 Jul 2026. Version 1.0, 28 Apr 2026. |

### Tariff Codes (Endeavour Energy)

Endeavour uses codes prefixed with "N" (e.g., N70, N71).

#### Residential

| Code | Name | Type |
|------|------|------|
| N70 | Residential Flat | flat |
| N71 | Residential Seasonal ToU | tou |
| N72 | Residential Demand | tou_demand |
| N73 | Residential Demand Transitional | tou_demand |
| N50 | Controlled Load 1 | controlled_load |
| N54 | Controlled Load 2 | controlled_load |

#### Business

| Code | Name | Type |
|------|------|------|
| N90 | General Supply Block | flat |
| N91 | General Supply Seasonal ToU | tou |
| N92 | General Supply Demand | tou_demand |
| N93 | General Supply Demand Transitional | tou_demand |
| N19 | LV Seasonal ToU Demand | tou_demand |
| N29 | HV Seasonal ToU Demand | tou_demand |
| N39 | ST Seasonal ToU Demand | tou_demand |
| N99 | Unmetered Supply | flat |

### Time Windows (Endeavour Energy)

- **Peak**: 4pm–8pm (16:00–20:00) business days only
- **Solar Soak**: 10am–2pm (10:00–14:00) all days
- **Off-peak**: All other times
- **High season**: November–March
- **Low season**: April–October
- **Demand window**: Peak periods only (16:00–20:00 weekdays), highest 30-min interval × days in month
- **Demand rates**: every demand tariff has a high-season charge (November to March) and a low-season charge (April to October) on the same window, from Table 1a. N19, N29 and N39 are priced per kVA (`unit` `kVA`)

---

## Essential Energy (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Essential Energy Price List & Explanatory Notes 2026-27 (AUTHORITATIVE)** | https://www.essentialenergy.com.au/-/media/Project/EssentialEnergy/Website/Files/Our-Network/PriceListAndExplanatoryNotes2026-27.ashx | Official AER-approved price list. PDF. Ex GST. Effective 1 Jul 2026. |

### Tariff Codes (Essential Energy)

Essential uses alphanumeric codes (e.g., BLNRSS2, BLND1AR).

#### Residential

| Code | Name | Type |
|------|------|------|
| BLNRSS2 | LV Residential ToU - Sun Soaker | tou |
| BLND1AR | LV Residential ToU Demand | tou_demand |
| BLNC1AU | Controlled Load 1 (5-9 hrs) | controlled_load |
| BLNC2AU | Controlled Load 2 (10-19 hrs) | controlled_load |

#### Business

| Code | Name | Type |
|------|------|------|
| BLNBSS1 | LV Small Business ToU - Sun Soaker | tou |
| BLND1AB | LV Small Business ToU Demand | tou_demand |
| BLND3AO | LV Large Business Demand | tou_demand |
| BHND3AO | HV Business Demand | tou_demand |
| BSSD3AO | Subtransmission Demand | tou_demand |

### Time Windows (Essential Energy)

PSO-Int (interval meter, default for new connections):
- **Peak**: 5pm–8pm (17:00–20:00) weekdays; also the demand window
- **Shoulder**: 7am–5pm (07:00–17:00) and 8pm–10pm (20:00–22:00) weekdays
- **Off-peak**: All other times (including all weekend)
- **Public holidays**: times are unchanged when a public holiday falls on a weekday (`public_holidays` `included`)
- **Demand**: priced per kVA per month (`unit` `kVA`), on the maximum 30-minute clocked kVA in the month. BLND3AO, BHND3AO and BSSD3AO also have shoulder and off-peak demand charges. They are not seeded: one charge over two windows, and a weekend window that ignores weekday public holidays, have no place in the model (#70)

Sun Soaker (SS) tariffs:
- **Peak**: 7am–10am and 3pm–10pm all days
- **Off-peak**: 10am–3pm (solar soak period) and overnight

---

## SA Power Networks (SA)

| Source | URL | Notes |
|--------|-----|-------|
| **SA Power Networks Annual Pricing Proposal Overview 2026-27 (AUTHORITATIVE)** | https://www.sapowernetworks.com.au/industry/pricing-and-tariffs/ | Official AER-approved NUoS schedule. PDF. Ex GST. Effective 1 Jul 2026. |

### Tariff Codes (SA Power Networks)

SAPN uses short codes (e.g., RSR, RTOU, RESELE).

#### Residential

| Code | Name | Type |
|------|------|------|
| RSR | Residential Single Rate | flat |
| RTOU | Residential Time of Use | tou |
| RESELE | Residential Electrify | tou |

#### Business

| Code | Name | Type |
|------|------|------|
| BSR | Business Single Rate | flat |
| SBTOU | Small Business Time of Use | tou |
| SBELE | Small Business Electrify | tou |
| MBTOUD | Medium Business Time of Use Demand | tou_demand |
| LBAD | Large LV Business Annual Demand | tou_demand |

### Time Windows (SA Power Networks)

From the 2026-27 customer overview (Tables 2, 4, 5) and Tariff Price List v1.0 (Table 1):

- **RTOU**: off-peak 12am–6am (00:00–06:00), solar sponge 10am–4pm (10:00–16:00), peak all other times; no shoulder
- **SBTOU, MBTOUD**: peak 5pm–9pm all days November–March; shoulder 7am–5pm workdays November–March and 7am–9pm workdays April–October; off-peak all other times
- **MBTOUD demand**: anytime, per kVA, highest 30-min interval in the last 12 months (`peak_period` `rolling_12_months`)
- **LBAD**: energy peak 7am–9pm workdays, off-peak all other times. Peak demand per kVA, 5pm–9pm all days November–March (non-CBD; CBD 11am–5pm workdays), on the highest daily average demand of the last 12 months and billed all year. No `measurement_method` value names a daily average, so the seeded `30min_max` stands (#70). Anytime demand 0.0630 $/kVA/day (1.89 $/kVA/month) on the highest 30-min interval of the last 12 months

- **RESELE**: peak 5pm–9pm (17:00–21:00) all days, solar sponge 10am–4pm (10:00–16:00) all days, shoulder all other times (the 14 hours outside peak and solar sponge); no off-peak (customer overview Table 2)
- **SBELE**: peak 5pm–9pm all days, shoulder 7am–10am and 4pm–5pm workdays, off-peak all other times (customer overview Table 4). Off-peak $0.1072/kWh and shoulder $0.1875/kWh, from the Off-Peak and Shoulder columns of the NUoS schedule (Table 9)

Exports, 0-30 kW export capacity (price list Table 1; overview Tables 2 and 4):
- **RSR, BSR**: charge 0.75 c/kWh above 11 kWh per day
- **RTOU, SBTOU, MBTOUD**: charge 1 c/kWh 10am–4pm above 9 kWh per day
- **RESELE, SBELE**: as RTOU, plus credit 13.22 c/kWh 5pm–9pm November–March
- Rollover of unused allowance within a billing period is not seeded (#31)

Source entries (OEC root): `knowledge/documents/sa-power-networks/2026-10-21-customer-overview-2026-27.md` and `knowledge/documents/sa-power-networks/2026-10-21-tariff-price-list-2026-27.md`. Windows are local time (ACST/ACDT).

---

## Jemena (VIC)

| Source | URL | Notes |
|--------|-----|-------|
| **Jemena Electricity Networks Network Tariffs 2026-27 (AUTHORITATIVE)** | https://www.jemena.com.au/contentassets/a440c960e37a4eca8497cf44990ebe0b/jen-2026-27-network-tariff-schedule.pdf | Official AER-approved tariff schedule. PDF. Ex GST. Effective 1 Jul 2026. |

### Tariff Codes (Jemena)

| Code | Name | Type |
|------|------|------|
| A100 | Residential Single Rate | flat |
| A130 | Residential Daytime Saver | tou |
| A10E | Residential Export | tou_export |
| A180 | Off-peak Dedicated Circuit | controlled_load |
| A210 | Small Business ToU Weekdays | tou |
| A230 | Small Business ToU Demand | tou_demand |

### Time Windows (Jemena)

Residential (A130, A10E):
- **Peak**: 4pm–9pm every day
- **Solar Soak**: 11am–4pm every day
- **Off-peak**: All other times

Business (A210):
- **Peak**: 9am–9pm weekdays
- **Off-peak**: All other times

Dedicated circuit (A180):
- **Off-peak**: 11pm–7am AEST all days (supply only in that window)
- **Time basis**: `standard`, the source fixes the window to AEST all year

Export (A10E):
- **Export charge**: 3.000 c/kWh, solar soak 11am–4pm every day
- **Export reward**: 15.000 c/kWh credit, peak 4pm–9pm every day

Business Demand (A230):
- **Peak**: 7am–11pm weekdays
- **Off-peak**: All other times
- **Demand**: 77.889 $/kW p.a., seeded as 6.49075 $/kW/month, any time, on the maximum level of the last 12 months (`peak_period` `rolling_12_months`)

---

## AusNet Services (VIC)

| Source | URL | Notes |
|--------|-----|-------|
| **AusNet Services Network Tariff Schedule 2026-27 (AUTHORITATIVE)** | https://www.ausnetservices.com.au/electricity/tariffs-and-charges/network-tariffs | Official AER-approved tariff schedule. Excel. Ex GST. Effective 1 Jul 2026. Standing charges in $/year. |

### Tariff Codes (AusNet Services)

| Code | Name | Type |
|------|------|------|
| NEE11 | Residential Single Rate | flat |
| NASS11 | Residential Time of Use | tou |
| RCER11 | Residential CER (Export) | tou_export |
| NEE33 | Dedicated Circuit 24hr | controlled_load |
| NAST12 | Small Business Time of Use | tou |
| NASN12 | Small Business Single Rate Demand | demand |

### Time Windows (AusNet Services)

Residential ToU (NASS11, RCER11):
- **Peak**: 4pm–9pm every day
- **Solar Soak**: 11am–4pm every day (1 c/kWh)
- **Off-peak**: All other times

Export (RCER11, sheet "Tariff structures", structure 20):
- **Export charge**: 11am–4pm every day, 1 c/kWh above a basic export level of 1 kWh per day
- **Export reward**: 4pm–9pm every day, 10 c/kWh

Business ToU (NAST12):
- **Peak**: 7am–11pm weekdays
- **Off-peak**: All other times

Demand (NASN12):
- **Demand window**: 3pm–9pm (15:00–21:00) weekdays, all year (sheet "Tariff structures", structure 15)
- **Demand rates**: two seasons on the same window. 11.473 $/kW/month December to March (`months` 12, 1, 2, 3) and 2.862 $/kW/month April to November (`months` 4 to 11)
- **Energy**: anytime 16.796 c/kWh (sheet "Network 2026-27")

---

## CitiPower (VIC)

| Source | URL | Notes |
|--------|-----|-------|
| **CitiPower 2026/27 Pricing (structure)** | https://www.aer.gov.au/system/files/2026-05/CitiPower%20%E2%80%93%202026%E2%80%9327%20%E2%80%93%20Pricing%20%E2%80%93%207%20May%202026.pdf | Tariff codes, eligibility, and time-window structure. PDF. Does **not** contain $ rates. It defers them to a separate "CitiPower - 2026-27 Tariff Summary" attachment (next row). Knowledge entry: `knowledge/documents/citipower/2026-10-21-pricing-2026-27.md`. |
| **CitiPower 2026-27 Tariff Summary (rates for CRSTOU)** | https://media.powercor.com.au/documents/Network-pricing/CitiPower-FINAL-2026-27-Tariff-Summary-07-May-2026-PUBLIC.xlsx | Final workbook, 7 May 2026, excluding GST. Sheet `CP_2026-27_NUOS` row 7 gives CRSTOU: fixed 31.51 c/day, peak 19.76, off-peak 4.95, saver 1.00 c/kWh. Knowledge entry: `knowledge/documents/citipower/2026-11-10-tariff-summary-2026-27.md`. |
| **AER TSS.01, SCS indicative prices (rates for every tariff except CRSTOU)** | https://www.aer.gov.au/system/files/2025-02/CP%20ATT%20TSS.01%20-%20SCS%20indicative%20prices%20-%20Jan2025%20-%20Public.xlsx | Regulator-hosted Excel attachment to CitiPower's 2026-31 Tariff Structure Statement (Jan2025 proposal). Contains the actual `$`/`c` figures by tariff code and year, including 2026-27. Tariff codes match the structural PDF above exactly. **Caveat**: these are TSS "indicative" prices from the regulatory proposal, not a DNSP-published final price list. A revised Dec2025 TSS compliance document exists and may carry updated figures not re-verified here. |

CRSTOU carries `verified_by: official_price_list`, checked 2026-11-10 against the Tariff Summary (`knowledge/findings/2026-11-10-victorian-2026-27-network-rates-found.md` in the OEC root, #46). The other seeded tariffs carry `verified_by: aer_tss01_indicative_jan2025`: the AER January 2025 TSS.01 indicative prices stand in until they are checked against the Tariff Summary.

### Tariff Codes (CitiPower) — seeded subset only

Only tariffs with an unambiguous single rate/period mapping in the indicative-prices sheet were seeded. **Not seeded**: CRCER (two-way/CER export tariff — indicative sheet only populates its off-peak column, peak/export/seasonal components are blank/zero, not enough to model faithfully); CG/CMG/CMGO21 and all large/HV/sub-transmission tariffs (demand charge is split across two seasonal windows — summer Dec-Mar, non-summer Apr-Nov — but this schema's `TariffDemand` supports only one window, so seeding these would require an unmade modeling decision, not a data gap).

| Code | Name | Type |
|------|------|------|
| C1R | Residential Single Rate | flat |
| CRSTOU | Residential ToU | tou |
| CDS | Dedicated Circuit | controlled_load |
| C1G | Small Business Single Rate | flat |
| CGTOU | Small Business ToU | tou |

### Time Windows (CitiPower)

Residential ToU (CRSTOU), every day, public holidays included:
- **Peak**: 4pm to 9pm
- **Saver**: 11am to 4pm
- **Off-peak**: 9pm to 11am

Business ToU (CGTOU):
- **Peak**: 9am–9pm weekdays (confirmed directly against CitiPower's TSS compliance document text, not assumed)
- **Off-peak**: all other times

---

## Powercor (VIC)

| Source | URL | Notes |
|--------|-----|-------|
| **Powercor 2026/27 Pricing (structure)** | https://www.aer.gov.au/system/files/2026-05/Powercor%20%E2%80%93%202026%E2%80%9327%20%E2%80%93%20Pricing%20%E2%80%93%207%20May%202026.pdf | Same structure-only gap as CitiPower's PDF (see above) — Powercor and CitiPower are commonly-owned/co-filed with near-identical document templates, confirmed by direct side-by-side comparison, not assumed. |
| **Powercor 2026-27 Tariff Summary (rates for PRSTOU)** | https://media.powercor.com.au/documents/Network-pricing/Powercor-FINAL-2026-27-Tariff-Summary-07-May-2026-PUBLIC.xlsx | Final workbook, 7 May 2026, excluding GST. Sheet `PAL_2026-27_NUOS` row 7 gives PRSTOU: fixed 43.84 c/day, peak 22.09, off-peak 5.52, saver 1.00 c/kWh. Knowledge entry: `knowledge/documents/powercor/2026-11-10-tariff-summary-2026-27.md`. |
| **AER TSS.01, SCS indicative prices (rates for every tariff except PRSTOU)** | https://www.aer.gov.au/system/files/2025-02/PAL%20ATT%20TSS.01%20-%20SCS%20indicative%20prices%20-%20Jan2025_0.xlsx | Same provenance/caveats as CitiPower's TSS.01 sheet above. Tariff codes match the structural PDF exactly. |

PRSTOU carries `verified_by: official_price_list`, checked 2026-11-10 against the Tariff Summary (`knowledge/findings/2026-11-10-victorian-2026-27-network-rates-found.md` in the OEC root, #46). The other seeded tariffs carry `verified_by: aer_tss01_indicative_jan2025`: the AER January 2025 TSS.01 indicative prices stand in until they are checked against the Tariff Summary.

### Tariff Codes (Powercor) — seeded subset only

Same exclusions as CitiPower (see above): PRCER, NDD/NDM/NDMO, and all large/HV/sub-transmission tariffs not seeded.

| Code | Name | Type |
|------|------|------|
| D1 | Residential Single Rate | flat |
| PRSTOU | Residential ToU | tou |
| DD1 | Dedicated Circuit | controlled_load |
| ND1 | Small Business Single Rate | flat |
| NDTOU | Small Business ToU | tou |

### Time Windows (Powercor)

Residential ToU (PRSTOU) has the CitiPower CRSTOU windows: peak 4pm to 9pm, saver 11am to 4pm, off-peak 9pm to 11am, every day (`knowledge/documents/powercor/2026-10-21-pricing-2026-27.md`).

Business ToU (NDTOU): peak 9am to 9pm weekdays (confirmed against Powercor's own TSS compliance document text), off-peak all other times.

---

## United Energy (VIC)

| Source | URL | Notes |
|--------|-----|-------|
| **United Energy 2026/27 Pricing (structure)** | https://www.aer.gov.au/system/files/2026-05/United%20Energy%20%E2%80%93%202026%E2%80%9327%20%E2%80%93%20Pricing%20%E2%80%93%207%20May%202026.pdf | Same structure-only gap as CitiPower/Powercor's PDFs. |
| **United Energy 2026-27 SCS pricing model (rates for URSTOU)** | https://www.aer.gov.au/system/files/2026-05/United%20Energy%20%E2%80%93%202026%E2%80%9327%20%E2%80%93%20SCS%20pricing%20model%20%E2%80%93%207%20May%202026.xlsm | United Energy's pricing model filed with the AER, 7 May 2026, excluding GST. United Energy's own Tariff Summary was not found. Sheet `Tariff schedule`, Tariff schedule 3, row 88 gives URSTOU: fixed 31.51 c/day, peak 20.92, off-peak 5.22, saver 1.00 c/kWh. Knowledge entry: `knowledge/documents/united-energy/2026-11-10-scs-pricing-model-2026-27.md`. |
| **AER TSS.01, SCS indicative prices (rates for every tariff except URSTOU)** | https://www.aer.gov.au/system/files/2025-02/UE%20ATT%20TSS.01%20-%20SCS%20indicative%20prices%20-%20Jan2025%20-%20Public.xlsx | Same provenance/caveats as above. Tariff codes match the structural PDF exactly. |

URSTOU carries `verified_by: official_price_list`, checked 2026-11-10 against the AER SCS pricing model (`knowledge/findings/2026-11-10-victorian-2026-27-network-rates-found.md` in the OEC root, #46). The other seeded tariffs carry `verified_by: aer_tss01_indicative_jan2025`: the AER January 2025 TSS.01 indicative prices stand in until they are checked against the SCS pricing model.

### Tariff Codes (United Energy) — seeded subset only

Same exclusions as CitiPower/Powercor: URCER, LVMKW1R/UMBD/UMBO, and all large/HV tariffs not seeded.

| Code | Name | Type |
|------|------|------|
| LVS1R | Residential Single Rate | flat |
| URSTOU | Residential ToU | tou |
| LVDed | Dedicated Circuit | controlled_load |
| LVM1R | Small Business Single Rate | flat |
| LVTOU | Small Business ToU | tou |

### Time Windows (United Energy)

Residential ToU (URSTOU) has the CitiPower CRSTOU windows: peak 4pm to 9pm, saver 11am to 4pm, off-peak 9pm to 11am, every day (`knowledge/documents/united-energy/2026-10-21-pricing-2026-27.md`).

Business ToU (LVTOU): peak 9am to 9pm weekdays (confirmed against United Energy's own TSS compliance document text), off-peak all other times.

---

## Evoenergy (ACT)

| Source | URL | Notes |
|--------|-----|-------|
| **Evoenergy Schedule of Electricity Network Charges 2026-27 (AUTHORITATIVE)** | https://www.evoenergy.com.au/Your-Energy/Pricing-and-tariffs | Official AER-approved schedule. PDF. Ex GST. Effective 1 Jul 2026. Includes LFiT adjustment (3.035 c/kWh). |

### Tariff Codes (Evoenergy)

Evoenergy uses numeric codes (e.g., 017, 023, 090).

| Code | Name | Type |
|------|------|------|
| 017 | New Residential TOU | tou |
| 023 | New Residential Demand | tou_demand |
| 060 | Controlled Load 1 | controlled_load |
| 090 | General TOU | tou |
| 101 | LV TOU kVA Demand | tou_demand |

### Time Windows (Evoenergy)

Tariff 017 (New Residential TOU):
- **Peak**: 7am–9am and 5pm–9pm every day
- **Solar Soak**: 11am–3pm every day
- **Off-peak**: All other times

Tariff 023 (New Residential Demand):
- **Demand (High)**: 5pm–9pm every day during winter (Jun-Aug), 21.808 c/kW/day
- **Demand (Low)**: 5pm–9pm every day during non-winter, 13.083 c/kW/day
- **Off-peak demand**: 9pm–9am every day, 2.076 c/kW/day
- **Solar Soak**: 11am–3pm every day
- **Off-peak**: All other times
- **Winter months**: June to August. The schedule of charges does not define them; the revised TSS 2024-29 does (pp. 7, 15: `knowledge/documents/evoenergy/2026-10-23-revised-tss-2024-29.md` in the OEC root)

Controlled load (060):
- **Off-peak**: 6 to 8 hours between 10pm and 7am every day, 5.413 c/kWh, no fixed charge (seeded as anytime)

Business (090, 101):
- **Peak**: 7am–5pm weekdays
- **Shoulder**: 5pm–10pm weekdays
- **Off-peak**: All other times
- **101 demand**: Peak kVA Demand 44.217 c/kVA/day, 7am–5pm weekdays (`unit` `kVA`)
- **Time basis**: `standard` for every Evoenergy tariff. The schedule heads each tariff table "Charge applicability (times in AEST)" (`knowledge/documents/evoenergy/2026-10-21-schedule-of-charges-2026-27.md` in the OEC root). In daylight saving each window runs one hour later on the Canberra clock, so 101's 7am-5pm peak is 8am-6pm AEDT (#68)

---

## Power and Water Corporation (NT)

| Source | URL | Notes |
|--------|-----|-------|
| **Power and Water Corporation Power Services 2026-27 Network Tariffs (AUTHORITATIVE)** | https://www.powerwater.com.au/__data/assets/pdf_file/0030/462909/Standard-control-service-network-tariffs-2026-27.pdf | Official SCS network price list. PDF. Ex GST. Effective 1 Jul 2026. |

### Tariff Codes (Power and Water)

| Code | Name | Type |
|------|------|------|
| T1 | Residential Tariff | flat |
| T2 | Non-residential Tariff | flat |
| T3A | LV Smart Meter (Residential 0-160MWh) | tou |
| T3B | LV Smart Meter (Non-Residential 0-160MWh) | tou |
| T3C | LV Smart Meter (160-750MWh) | tou |
| T5 | LV Majors (Above 750MWh) | demand |
| T6 | HV Smart Meter | demand |

### Time Windows (Power and Water)

Smart meter tariffs (T3A/B/C):
- **High Period (Peak)**: 3pm–9pm weekdays, October–March only
- **Low Period (Super Off-Peak/Solar Soak)**: 9am–3pm every day, all year
- **Mid Period (Off-Peak)**: All other times

Demand tariffs (T5, T6):
- **On Season demand**: 3pm–9pm weekdays, October–March
- **Off Season demand**: 3pm–9pm weekdays, April–September
- **Demand rates**: T5 On Season 16.7014 and Off Season 3.9297 $/kVA; T6 8.8419 and 2.6154 $/kVA. Both seasons include public holidays
- **Unit**: the price list gives $/kVA without a period; read as per month (`knowledge/findings/2026-10-21-tariff-service-source-gaps-resolved-2026-27.md`), seeded without conversion as `unit` `kVA`
- **Note**: NT uses UTC+9:30, no daylight saving

---

## Energex (QLD)

| Source | URL | Notes |
|--------|-----|-------|
| **Energex 2026-27 Network Price List (AUTHORITATIVE)** | https://www.energex.com.au/__data/assets/excel_doc/0010/1985968/Energex-2026-27-Network-Price-List-Updated-for-Sch-8.xlsx | Official AER-approved network tariff schedule. Excel spreadsheet. Ex GST. Effective 1 Jul 2026. |
| Energex network pricing page (links to above) | https://www.energex.com.au/our-network/network-pricing-and-tariffs | Landing page where price list is published. Check annually for updates. |
| Amber Electric FY 26-27 tariff rates (CROSS-REFERENCE ONLY) | https://help.amber.com.au/hc/en-us/articles/360060072251-FY-26-27-tariff-rates | Amber's retail pass-through view. Useful for mapping Amber tariff codes to NTCs. NOT authoritative for rates. |
| Energex residential tariffs (descriptions) | https://www.energex.com.au/manage-your-energy/ways-to-save-for-businesses-and-farms/tariffs/residential-tariffs | Tariff descriptions, time windows, eligibility. |

## Tariff Code Mapping

The API uses **NTC (Network Tariff Code)** as the canonical identifier. These are assigned by
Energex and published in the official Network Price List.

Some retailers (e.g., Amber Electric) append zone suffixes to NTC codes:
- NTC `3900` → Amber codes `3900`, `3920`, `3950`, `3970`
- Suffixes indicate supply voltage/connection type — rates are identical

**To find your NTC:** strip the last two digits if they are 20/50/70 (e.g., `3970` → `3900`).

### Residential (<100MWh pa)

| NTC | Name | Type |
|-----|------|------|
| 6900 | Residential ToU Energy | tou |
| 3900 | Residential ToU Demand & Energy | tou_demand |
| 8400 | Residential Flat (closed to new) | flat |
| 9100 | Economy (Controlled Load) | controlled_load |
| 9000 | Super Economy (Controlled Load) | controlled_load |

### Small Business (<100MWh pa)

| NTC | Name | Type |
|-----|------|------|
| 6800 | Small Business ToU Energy | tou |
| 3800 | Small Business ToU Demand & Energy | tou_demand |
| 8500 | Business Flat (closed to new) | flat |
| 5700 | Small Business Primary Load Control | controlled_load |

### Large (>100MWh pa)

| NTC | Name | Type |
|-----|------|------|
| 7200 | Large ToU Demand & Energy | tou_demand |
| 8300 | Demand Small | demand |
| 6700 | Large Business Energy | flat |
| 94300 | Large ToU Energy | tou |
| 5800 | Large Business Primary Load Control | controlled_load |
| 5900 | Large Business Secondary Load Control | controlled_load |

### Tariff Trials

| NTC | Name | Type |
|-----|------|------|
| 96200 | Residential Two-Way Tariff Trial | tou_export |
| 94500 | Dynamic Business LV Tariff Trial | dynamic |

## Time Windows (Energex)

Residential ToU and demand (6900, 3900), from the residential tariffs page (`knowledge/documents/energex/2026-10-21-residential-tariffs-page.md` in the OEC root):
- **Peak**: 4pm–9pm (16:00–21:00) every day
- **Off-peak**: 11am–4pm (11:00–16:00) every day
- **Shoulder**: 9pm–11am (21:00–11:00) every day
- **Demand window**: 4pm–9pm, measured as max 30-min average of the month

Business ToU demand (3800, 7200), from the Energex Network Tariff Guide 2026-27 (Table 6 and section 3.3; `knowledge/documents/energex/2026-10-21-network-tariff-guide-2026-27.md`):
- **Peak**: 5pm–8pm (17:00–20:00) weekdays; no peak on weekends; also the peak demand window
- **Shoulder**: 1pm–5pm and 8pm–11am weekdays, 1pm–11am weekends
- **Off-peak**: 11am–1pm (11:00–13:00) every day
- **Public holidays**: weekdays and weekends each include the public holidays that fall on them
- **7200 demand**: $/kVA/month by default; the kW variant (15.459 $/kW/month peak) is seeded on purpose, because OEC measures and plans in kW (decided 2026-11-10). The shoulder demand charge is not seeded: one charge over two windows, and a weekend window that ignores weekday public holidays, have no place in the model (#70). Off-peak demand is 0

Small Demand (8300): anytime demand on the highest 30-minute kVA in the month, priced per kVA (`unit` `kVA`).

## Time Basis and Public Holidays

- **Time basis**: every tariff version carries `time_basis`. `local` windows follow the distributor's clock with daylight saving. `standard` windows follow standard time all year. Each DNSP's captured 2026-27 source was checked for its time basis on 2026-11-10 (#68), as the table below records. A tariff is `standard` only where its source states standard time. Where the source is silent or ambiguous, the tariff stays `local`. Entry paths are under `knowledge/documents/` in the OEC root.

| DNSP | Source entry | Source wording | Seeded basis |
|---|---|---|---|
| Ausgrid | `ausgrid/2026-10-21-network-price-list-2026-27.md`, `ausgrid/2026-10-21-revised-tss-explanatory-statement-2024-29.md` | Source silent | `local` |
| Endeavour Energy | `endeavour-energy/2026-10-21-network-price-list-2026-27.md`, sections 6.1 and 6.7 | Periods "apply during both Eastern Standard Time (EST) and Daylight Saving Time (DST)"; "billing data is adjusted by shifting the data forward an hour to accommodate for the time shift during DST" | `local` |
| Essential Energy | `essential-energy/2026-10-21-price-list-explanatory-notes-2026-27.md`, section 4 | "DAYLIGHT SAVINGS TIME will be applied to all customers with interval read meters and unmetered supplies in determining Network charges." Far West region: "based on either Eastern Standard Time or Summer Time depending on when the meter was installed or programmed" (ambiguous, not modelled) | `local` |
| SA Power Networks | `sa-power-networks/2026-10-21-customer-overview-2026-27.md` and its `.pdf`, Tables 2, 3, 4, 5 | "Interval meter tariff structures are based on local time: ACST/ ACDT." BSR is accumulation-metered and Table 4 says "Accumulation meter tariff structures are based on ACST." (the wording is in the `.pdf`, not the `.md`). RSR is accumulation-metered and Table 2 states nothing for accumulation meters (source silent). Table 3 says "Tariff structures are based on ACST." for OPCL and CL, which are not seeded | BSR `standard`, all other SAPN tariffs `local` (RSR included) |
| Jemena | `jemena/2026-10-21-network-tariff-schedule-2026-27.md` | A180: "11 pm to 7 am AEST all days". A130, A10E, A210, A230: "(local time)" on each window. A100: "Single rate all times", no window | A180 `standard`, others `local` |
| AusNet Services | `ausnet/2026-10-21-network-tariff-schedule-2026-27.md`, sheet "Tariff structures" | NASS11, RCER11, NAST12 (structures 21, 20, 17): "* Based on local time". NEE11, NEE33 (structures 1, 19): no window, source silent. NASN12 (structure 15): "3:00PM to 9:00PM ADST Monday to Friday" (ambiguous) | `local` |
| CitiPower | `citipower/2026-10-21-pricing-2026-27.md`, Tables 4 and 5; `citipower/2026-11-10-tariff-summary-2026-27.md` | "All times are local time, except for C2U which is in AEST". C2U is not seeded | `local` |
| Powercor | `powercor/2026-10-21-pricing-2026-27.md`, Tables 4 and 5; `powercor/2026-11-10-tariff-summary-2026-27.md` | "All times are local time, except for PL2 which is in AEST". PL2 is not seeded | `local` |
| United Energy | `united-energy/2026-10-21-pricing-2026-27.md`, Tables 4 and 5 | "All times are local time, except for UNMET which is in AEST". UNMET is not seeded | `local` |
| Evoenergy | `evoenergy/2026-10-21-schedule-of-charges-2026-27.md` | "Charge applicability (times in AEST)" on every tariff table | `standard` (017, 023, 060, 090, 101) |
| Power and Water | `power-and-water/2026-10-21-network-tariffs-2026-27.md` | Source silent. NT has no daylight saving, so both bases agree | `local` |
| Energex | `energex/2026-10-21-network-tariff-guide-2026-27.md`, `energex/2026-10-21-residential-tariffs-page.md` | Source silent. Queensland has no daylight saving, so both bases agree | `local` |

- **Public holidays**: looked up by the DNSP's state with the `holidays` Python package (MIT, pinned in `pyproject.toml`), state-wide only. The captured price lists do not name a holiday list, so regional holidays are not modelled.
- **Treatment**: `public_holidays` on a weekday or weekend window is `excluded` (the window does not apply on a holiday) or `included` (a weekday window applies on a weekday holiday only, a weekend window applies on any holiday). Ausgrid, Endeavour, CitiPower, Powercor and United Energy weekdays are `excluded`, Power and Water weekdays are `included`. Essential and Energex sources keep weekday times on a weekday holiday, so their weekdays are `included`. The AusNet and Evoenergy sources state no treatment for their weekday demand windows, which keep the seeded `included`. Other weekday windows are not checked against their sources here.
- **Prices expected until**: `prices_expected_until` is 2027-07-01 on every seeded tariff, the day after the 2026-27 price lists end and the next annual price change.

## Notes
- **Authoritative source**: Energex Network Price List spreadsheet (AER-approved)
- All rates are **excluding GST** and represent **NUOS network charges only** (not retail)
- Spreadsheet breaks down: NUOS (total) = DUOS (distribution) + TUOS (transmission) + JS (jurisdictional) + Metering
- We use **NUOS** (the bundled total) as this is what retailers pass through
- Rates are in **$/kWh** and **$/day** — already in the correct unit for the API
- Demand charges are in **$/kW/month**, or **$/kVA/month** where `unit` is `kVA` (8300)
- Amber zone suffixes (50/70/00/20) = different supply voltage/connection types; all share the same NTC rate
- Tariffs marked with * are closed to new customers but still active for existing customers
- The demand measurement window (peak 4pm–9pm, 30-min average) is NOT in the price list — sourced from Energex tariff descriptions page
