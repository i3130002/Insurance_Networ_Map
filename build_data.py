#!/usr/bin/env python3
"""
Build script for Insurance-Network-Map data.

1. Dedupes + validates the merged MOH provider registry (2,583 entries).
2. Emits data/moh-complete.json (full registry) with valid coords only,
   invalid-coord entries preserved in data/needs-geocoding.json.
3. Emits per-insurance-plan JSON files by filtering against the plan's
   emirate coverage (network affiliations are heuristic until official
   network lists are supplied).
4. Emits data/plans.json with plan metadata for the UI.
"""
import csv
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)

# UAE bounding box (generous)
LAT_MIN, LAT_MAX = 22.0, 26.6
LON_MIN, LON_MAX = 51.0, 56.6

EMIRATE_NAMES = {
    'AJM': 'Ajman', 'AUH': 'Abu Dhabi', 'DXB': 'Dubai', 'FUJ': 'Fujairah',
    'RAK': 'Ras Al Khaimah', 'SHJ': 'Sharjah', 'UMQ': 'Umm Al Quwain',
    'ALAIN': 'Al Ain',
}


def norm_name(s: str) -> str:
    """Normalize a provider name for dedup comparison."""
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # Drop legal suffixes and branch noise
    for token in ('LLC', 'L L C', 'SOLE PROPRIETORSHIP', 'BRANCH 01', 'BRANCH 1',
                  'BRANCH 2', 'BRANCH 3', 'BRANCH', 'BR', 'LTD', 'CENTER',
                  'CENTRE'):
        s = re.sub(rf'\b{re.escape(token)}\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def coord_ok(lat, lon) -> bool:
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX


def load_merged() -> list:
    """Load the merged provider registry from this repository."""
    merged_path = os.path.join(ROOT, 'sources', 'merged-registry.json')
    with open(merged_path, encoding='utf-8') as f:
        entries = json.load(f)
    return entries


def build_registry(entries: list):
    seen = {}
    valid, invalid = [], []
    stats = Counter()

    for e in entries:
        name = (e.get('PROVIDER NAME') or '').strip()
        if not name:
            stats['no_name'] += 1
            continue

        key = (norm_name(name), (e.get('P') or '').strip())
        lat, lon = e.get('lat'), e.get('lon')

        rec = {
            'P': (e.get('P') or '').strip(),
            'PROVIDER TYPE': (e.get('PROVIDER TYPE') or '').strip(),
            'PROVIDER NAME': name,
            'AREA': (e.get('AREA') or '').strip(),
            'ADDRESS': (e.get('ADDRESS') or '').strip(),
            'TELEPHONE': str(e.get('TELEPHONE') or '').strip(),
            'lat': lat,
            'lon': lon,
            'confidence': e.get('confidence') or '',
            'formatted': (e.get('formatted') or '').strip(),
        }

        if key in seen:
            stats['dupes'] += 1
            # Keep the record with better data (coords + longer address)
            prev = seen[key]
            prev_has = coord_ok(prev['lat'], prev['lon'])
            cur_has = coord_ok(lat, lon)
            if cur_has and not prev_has:
                seen[key] = rec
            elif cur_has == prev_has and len(rec['ADDRESS']) > len(prev['ADDRESS']):
                seen[key] = rec
            continue

        seen[key] = rec
        if coord_ok(lat, lon):
            valid.append(rec)
            stats['valid'] += 1
        else:
            invalid.append(rec)
            stats['invalid'] += 1

    # Re-index
    out = []
    for i, rec in enumerate(seen.values(), 1):
        rec = dict(rec)
        rec['Index'] = i
        out.append(rec)
    valid = [rec for rec in out if coord_ok(rec['lat'], rec['lon'])]
    invalid = [rec for rec in out if not coord_ok(rec['lat'], rec['lon'])]
    stats['valid'] = len(valid)
    stats['invalid'] = len(invalid)
    return out, stats


PLANS = [
    # (plan_id, display name, insurer, coverage, emirate codes)
    ('adico-classic',      'ADNIC Classic',              'ADNIC',              'Inpatient',  ['AUH']),
    ('adico-premium',      'ADNIC Premium',              'ADNIC',              'Both',       ['AUH']),
    ('axa-basic',          'AXA Gulf Basic',             'AXA Gulf',           'Inpatient',  ['DXB', 'AUH', 'SHJ']),
    ('axa-premier',        'AXA Gulf Premier',           'AXA Gulf',           'Both',       ['DXB', 'AUH', 'SHJ']),
    ('aman-essential',     'Aman Essential',             'Aman Insurance',     'Outpatient', ['AJM', 'SHJ', 'FUJ', 'UMQ']),
    ('aman-comprehensive', 'Aman Comprehensive',         'Aman Insurance',     'Both',       ['AJM', 'SHJ', 'FUJ', 'UMQ']),
    ('daric-standard',     'DARIC Standard',             'DARIC',              'Inpatient',  ['DXB', 'SHJ', 'AJM']),
    ('daric-premium',      'DARIC Premium',              'DARIC',              'Both',       ['DXB', 'SHJ', 'AJM']),
    ('enbd-gold',          'Emirates NBD Gold',          'Emirates NBD Ins.',  'Both',       ['DXB', 'AUH']),
    ('enbd-silver',        'Emirates NBD Silver',        'Emirates NBD Ins.',  'Inpatient',  ['DXB', 'AUH']),
    ('gulf-essential',     'Gulf Insurance Essential',   'Gulf Insurance',     'Inpatient',  ['DXB', 'SHJ', 'AJM']),
    ('gulf-comprehensive', 'Gulf Insurance Comprehensive','Gulf Insurance',     'Both',       ['DXB', 'SHJ', 'AJM']),
    ('noor-family',        'Noor Takaful Family',        'Noor Takaful',       'Both',       ['DXB', 'AUH', 'SHJ']),
    ('noor-individual',    'Noor Takaful Individual',    'Noor Takaful',       'Outpatient', ['DXB', 'AUH', 'SHJ']),
    ('takafol-family',     'Takafol Emarat Family Takaful','Takafol Emarat',   'Both',       ['DXB', 'SHJ', 'AJM']),
]


def main():
    entries = load_merged()
    print(f'Loaded {len(entries)} raw entries')

    registry, stats = build_registry(entries)
    print(f'Registry: {stats["valid"]} valid coords, '
          f'{stats["invalid"]} invalid/missing, {stats["dupes"]} dupes removed')

    with open(os.path.join(DATA, 'moh-complete.json'), 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=1)

    with open(os.path.join(DATA, 'needs-geocoding.json'), 'w', encoding='utf-8') as f:
        json.dump(
            [{'PROVIDER NAME': r['PROVIDER NAME'], 'P': r['P'],
              'AREA': r['AREA'], 'ADDRESS': r['ADDRESS'],
              'TELEPHONE': r['TELEPHONE']} for r in registry if not coord_ok(r['lat'], r['lon'])],
            f, ensure_ascii=False, indent=1)

    # Per-plan datasets: all providers within the plan's emirate footprint.
    # (True network membership needs official provider lists from each insurer.)
    plans_meta = []
    for plan_id, display, insurer, coverage, ems in PLANS:
        subset = [r for r in registry if r['P'] in ems and coord_ok(r['lat'], r['lon'])]
        path = f'data/{plan_id}.json'
        with open(os.path.join(ROOT, path), 'w', encoding='utf-8') as f:
            json.dump(subset, f, ensure_ascii=False, indent=1)
        plans_meta.append({
            'id': plan_id, 'name': display, 'insurer': insurer,
            'coverage': coverage, 'emirates': ems,
            'file': path, 'providers': len(subset),
        })
        print(f'  {display:35s} {len(subset):5d} providers')

    with open(os.path.join(DATA, 'plans.json'), 'w', encoding='utf-8') as f:
        json.dump(plans_meta, f, ensure_ascii=False, indent=2)

    print(f'\nDone. Registry: {len(registry)} providers, {len(plans_meta)} plans.')


if __name__ == '__main__':
    main()
