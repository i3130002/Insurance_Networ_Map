# Maintainer Guide — Insurance-Network-Map

How this repo's data flows, where every CSV came from, and how to extend it.
Everything regenerates from `sources/` via `build_data.py`.

```
sources/csv/*.csv          raw + processed source data (do not hand-edit)
sources/networks/          per-insurer official network CSVs (add these!)
sources/merged-registry.json   deduped merge of registry + repo data
        │
        ▼
build_data.py              validates coords, dedupes, splits per plan
        │
        ▼
data/*.json                what the website and review tools load
```

---

## 1. What's in `sources/csv/`

| File | Rows | What it is |
|---|---|---|
| `moh-registry-original.csv` | 2,216 | Baseline MOH facility list (Ajman/Al Ain/Abu Dhabi batch). Names, areas, addresses, phones. No coords. |
| `moh-registry-maps-links.csv` | 2,216 | Same + address-based Google Maps *search* links (not coordinate pins). |
| `moh-registry-geocoded-geoapify.csv` | 2,216 | Same + LATITUDE/LONGITUDE/GEOCODE_STATUS. Early pass: most coords are emirate-center fallbacks — treat as low quality. |
| `moh-registry-oxalpha-enriched.csv` | 2,216 | Same + websites/notes enriched via ox-alpha (OpenRouter `stealth/ox-alpha`). Coordinates in this file are still area-level, NOT building-level. |
| `merged-providers.csv` | 2,583 | Deduped union of the original 1,382 (`ecare-blue.json`, Geoapify-geocoded, building-level) + the 2,216 MOH rows. 1,201 net new entries. This is the best single source of truth. |
| `provider-network-xref.csv` | 2,216 | Provider → insurance network guess from name/notes keyword matching (NMC, Shifa/ADICO, Right Health/DARIC, …). Heuristic — not official. |
| `uae-insurance-plans.csv` | 15 | 8 insurers × 15 plans: name, homepage, emirate coverage, coverage type, known network hospitals/clinics. |

**Coordinate quality, honestly:**
- `merged-providers.csv` rows that came from the old `ecare-blue.json` have real building-level Geoapify coords (with `confidence`).
- Rows that came from the MOH batch mostly have empty or area-level coords.
- `data/needs-geocoding.json` (currently 174 entries) is exactly the backlog of rows without usable pins.

## 2. Rebuilding the site data

```bash
python3 build_data.py
python3 assign_networks.py
```

What it does:
1. Loads `sources/merged-registry.json` (2,583 entries).
2. Normalizes names (strips LLC/branch noise), dedupes (keeps the record with better coords/address).
3. Keeps only coordinates inside the UAE bounding box → `data/moh-complete.json`.
4. Writes unusable-coordinate rows to `data/needs-geocoding.json` so they're tracked, not silently broken.
5. Splits providers per insurance plan (see §4) → `data/<plan-id>.json` + `data/plans.json`.

After rebuilding and applying network assignments, sanity-check:

```bash
python3 - <<'EOF'
import json, glob
for f in glob.glob('data/*.json'):
    if f.endswith('plans.json') or f.endswith('needs-geocoding.json'): continue
    d = json.load(open(f))
    if isinstance(d, list) and d and 'lat' in d[0]:
        bad = sum(1 for e in d if not e.get('lat') or not e.get('lon'))
        assert bad == 0, f'{f}: {bad} entries missing coords'
print('all plan files clean')
EOF
```

Then run the data validator:

```bash
python3 validate_data.py
```

It checks `data/plans.json`, every referenced plan file, provider fields and types,
emirate codes, coordinate values and UAE bounds, provider counts, and optional
network-assignment indexes, and the official-network unmatched review report.
The command must pass before deployment.

## 3. Geocoding the backlog

`data/needs-geocoding.json` holds providers with no valid pin. To fix:

1. Pick a geocoder:
   - **Nominatim** (free, 1 req/sec, no key): `https://nominatim.openstreetmap.org/search?q=<address>&countrycodes=ae&format=json`
   - **Geoapify** (what the original data used; free tier): `https://api.geoapify.com/v1/geocode/search?text=<address>&apiKey=<KEY>`
2. Query with `PROVIDER NAME + ADDRESS + AREA + emirate name + UAE`.
3. Accept a result only if it lands in the UAE bounding box (lat 22–26.6, lon 51–56.6) **and** the returned address contains the expected emirate — ~42% of the old geocodes were wrong-emirate, so verify.
4. Merge results back into `sources/merged-registry.json` (fill `lat`/`lon`, set `confidence`), then re-run `build_data.py`.

Rate-limit politely: 1 req/sec Nominatim, ~174 entries ≈ 3 min.

## 4. Adding a REAL insurance network

