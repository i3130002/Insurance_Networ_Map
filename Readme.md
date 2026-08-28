# UAE Insurance Network Map

Interactive map of UAE healthcare providers, filterable by insurance plan.

**Live:** https://i3130002.github.io/Insurance-Network-Map/

## Features

- 2,390 unique providers (clinics, hospitals, pharmacies, dental, diagnostic, daycare) across all 8 emirates
- 15 insurance plans from 8 insurers (ADNIC, AXA Gulf, Aman, DARIC, Emirates NBD, Gulf Insurance, Noor Takaful, Takafol Emarat)
- Marker clustering for performance; color-coded provider types
- Popups with Google Maps link + AI search query per provider

## Data

| File | Contents |
|---|---|
| `data/moh-complete.json` | Full provider registry (deduped, valid coordinates) |
| `data/needs-geocoding.json` | Providers still missing reliable coordinates (200) |
| `data/plans.json` | Plan metadata (name, insurer, coverage, emirates, provider count) |
| `data/<plan-id>.json` | Per-plan provider subsets |

### Provider schema

`Index`, `P` (emirate code), `PROVIDER TYPE`, `PROVIDER NAME`, `AREA`, `ADDRESS`,
`TELEPHONE`, `lat`, `lon`, `confidence`, `formatted`

Emirate codes: AJM, AUH, DXB, FUJ, RAK, SHJ, UMQ, ALAIN

### Plan network caveat

Most per-plan files currently filter the full registry by the plan's **emirate
coverage**. The ADNIC plans also use matches from the official ADNIC directory.
True plan-level membership for the other insurers requires each insurer's
official provider list.

## Rebuilding data

```bash
python3 build_data.py
```

Regenerates `data/` from `sources/merged-registry.json`. See **[MAINTENANCE.md](MAINTENANCE.md)** for the full data pipeline.

## Docs

- **[MAINTENANCE.md](MAINTENANCE.md)** — data lineage, how to rebuild, geocode the backlog, add real insurer networks, add plans/providers

## Sources

- Provider registry: UAE MOH facility lists, geocoded via [Geoapify](https://www.geoapify.com/) / [Mapbox](https://www.mapbox.com/pricing), enriched via ox-alpha (OpenRouter)
- Official network sources: [Orient](https://www.insuranceuae.com/medical-insurance/individual/individual/) and [Union Insurance](https://www.unioninsurance.ae/en-us/medical-network/) workbooks are stored under `sources/networks/`.
- Map: [Leaflet](https://leafletjs.com/) + [markercluster](https://github.com/Leaflet/Leaflet.markercluster), tiles © OpenStreetMap contributors
