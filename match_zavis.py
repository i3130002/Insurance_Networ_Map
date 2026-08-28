#!/usr/bin/env python3
"""Build a one-time provider crosswalk between the registry and Zavis."""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CITY_CODES = {
    "abu dhabi": "AUH", "al ain": "ALAIN", "ajman": "AJM", "dubai": "DXB",
    "fujairah": "FUJ", "ras al khaimah": "RAK", "sharjah": "SHJ",
    "umm al quwain": "UMQ",
}
FIELDS = ("Index", "match_method", "zavis_id", "zavis_name", "zavis_url",
          "zavis_city", "zavis_category", "zavis_address", "zavis_phone")


def norm_name(value: str) -> str:
    """Normalize provider names for exact identity comparison."""
    value = re.sub(r"[^A-Z0-9 ]", " ", (value or "").upper())
    value = re.sub(r"\b(LLC|L L C|SOLE PROPRIETORSHIP|BRANCH|CENTRE|CENTER)\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def phone_values(value: str) -> set[str]:
    """Return normalized full and local suffixes for one or more phones."""
    values = set()
    for part in re.split(r"[;,/|]+", value or ""):
        digits = re.sub(r"\D", "", part)
        if digits.startswith("00971"):
            digits = digits[5:]
        elif digits.startswith("971"):
            digits = digits[3:]
        if digits.startswith("0"):
            digits = digits[1:]
        if len(digits) >= 7:
            values.add(digits)
            values.add(digits[-7:])
    return values


def city_to_emirate(city: str) -> str:
    """Map a Zavis city label to the registry emirate code."""
    key = re.sub(r"\s+", " ", (city or "").casefold()).strip()
    return CITY_CODES.get(key, "")


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV source."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def choose_match(provider: dict[str, str], by_phone: dict[tuple[str, str], list[dict[str, str]]],
                 by_name: dict[tuple[str, str], list[dict[str, str]]]) -> tuple[dict[str, str] | None, str]:
    """Choose a unique phone match, then a unique name/emirate match."""
    emirate = provider.get("P", "")
    phone_matches = {id(row): row for phone in phone_values(provider.get("TELEPHONE", ""))
                     for row in by_phone.get((phone, emirate), [])}
    if len(phone_matches) == 1:
        return next(iter(phone_matches.values())), "phone"
    name_matches = by_name.get((norm_name(provider.get("PROVIDER NAME", "")), emirate), [])
    return (name_matches[0], "name") if len(name_matches) == 1 else (None, "")


def main() -> int:
    """Build and write the registry-to-Zavis crosswalk."""
    registry = json.loads((ROOT / "data/moh-complete.json").read_text(encoding="utf-8"))
    zavis = read_csv(ROOT / "sources/csv/zavis-providers.csv")
    by_phone: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_name: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in zavis:
        emirate = city_to_emirate(row.get("city", ""))
        for phone in phone_values(row.get("phone", "")):
            by_phone[(phone, emirate)].append(row)
        by_name[(norm_name(row.get("name", "")), emirate)].append(row)
    matches = []
    counts = defaultdict(int)
    for provider in registry:
        row, method = choose_match(provider, by_phone, by_name)
        counts[method or "unmatched"] += 1
        matches.append({
            "Index": provider["Index"], "match_method": method,
            "zavis_id": row.get("id", "") if row else "",
            "zavis_name": row.get("name", "") if row else "",
            "zavis_url": row.get("url", "") if row else "",
            "zavis_city": row.get("city", "") if row else "",
            "zavis_category": row.get("category", "") if row else "",
            "zavis_address": row.get("address", "") if row else "",
            "zavis_phone": row.get("phone", "") if row else "",
        })
    output = ROOT / "sources/csv/zavis-provider-matches.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(matches)
    print(f"Matched {len(matches) - counts['unmatched']} of {len(matches)} registry providers: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
