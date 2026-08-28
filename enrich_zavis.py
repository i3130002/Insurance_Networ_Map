#!/usr/bin/env python3
"""Enrich matched registry providers with coordinates from Zavis detail pages."""

import csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from extract_zavis import parse_provider_detail, safe_fetch

ROOT = Path(__file__).resolve().parent


def enrich(row: dict[str, str]) -> dict[str, str]:
    """Fetch one matched provider detail page and append its coordinates."""
    if not row.get("zavis_url"):
        return row
    detail = parse_provider_detail(safe_fetch(row["zavis_url"]))
    row.update({"zavis_lat": detail["lat"], "zavis_lon": detail["lon"],
                "zavis_email": detail["email"],
                "zavis_maps_url": (
                    f'https://www.google.com/maps?q={detail["lat"]},{detail["lon"]}'
                    if detail["lat"] and detail["lon"] else "")})
    return row


def main() -> int:
    """Enrich the existing registry-to-Zavis crosswalk in place."""
    path = ROOT / "sources/csv/zavis-provider-matches.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fields = list(rows[0]) + ["zavis_lat", "zavis_lon", "zavis_email", "zavis_maps_url"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(enrich, rows))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Enriched {sum(bool(row.get('zavis_lat')) for row in rows)} providers with coordinates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
