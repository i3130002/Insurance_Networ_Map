#!/usr/bin/env python3
"""
Network assignment engine.

Assigns providers to insurance networks in layers, most-reliable first:

  L1 official   — a per-insurer network CSV exists in sources/networks/
                  (columns: PROVIDER NAME, EMIRATE[, NETWORK_TIER]).
                  Exact/fuzzy name+emirate match. This is authoritative.

  L2 chain      — provider belongs to a known multi-branch chain group
                  (NMC, Aster, Burjeel, Medcare, ...). Chains sign group-wide
                  agreements with insurers, so chain membership implies
                  network membership for insurers that list the chain.

  L3 geographic — fallback: provider is in an emirate the plan covers.
                  Marked clearly as 'geo_only' so the UI can badge it.

Outputs data/network-assignments.json consumed by build_data.py.
"""
import csv
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
NETWORKS_DIR = os.path.join(ROOT, 'sources', 'networks')
PLANS_CSV = os.path.join(ROOT, 'sources', 'csv', 'uae-insurance-plans.csv')
LAT_MIN, LAT_MAX = 22.0, 26.6
LON_MIN, LON_MAX = 51.0, 56.6

# Chain groups: parent org -> name tokens that identify its facilities.
# These chains sign group-level contracts, so every branch inherits them.
CHAINS = {
    'NMC Healthcare':      ['NMC'],
    'Aster DM Healthcare': ['ASTER', 'MEDCARE', 'ACCESS CLINIC'],
    'Burjeel / VPS':       ['BURJEEL', 'PHOENIX HOSPITAL', 'MEDICLINIC'],
    'Lifecare / CCS':      ['LIFECARE', 'RIGHT HEALTH', 'RIGHT MEDICAL'],
    'LLH Group':           ['LLH'],
    'Zulekha Healthcare':  ['ZULEKHA'],
    'Prime Medical':       ['PRIME MEDICAL', 'PRIME HOSPITAL'],
    'Mediclinic Middle East': ['MEDICLINIC', 'WELLCARE'],
    'Al Zahra':            ['AL ZAHRA', 'ZAHRA HOSPITAL'],
    'Saudi German':        ['SAUDI GERMAN'],
    'Canadian Specialist': ['CANADIAN SPECIALIST', 'CANADIAN MEDICAL'],
    'Emirates Hospitals':  ['EMIRATES HOSPITAL', 'EMIRATES MEDICAL CENTRE'],
    'HealthHub / Al-Futtaim': ['HEALTHHUB'],
    'Doclib / Al Thor':    ['DOCLIB'],
    'Manzil /aya':         ['AL AMANAH', 'AL AMANA'],
}

# Which chains each insurer includes, per known group agreements (public info).
# Plans not listed here get L3 geo-only until official lists arrive.
INSURER_CHAINS = {
    'ADNIC':                ['NMC Healthcare', 'Burjeel / VPS', 'LLH Group'],
    'AXA Gulf':             ['Aster DM Healthcare', 'Mediclinic Middle East',
                             'Burjeel / VPS', 'Emirates Hospitals'],
    'Aman Insurance':       ['NMC Healthcare', 'Lifecare / CCS', 'LLH Group',
                             'Zulekha Healthcare', 'Prime Medical'],
    'DARIC':                ['NMC Healthcare', 'Aster DM Healthcare',
                             'Lifecare / CCS', 'Zulekha Healthcare'],
    'Emirates NBD Ins.':    ['Aster DM Healthcare', 'Emirates Hospitals',
                             'Mediclinic Middle East'],
    'Gulf Insurance':       ['NMC Healthcare', 'Aster DM Healthcare',
                             'Prime Medical'],
    'Noor Takaful':         ['Al Zahra', 'Saudi German', 'NMC Healthcare'],
    'Takafol Emarat':       ['Al Zahra', 'Saudi German', 'NMC Healthcare'],
}


