#!/usr/bin/env python3
"""
Geocode the needs-geocoding backlog via Nominatim (OSM).
- 1 req/sec hard politeness limit
- Only accepts results inside the UAE bounding box
- Cross-checks the returned address contains the expected emirate
  (or an area token) — the old dataset had a 42% wrong-emirate rate
- Writes progress to sources/merged-registry.json incrementally and
  a summary to geocode_run_report.json
"""
import json
import csv
from difflib import SequenceMatcher
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(ROOT, 'sources', 'merged-registry.json')
BACKLOG = os.path.join(ROOT, 'data', 'needs-geocoding.json')
REPORT = os.path.join(ROOT, 'geocode_run_report.json')
NETWORKS_DIR = os.path.join(ROOT, 'sources', 'networks')

UA = 'InsuranceNetworkMap/1.0 (UAE provider directory; contact: repo owner)'
LAT_MIN, LAT_MAX = 22.0, 26.6
LON_MIN, LON_MAX = 51.0, 56.6

EMIRATE_TOKENS = {
    'AJM': ['ajman', 'عجمان'],
    'AUH': ['abu dhabi', 'abu zaby', 'أبوظبي', 'أبو ظبي'],
    'DXB': ['dubai', 'dubayy', 'دبي'],
    'FUJ': ['fujairah', 'al fujairah', 'الفجيرة'],
    'RAK': ['ras al khaimah', 'رأس الخيمة'],
    'SHJ': ['sharjah', 'ash shariqah', 'الشارقة'],
    'UMQ': ['umm al quwain', 'أم القيوين', 'ام القيوين'],
    'ALAIN': ['al ain', 'abu dhabi', 'العين', 'أبوظبي', 'أبو ظبي'],
}


