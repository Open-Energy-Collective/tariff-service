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
