#!/usr/bin/env python3
"""Extract canonical UAE facility records from Zavis public pages."""

import argparse
import csv
import json
import re
import time
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

SITEMAP_URL = "https://www.zavis.ai/sitemap.xml"
BASE_URL = "https://www.zavis.ai"
FIELDS = ("name", "city", "description", "employees", "url")


def fetch(url: str, attempts: int = 4) -> str:
    """Fetch one public page with a descriptive user agent."""
    request = Request(url, headers={"User-Agent": "Insurance-Network-Map/1.0"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def facility_urls(sitemap: str) -> list[str]:
    """Return English canonical facility URLs, excluding specialty duplicates."""
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    return sorted({url for url in urls if "/professionals/facility/" in url
                   and url.rstrip("/").count("/") == 5})


def parse_medical_business(html: str) -> dict[str, str]:
    """Extract the MedicalBusiness JSON-LD record from a detail page."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for block in blocks:
        try:
            value = json.loads(unescape(block))
        except json.JSONDecodeError:
            continue
        if value.get("@type") != "MedicalBusiness":
            continue
        city = value.get("areaServed", {}).get("name", "")
        employees = value.get("numberOfEmployees", {}).get("value", "")
        return {"name": value.get("name", ""), "city": city,
                "description": value.get("description", ""),
                "employees": str(employees), "url": value.get("url", "")}
    return {field: "" for field in FIELDS}


def extract(url: str) -> dict[str, str]:
    """Fetch and parse one facility page, retaining its source URL."""
    try:
        record = parse_medical_business(fetch(url))
    except (HTTPError, URLError) as error:
        print(f"  failed: {url} ({error})")
        record = {field: "" for field in FIELDS}
    record["url"] = record["url"] or url
    return record


def main() -> int:
    """Extract facilities listed in the live Zavis sitemap to CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("sources/csv/zavis-facilities.csv"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    urls = facility_urls(fetch(SITEMAP_URL))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(extract, urls))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(record for record in records if record["name"])
    print(f"Extracted {sum(bool(record['name']) for record in records)} facilities from {len(urls)} URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