Per-plan files are currently **emirate-coverage approximations** (every provider in the plan's emirates). To make a plan accurate:

1. Get the insurer's official network list (usually a CSV/PDF from the insurer portal: provider name, branch, emirate, sometimes network tier).
2. Save it as `sources/networks/<plan-id>.csv` with at least columns: `PROVIDER NAME`, `EMIRATE` (one of AJM/AUH/DXB/FUJ/RAK/SHJ/UMQ/ALAIN), optionally `NETWORK_TIER`, `AREA`, `ADDRESS`.
3. In `build_data.py`, replace the emirate-filter in the per-plan loop with a join against that CSV (match on normalized name + emirate — reuse `norm_name()`).
4. Re-run `build_data.py`. The plan file then contains only genuine network members, and `plans.json` can carry a `"network_source": "official"` flag.

Known official source: [Takaful Emarat's network page](https://takafulemarat.com/your-network/) lists 43 public Microsoft SharePoint workbooks for NAS, Nextcare, MedNet, NorthCare, APN, and AM networks. Direct workbook export returned HTTP 403 during the 2026-08-28 refresh; do not mark Takafol membership official until the files can be downloaded and mapped to products.

Additional official sources: [Orient's network page](https://www.insuranceuae.com/medical-insurance/individual/individual/) provides downloadable Nextcare and MedNet workbooks; [Union Insurance's network page](https://www.unioninsurance.ae/en-us/medical-network/) provides eCare Blue and NAS workbooks. These are stored as `sources/networks/Orient Insurance.csv` and `sources/networks/Union Insurance.csv`; they are not assigned to a configured plan until matching plan metadata exists.

`assign_networks.py` writes `data/network-unmatched.json` with official-list records
that do not match the provider registry by normalized name and emirate. Review this
file before adding aliases or manual matches.

The [Sukoon provider locator](https://www.sukoon.com/health-insurance/clinic-hospital-list?networkType=EDGE&emirate=Dubai) exposes a public read-only lookup endpoint with coordinates. The current source stores 3,381 EDGE providers across eight emirates in `sources/networks/Sukoon Insurance.csv`.

Fuzzy-matching tip: insurer lists write names differently ("NMC Medical Centre LLC" vs "NMC MEDICAL CENTER L.L.C"). `norm_name()` handles the common cases; consider `rapidfuzz` (token_set_ratio > 90) for the rest, and keep an explicit override map for recurring mismatches.

## 5. Adding a new plan (metadata only)

Edit `PLANS` in `build_data.py`:

```python
('newplan-id', 'Display Name', 'Insurer', 'Inpatient|Outpatient|Both', ['DXB','SHJ']),
```

Re-run. `data/plans.json`, the dropdown (grouped by insurer), and the plan file all update automatically. Also add a row to `sources/csv/uae-insurance-plans.csv` so the metadata stays in one place.

## 6. Adding new providers

1. New CSV must carry at minimum: `PROVIDER NAME`, `EMIRATE` (P-code), `PROVIDER TYPE` (CLINIC/HOSPITAL/PHARMACY/DENTAL/DIAGNOSTIC CENTRE/DAYCARE), `ADDRESS`, `AREA`, `TELEPHONE`; `lat`/`lon` if available.
2. Normalize the emirate column to P-codes (`Ajman` → `AJM`, `Al Ain` → `ALAIN`).
3. Append to `sources/merged-registry.json` (same JSON shape as existing entries, new `Index`).
4. `python3 build_data.py` — dedupe + coord validation happen automatically. Rows failing validation land in `needs-geocoding.json`, not on the map.

## 7. Website

Static site — GitHub Pages serves the repo root. `index.html` fetches `data/plans.json` at load, builds the insurer-grouped dropdown, and loads the chosen `data/<plan-id>.json` into a marker cluster layer. No build step, no server.

Known limits (fine to ignore until they bite):
- All plan JSON loads are full-file fetches; if a plan file ever exceeds ~5 MB, switch to serving filtered subsets or add a pagination control.
- Popups render on demand (Leaflet lazy-render), so 800-marker plans stay smooth.

## 8. Conventions

- Emirate codes everywhere in data: `AJM AUH DXB FUJ RAK SHJ UMQ ALAIN` (note: `ALAIN` is one token, not `ALN`).
- `PROVIDER TYPE` is always uppercase, from the fixed set in §6.
- Never hand-edit `data/*.json` — change `sources/`, re-run `build_data.py`.
- Provider identity = (normalized name, emirate). Two records matching that are the same provider; `build_data.py` keeps the better-geocoded one.

## 9. Current state / TODO

- [x] 2,390-provider deduped registry, all 8 emirates
- [x] 15 plans / 8 insurers wired into the dropdown
- [ ] Geocode the 174-entry backlog (§3) — **highest impact next step**
- [ ] Replace emirate-approximation plans with official network lists (§4)
- [ ] Dedupe review: some kept "duplicates" may be genuine branches — spot-check a sample
- [ ] Provider-network-xref (§1) is heuristic; rebuild it against official lists
