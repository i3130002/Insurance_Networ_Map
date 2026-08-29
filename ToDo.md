# To-do

Prioritized work for completing the Insurance Network Map.

## P0 — Data completeness

- [ ] Retry the seven Zavis pages that returned HTTP 503.
- [ ] Re-run the Zavis crawl and verify deduplication and record counts.
- [x] Fetch usable coordinates for matched providers still missing them; no
      matched provider remains in the current 106-record coordinate backlog.
- [ ] Match the remaining 1,253 registry providers to Zavis using phone, name, emirate, and address review.
- [ ] Resolve the remaining 106 providers without coordinates.

## P1 — Network accuracy

- [ ] Replace approximate plans with official network sources for AXA, Aman, DARIC, Emirates NBD, Gulf Insurance, Noor Takaful, and the generic Takafol plan.
- [ ] Review unmatched official-network rows, including the excluded MEDNET reimbursement list.
- [ ] Preserve source lineage and confidence for every plan and provider match.
- [ ] Review duplicate and ambiguous provider merges for false positives.

## P1 — Documentation and data quality

- [x] Update `objectives.html` with the current plan, provider, coordinate, and missing-data counts.
- [x] Validate provider names, phone numbers, addresses, provider types, and coordinate bounds.
- [x] Document the repeatable Zavis matching and enrichment workflow.

## P2 — Product and release

- [ ] Test the company → plan → map flow.
- [ ] Test provider search, filters, reset behavior, empty results, and mobile layout.
- [ ] Verify direct Zavis and Google Maps links.
- [ ] Check performance with the largest plan datasets.
- [ ] Run a GitHub Pages deployment smoke test.

## Repeatable data pipeline

```text
python3 extract_zavis.py --output sources/csv/zavis-providers.csv --workers 2
python3 match_zavis.py
python3 enrich_zavis.py
python3 build_data.py
python3 assign_networks.py
python3 validate_data.py
python3 -m unittest discover -p 'test_*.py'
```

Raw downloaded XLSX files remain ignored; refreshes must use public source URLs.
