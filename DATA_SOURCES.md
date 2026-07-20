# Data Sources

Metadata file tracking where tariff data comes from. Updated as new sources are found.

## Ausgrid (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Ausgrid Network Price List 2026-27 (AUTHORITATIVE)** | https://aopt-p-001.sitecorecontenthub.cloud/api/public/content/a6b7b18dc0e84cda9ab067f61a6bbab7?v=21f13674 | Official AER-approved network tariff schedule. PDF. Ex GST. Effective 1 Jul 2026. Updated Apr 27, 2026. |
| Ausgrid network prices page (links to above) | https://www.ausgrid.com.au/prices | Landing page where price list is published. Check annually for updates. |
| Ausgrid ToU pricing explainer | https://www.ausgrid.com.au/your-energy-use/smarter-energy-use/understanding-network-tariffs/time-of-use-pricing | Official peak/off-peak window definitions. |
| Ausgrid demand pricing explainer | https://ausgrid.com.au/your-energy-use/smarter-energy-use/understanding-network-tariffs/demand-pricing | Official demand measurement methodology. |
| Local copy of price list | ~/hass/ai-inputs/Ausgrid Network Price List 2026-27 (1).pdf | Downloaded 2026-07-20 |

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
- **Demand window**: Same as peak (15:00–21:00, high season only)
- **Demand measurement**: Maximum 30-minute interval in the peak window per month

---

## Endeavour Energy (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Endeavour Energy Network Price List 2026-27 (AUTHORITATIVE)** | https://www.endeavourenergy.com.au/about/corporate-information/how-were-regulated/information-for-retailers | Official AER-approved NUOS price list. PDF. Ex GST. Effective 1 Jul 2026. Version 1.0, 28 Apr 2026. |
| Local copy of price list | ~/hass/ai-inputs/dnsp-tariffs/NUOS-Price-List.pdf | Downloaded 2026-07-20 |

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

---

## Essential Energy (NSW)

| Source | URL | Notes |
|--------|-----|-------|
| **Essential Energy Price List & Explanatory Notes 2026-27 (AUTHORITATIVE)** | https://www.essentialenergy.com.au/-/media/Project/EssentialEnergy/Website/Files/Our-Network/PriceListAndExplanatoryNotes2026-27.ashx | Official AER-approved price list. PDF. Ex GST. Effective 1 Jul 2026. |
| Local copy of price list | ~/hass/ai-inputs/dnsp-tariffs/PriceListAndExplanatoryNotes2026-27.ashx | Downloaded 2026-07-20 |

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
- **Peak**: 3pm–5pm (15:00–17:00) weekdays
- **Shoulder**: 7am–3pm (07:00–15:00) and 5pm–8pm (17:00–20:00) weekdays
- **Off-peak**: All other times (including all weekend)

Sun Soaker (SS) tariffs:
- **Peak**: 7am–10am and 3pm–10pm all days
- **Off-peak**: 10am–3pm (solar soak period) and overnight

---

## SA Power Networks (SA)

| Source | URL | Notes |
|--------|-----|-------|
| **SA Power Networks Annual Pricing Proposal Overview 2026-27 (AUTHORITATIVE)** | https://www.sapowernetworks.com.au/industry/pricing-and-tariffs/ | Official AER-approved NUoS schedule. PDF. Ex GST. Effective 1 Jul 2026. |
| Local copy | ~/hass/ai-inputs/dnsp-tariffs/SA Power Networks – 2026–27 – Customer Overview Document – 10 April 2026.pdf | Downloaded 2026-07-20 |

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

- **Peak**: 5pm–9pm (17:00–21:00) all days
- **Solar Sponge**: 10am–3pm (10:00–15:00) all days
- **Shoulder**: 6am–10am (06:00–10:00), 3pm–5pm (15:00–17:00), 9pm–1am (21:00–01:00)
- **Off-peak**: 1am–6am (01:00–06:00) all days
- **Demand window**: Peak period (17:00–21:00), highest 30-min interval
- **Note**: SA is UTC+9:30 (no daylight saving)

---

## Energex (QLD)

| Source | URL | Notes |
|--------|-----|-------|
| **Energex 2026-27 Network Price List (AUTHORITATIVE)** | https://www.energex.com.au/__data/assets/excel_doc/0010/1985968/Energex-2026-27-Network-Price-List-Updated-for-Sch-8.xlsx | Official AER-approved network tariff schedule. Excel spreadsheet. Ex GST. Effective 1 Jul 2026. |
| Energex network pricing page (links to above) | https://www.energex.com.au/our-network/network-pricing-and-tariffs | Landing page where price list is published. Check annually for updates. |
| Amber Electric FY 26-27 tariff rates (CROSS-REFERENCE ONLY) | https://help.amber.com.au/hc/en-us/articles/360060072251-FY-26-27-tariff-rates | Amber's retail pass-through view. Useful for mapping Amber tariff codes to NTCs. NOT authoritative for rates. |
| Energex residential tariffs (descriptions) | https://www.energex.com.au/manage-your-energy/ways-to-save-for-businesses-and-farms/tariffs/residential-tariffs | Tariff descriptions, time windows, eligibility. |
| Local copy of price list | ~/hass/ai-inputs/Energex-2026-27-Network-Price-List-Updated-for-Sch-8.xlsx | Downloaded 2026-07-20 |

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

All Energex tariffs use the same peak/shoulder/off-peak windows:
- **Peak**: 4pm–9pm (16:00–21:00) every day
- **Shoulder**: 9pm–12am (21:00–00:00) every day
- **Off-peak**: 12am–4pm (00:00–16:00) every day
- **Demand window**: 4pm–9pm, measured as max 30-min average of the month

## Notes
- **Authoritative source**: Energex Network Price List spreadsheet (AER-approved)
- All rates are **excluding GST** and represent **NUOS network charges only** (not retail)
- Spreadsheet breaks down: NUOS (total) = DUOS (distribution) + TUOS (transmission) + JS (jurisdictional) + Metering
- We use **NUOS** (the bundled total) as this is what retailers pass through
- Rates are in **$/kWh** and **$/day** — already in the correct unit for the API
- Demand charges are in **$/kW/month**
- Amber zone suffixes (50/70/00/20) = different supply voltage/connection types; all share the same NTC rate
- Tariffs marked with * are closed to new customers but still active for existing customers
- The demand measurement window (peak 4pm–9pm, 30-min average) is NOT in the price list — sourced from Energex tariff descriptions page
