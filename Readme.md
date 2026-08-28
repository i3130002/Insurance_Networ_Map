# UAE Insurance Network Map

Interactive map of UAE healthcare providers, filterable by insurance plan.

**Live:** https://i3130002.github.io/Insurance-Network-Map/

## Features

- 2,390 unique providers (clinics, hospitals, pharmacies, dental, diagnostic, daycare) across all 8 emirates
- 56 selectable plans from 8 insurers, including 41 Takafol Emarat network variants
- Marker clustering for performance; color-coded provider types
- Popups with Google Maps link + AI search query per provider
- Popups include a phone-first Zavis directory search link for provider cross-checking

## Data

| File | Contents |
|---|---|
| `data/moh-complete.json` | Full provider registry (deduped, valid coordinates) |
| `data/needs-geocoding.json` | Providers still missing reliable coordinates (174) |
| `data/network-unmatched.json` | Official-network records not matched to the registry, for review |
| `data/plans.json` | Plan metadata (name, insurer, coverage, emirates, provider count) |
| `data/<plan-id>.json` | Per-plan provider subsets |

### Provider schema

`Index`, `P` (emirate code), `PROVIDER TYPE`, `PROVIDER NAME`, `AREA`, `ADDRESS`,
`TELEPHONE`, `lat`, `lon`, `confidence`, `formatted`

Emirate codes: AJM, AUH, DXB, FUJ, RAK, SHJ, UMQ, ALAIN

### Plan network caveat

Most legacy per-plan files filter the full registry by the plan's **emirate
coverage**. Takafol Emarat's 41 imported network lists and the ADNIC directory
use official name/phone matches where the provider registry has an identity.
Unmatched source rows remain in `data/network-unmatched.json` for review.

## Rebuilding data

```bash
python3 build_data.py
python3 assign_networks.py
```

Regenerates `data/` from `sources/merged-registry.json` and applies official
network membership where a configured plan has a matching source. See
**[MAINTENANCE.md](MAINTENANCE.md)** for the full data pipeline.

## Docs

- **[MAINTENANCE.md](MAINTENANCE.md)** — data lineage, how to rebuild, geocode the backlog, add real insurer networks, add plans/providers

## Sources

- Provider registry: UAE MOH facility lists, geocoded via [Geoapify](https://www.geoapify.com/) / [Mapbox](https://www.mapbox.com/pricing), enriched via ox-alpha (OpenRouter)
- Official network sources: [Orient](https://www.insuranceuae.com/medical-insurance/individual/individual/) and [Union Insurance](https://www.unioninsurance.ae/en-us/medical-network/) workbooks are stored under `sources/networks/`.
- Sukoon’s public EDGE provider locator is stored as `sources/networks/Sukoon Insurance.csv` with coordinates for 3,381 providers.
- `data/network-unmatched.json` records official-source facilities that still need registry identity matching; these are not silently treated as plan members.
- [Zavis](https://www.zavis.ai/directory) is used as a public directory cross-check; popup searches use provider name and phone number.
- Map: [Leaflet](https://leafletjs.com/) + [markercluster](https://github.com/Leaflet/Leaflet.markercluster), tiles © OpenStreetMap contributors