def norm_name(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    for t in ('LLC', 'L L C', 'SOLE PROPRIETORSHIP', 'BRANCH', 'BR', 'LTD'):
        s = re.sub(rf'\b{re.escape(t)}\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def norm_phone(value):
    """Normalize one UAE phone number for cross-source matching."""
    digits = re.sub(r'\D', '', value or '')
    if digits.startswith('00971'):
        digits = digits[5:]
    elif digits.startswith('971'):
        digits = digits[3:]
    if digits.startswith('0'):
        digits = digits[1:]
    return digits if len(digits) >= 7 else ''


def phone_values(value):
    """Return normalized values when a source lists multiple phone numbers."""
    values = {norm_phone(part) for part in re.split(r'[;,/|]+', value or '')}
    return {value for number in values if (value := number)} | {
        value[-7:] for value in values if value and len(value) > 7
    }


def load_official_networks():
    """Load insurer CSVs and imported Takafol network members."""
    official = {}  # source key -> {'members': set, 'phones': set}
    if not os.path.isdir(NETWORKS_DIR):
        return official
    for fn in os.listdir(NETWORKS_DIR):
        if not fn.endswith('.csv'):
            continue
        source_key = os.path.splitext(fn)[0]
        members = set()
        phones = set()
        with open(os.path.join(NETWORKS_DIR, fn), encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                name = norm_name(row.get('PROVIDER NAME', ''))
                em = (row.get('EMIRATE') or '').strip().upper()
                if name and em:
                    members.add((name, em))
                for phone in phone_values(row.get('TELEPHONE', '')):
                    if em:
                        phones.add((phone, em))
        if members:
            official[source_key] = {'members': members, 'phones': phones}
            print(f'  official list: {source_key}: {len(members)} facilities')

    takafol_path = os.path.join(
        ROOT, 'sources', 'csv', 'takafol-network-members.csv')
    if os.path.exists(takafol_path):
        with open(takafol_path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                source_key = (row.get('NETWORK_ID') or '').strip()
                name = norm_name(row.get('PROVIDER NAME', ''))
                em = (row.get('EMIRATE') or '').strip().upper()
                if not source_key or not em:
                    continue
                source = official.setdefault(source_key, {'members': set(), 'phones': set()})
                if name:
                    source['members'].add((name, em))
                for phone in phone_values(row.get('TELEPHONE', '')):
                    source['phones'].add((phone, em))
        for source_key, source in sorted(official.items()):
            if source_key.startswith(('aaf', 'am-', 'ecare-', 'mednet-', 'nas-', 'nextcare-')):
                print(f'  official list: {source_key}: {len(source["members"])} facilities')
    return official


def chain_of(provider_name):
    n = norm_name(provider_name)
    for chain, tokens in CHAINS.items():
        for t in tokens:
            if t in n:
                return chain
    return None


def coord_ok(provider):
    """Return whether a provider is included in generated plan files."""
    try:
        lat, lon = float(provider.get('lat')), float(provider.get('lon'))
    except (TypeError, ValueError):
        return False
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def main():
    # Use the generated registry so indexes match the plan JSON files.
    registry = json.load(open(os.path.join(
        ROOT, 'data', 'moh-complete.json'), encoding='utf-8'))
    plans = json.load(open(os.path.join(
        ROOT, 'data', 'plans.json'), encoding='utf-8'))

    print('Loading official network lists...')
    official = load_official_networks()
    registry_identities = {
        (norm_name(r['PROVIDER NAME']), r['P']) for r in registry
    }
    unmatched_official = {
        source_key: [
            {'PROVIDER NAME': name, 'EMIRATE': emirate}
            for name, emirate in sorted(source['members'] - registry_identities)
        ]
        for source_key, source in official.items()
    }

    # Precompute chain membership
    for r in registry:
        r['_chain'] = chain_of(r['PROVIDER NAME'])

    assignments = {}   # plan_id -> list of provider Index
    layers = defaultdict(lambda: defaultdict(int))

    for plan in plans:
        insurer = plan['insurer']
        plan_emirates = set(plan['emirates'])
        members = []
        chain_allow = set(INSURER_CHAINS.get(insurer, []))
        source_key = plan.get('network_id') or insurer
        official_source = official.get(source_key)
        official_set = official_source['members'] if official_source else None
        official_phones = official_source['phones'] if official_source else set()

        for r in registry:
            if not coord_ok(r):
                continue
            em = r['P']
            n = norm_name(r['PROVIDER NAME'])
            phones = phone_values(r.get('TELEPHONE', ''))
            layer = None
            name_match = official_set is not None and (n, em) in official_set
            phone_match = bool(official_phones.intersection((phone, em) for phone in phones))
            if official_set is not None and em in plan_emirates and (name_match or phone_match):
                layer = 'official'
            elif official_set is None and r['_chain'] and r['_chain'] in chain_allow and em in plan_emirates:
                layer = 'chain'
            elif official_set is None and em in plan_emirates:
                layer = 'geo_only'
            if layer:
                members.append({'index': r['Index'], 'layer': layer,
                                'chain': r['_chain']})
                layers[plan['id']][layer] += 1

        assignments[plan['id']] = members
        if official_set is not None:
            official_indexes = {
                member['index'] for member in members if member['layer'] == 'official'
            }
            plan_path = os.path.join(ROOT, plan['file'])
            with open(plan_path, encoding='utf-8') as f:
                plan_providers = json.load(f)
            plan_providers = [
                provider for provider in plan_providers
                if provider['Index'] in official_indexes
            ]
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump(plan_providers, f, ensure_ascii=False, indent=1)
            plan['providers'] = len(plan_providers)
        c = layers[plan['id']]
        print(f"{plan['name']:35s} official={c['official']:5d} "
              f"chain={c['chain']:5d} geo={c['geo_only']:5d}")

    with open(os.path.join(ROOT, 'data', 'network-assignments.json'), 'w',
              encoding='utf-8') as f:
        json.dump({'plans': {pid: dict(v) for pid, v in layers.items()},
                   'assignments': assignments}, f, ensure_ascii=False)

    with open(os.path.join(ROOT, 'data', 'network-unmatched.json'), 'w',
              encoding='utf-8') as f:
        json.dump(unmatched_official, f, ensure_ascii=False, indent=2)

    # Annotate plans.json with layer counts
    for plan in plans:
        plan['layers'] = dict(layers[plan['id']])
        source_key = plan.get('network_id') or plan['insurer']
        plan['network_source'] = ('official' if source_key in official
                                  else 'chain+geo')
    with open(os.path.join(ROOT, 'data', 'plans.json'), 'w',
              encoding='utf-8') as f:
        json.dump(plans, f, ensure_ascii=False, indent=2)

    print('\nWrote data/network-assignments.json + updated plans.json')
    print('NOTE: geo_only memberships are approximations. Drop official')
    print('CSVs into sources/networks/ (named e.g. "Aman Insurance.csv")')
    print('and re-run to upgrade a plan to authoritative data.')


if __name__ == '__main__':
    main()