def norm_name(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    for t in ('LLC', 'L L C', 'SOLE PROPRIETORSHIP', 'BRANCH', 'BR', 'LTD',
              'CENTER', 'CENTRE'):
        s = re.sub(rf'\b{re.escape(t)}\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def branch_number(name):
    """Return a branch number when the provider name explicitly contains one."""
    match = re.search(r'\b(?:BRANCH|BR)[ .-]*(\d+)\b', (name or '').upper())
    return match.group(1) if match else None


def load_official_locations():
    """Load official network CSV rows that include usable coordinates."""
    locations = []
    if not os.path.isdir(NETWORKS_DIR):
        return locations
    for filename in os.listdir(NETWORKS_DIR):
        if not filename.endswith('.csv'):
            continue
        path = os.path.join(NETWORKS_DIR, filename)
        with open(path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                try:
                    float(row.get('lat', ''))
                    float(row.get('lon', ''))
                except (TypeError, ValueError):
                    continue
                row['_source'] = os.path.splitext(filename)[0]
                locations.append(row)
    return locations


def official_match(entry, network):
    """Return a high-confidence ADNIC coordinate match, or ``None``.

    Matching is restricted to the same emirate and rejects conflicting explicit
    branch numbers. This prevents a nearby branch from receiving another
    branch's coordinates.
    """
    emirate = entry.get('P', '').upper()
    candidates = []
    name = norm_name(entry.get('PROVIDER NAME'))
    entry_branch = branch_number(entry.get('PROVIDER NAME'))
    for row in network:
        if row.get('EMIRATE', '').upper() != emirate:
            continue
        row_branch = branch_number(row.get('PROVIDER NAME'))
        if entry_branch and not row_branch:
            continue
        if entry_branch and row_branch and entry_branch != row_branch:
            continue
        score = SequenceMatcher(
            None, name, norm_name(row.get('PROVIDER NAME'))).ratio()
        left = set(name.split())
        right = set(norm_name(row.get('PROVIDER NAME')).split())
        overlap = len(left & right) / max(1, len(left | right))
        candidates.append((score, overlap, row))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if not candidates:
        return None
    best = candidates[0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0
    if best[0] < 0.92 or best[1] < 0.5 or best[0] - second_score < 0.04:
        return None
    try:
        float(best[2]['lat'])
        float(best[2]['lon'])
    except (KeyError, ValueError):
        return None
    return (best[2]['lat'], best[2]['lon'],
            f"{best[2]['_source']} official network: "
            f"{best[2]['PROVIDER NAME']}",
            'official_network_fuzzy')


def nominatim(query, limit=1):
    url = ('https://nominatim.openstreetmap.org/search?'
           + urllib.parse.urlencode({
               'q': query, 'countrycodes': 'ae', 'format': 'json',
               'limit': limit, 'addressdetails': 0}))
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def geocode_one(entry, official_network, allow_external=True):
    """Return (lat, lon, display, confidence) or None."""
    local = official_match(entry, official_network)
    if local:
        return local
    if not allow_external:
        return None

    em = entry.get('P', '')
    name = entry.get('PROVIDER NAME', '')
    area = entry.get('AREA', '')
    addr = entry.get('ADDRESS', '')
    em_name = {'AJM': 'Ajman', 'AUH': 'Abu Dhabi', 'DXB': 'Dubai',
               'FUJ': 'Fujairah', 'RAK': 'Ras Al Khaimah', 'SHJ': 'Sharjah',
               'UMQ': 'Umm Al Quwain', 'ALAIN': 'Al Ain'}.get(em, '')

    # Try progressively simpler queries
    queries = [
        f'{name}, {area}, {em_name}, UAE',
        f'{name}, {em_name}, UAE',
        f'{area}, {em_name}, UAE',
    ]
    for q in queries:
        try:
            results = nominatim(q)
        except Exception:
            time.sleep(2)
            continue
        for res in results:
            try:
                la, lo = float(res['lat']), float(res['lon'])
            except (KeyError, ValueError):
                continue
            if not (LAT_MIN <= la <= LAT_MAX and LON_MIN <= lo <= LON_MAX):
                continue
            display = (res.get('display_name') or '').lower()
            tokens = EMIRATE_TOKENS.get(em, [])
            # Require emirate token in the returned address
            if tokens and not any(t in display for t in tokens):
                continue
            # For queries with the name, require some name overlap
            if q.startswith(name):
                name_tokens = [w for w in norm_name(name).split() if len(w) > 2]
                hit = sum(1 for w in name_tokens if w in display)
                if name_tokens and hit / len(name_tokens) < 0.4:
                    continue
                return la, lo, res.get('display_name', ''), 'name_match'
            return la, lo, res.get('display_name', ''), 'area_match'
        time.sleep(1.1)  # politeness between queries
    return None


def main():
    local_only = os.getenv('LOCAL_ONLY') == '1'
    with open(BACKLOG, encoding='utf-8') as f:
        backlog = json.load(f)
    with open(REG, encoding='utf-8') as f:
        registry = json.load(f)
    official_network = load_official_locations()

    # Index registry by (norm name, P) to patch entries
    idx = {}
    for i, r in enumerate(registry):
        idx.setdefault((norm_name(r['PROVIDER NAME']), r['P']), []).append(i)

    # Skip any already-fixed in prior interrupted runs
    remaining = [e for e in backlog
                 if not (e.get('lat') and e.get('lon'))]
    print(f'{len(backlog)} backlog entries, {len(remaining)} still pending')

    stats = {'geocoded': 0, 'failed': 0, 'skipped_existing': 0}
    failures = []
    done = 0

    for entry in remaining:
        done += 1
        if entry.get('lat') and entry.get('lon'):
            stats['skipped_existing'] += 1
            continue

        result = geocode_one(entry, official_network, not local_only)
        if not result and not local_only:
            time.sleep(1.1)  # Nominatim politeness

        if result:
            la, lo, display, conf = result
            entry['lat'], entry['lon'] = str(la), str(lo)
            entry['confidence'] = conf
            entry['formatted'] = display
            stats['geocoded'] += 1
            # Patch the registry
            for i in idx.get((norm_name(entry['PROVIDER NAME']),
                              entry['P']), []):
                if not (registry[i].get('lat') and registry[i].get('lon')):
                    registry[i]['lat'] = str(la)
                    registry[i]['lon'] = str(lo)
                    registry[i]['confidence'] = conf
                    registry[i]['formatted'] = display
        else:
            stats['failed'] += 1
            failures.append({'PROVIDER NAME': entry.get('PROVIDER NAME'),
                             'P': entry.get('P'), 'ADDRESS': entry.get('ADDRESS')})

        if done % 10 == 0:
            print(f'[{done}/{len(remaining)}] ok={stats["geocoded"]} '
                  f'fail={stats["failed"]}')
            # checkpoint
            with open(REG, 'w', encoding='utf-8') as f:
                json.dump(registry, f, ensure_ascii=False, indent=1)
            with open(BACKLOG, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, ensure_ascii=False, indent=1)

    # Final write
    with open(REG, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=1)
    with open(BACKLOG, 'w', encoding='utf-8') as f:
        json.dump(backlog, f, ensure_ascii=False, indent=1)
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump({'stats': stats, 'failures': failures}, f,
                  ensure_ascii=False, indent=2)

    print(f'DONE: {stats}')


if __name__ == '__main__':
    main()
