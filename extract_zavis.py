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
DIRECTORY_FIELDS = ("id", "name", "city", "category", "address", "phone",
                    "rating", "reviews", "insurance", "languages", "url")


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


def safe_fetch(url: str) -> str:
    """Fetch a page while allowing a large crawl to continue past 503s."""
    try:
        return fetch(url)
    except (HTTPError, URLError):
        print(f"  failed: {url}")
        return ""


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


def parse_provider_detail(html: str) -> dict[str, str]:
    """Extract coordinates and contact fields from a Zavis provider page."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    for block in blocks:
        try:
            value = json.loads(unescape(block))
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or not value.get("geo"):
            continue
        geo = value["geo"]
        return {"lat": str(geo.get("latitude", "")),
                "lon": str(geo.get("longitude", "")),
                "phone": value.get("telephone", ""),
                "email": value.get("email", "")}
    return {"lat": "", "lon": "", "phone": "", "email": ""}


def _json_text(value: str) -> str:
    """Decode one escaped value from a Next.js streamed payload."""
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def parse_directory_providers(html: str, source_url: str = "") -> list[dict[str, str]]:
    """Extract provider cards rendered in one paginated directory page."""
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    ):
        try:
            value = json.loads(unescape(block))
        except json.JSONDecodeError:
            continue
        if value.get("@type") != "ItemList":
            continue
        category = source_url.split("/")[-1].split("?")[0]
        records = []
        for entry in value.get("itemListElement", []):
            provider = entry.get("item", {})
            address = provider.get("address", {})
            provider_url = provider.get("url", entry.get("url", ""))
            provider_id = provider.get("@id", provider_url).split("#")[0].rstrip("/").split("/")[-1]
            records.append({
                "id": provider_id, "name": provider.get("name", ""),
                "city": address.get("addressLocality", ""), "category": category,
                "address": address.get("streetAddress", ""),
                "phone": provider.get("telephone", ""), "rating": "",
                "reviews": "", "insurance": "", "languages": "",
                "url": provider_url,
            })
        if records:
            return records
    pattern = re.compile(
        r'\\"id\\":\\"(dha_[^\\"]+)\\",\\"name\\":\\"([^\\"]*)\\",'
        r'\\"slug\\":\\"([^\\"]*)\\".*?\\"citySlug\\":\\"([^\\"]*)\\",'
        r'\\"categorySlug\\":\\"([^\\"]*)\\".*?\\"address\\":\\"([^\\"]*)\\"'
        r'.*?\\"googleRating\\":\\"([^\\"]*)\\",\\"googleReviewCount\\":([0-9]+)'
        r'.*?\\"insurance\\":\[(.*?)\],\\"languages\\":\[(.*?)\]', re.DOTALL)
    records = []
    for match in pattern.finditer(html):
        values = [_json_text(value) for value in match.groups()]
        insurance = ", ".join(re.findall(r'\\"([^\\"]*)\\"', match.group(9)))
        languages = ", ".join(re.findall(r'\\"([^\\"]*)\\"', match.group(10)))
        records.append(dict(zip(DIRECTORY_FIELDS, [
            values[0], values[1], values[3], values[4], values[5],
            "", values[6], values[7], insurance, languages, "",
        ])))
        records[-1]["url"] = f'{BASE_URL}/directory/{values[3]}/{values[4]}/{values[2]}'
    return records


def directory_categories(sitemap: str) -> list[str]:
    """Return English UAE city/category pages from the public sitemap."""
    cities = {"dubai", "abu-dhabi", "sharjah", "al-ain", "ajman",
              "ras-al-khaimah", "fujairah", "umm-al-quwain"}
    categories = {"hospitals", "clinics", "dental", "dermatology", "ophthalmology",
                  "cardiology", "orthopedics", "mental-health", "pediatrics", "ob-gyn",
                  "ent", "fertility-ivf", "physiotherapy", "nutrition-dietetics",
                  "pharmacy", "labs-diagnostics", "radiology-imaging", "home-healthcare",
                  "alternative-medicine", "cosmetic-plastic", "neurology", "urology",
                  "gastroenterology", "oncology", "emergency-care", "wellness-spas",
                  "nephrology", "medical-equipment"}
    return sorted({url for url in re.findall(r"<loc>(.*?)</loc>", sitemap)
                   if "/ar/" not in url and "/directory/" in url
                   and len(url.split("/")) == 6
                   and "?" not in url and url.split("/")[-2] in cities
                   and url.split("/")[-1] in categories})


def directory_page_count(html: str) -> int:
    """Read the server-rendered page count for one directory category."""
    match = re.search(r'\\"currentPage\\":1,\\"totalPages\\":([0-9]+)', html)
    return int(match.group(1)) if match else 1


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
    parser.add_argument("--output", type=Path, default=Path("sources/csv/zavis-providers.csv"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    categories = directory_categories(fetch(SITEMAP_URL))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        first_pages = dict(zip(categories, pool.map(safe_fetch, categories)))
    page_urls = [f"{url}?page={page}" for url, html in first_pages.items()
                 for page in range(2, directory_page_count(html) + 1)]
    records = [record for url, html in first_pages.items()
               for record in parse_directory_providers(html, url)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for url, html in zip(page_urls, pool.map(safe_fetch, page_urls)):
            records.extend(parse_directory_providers(html, url))
    unique = {record["id"]: record for record in records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=DIRECTORY_FIELDS)
        writer.writeheader()
        writer.writerows(unique.values())
    print(f"Extracted {len(unique)} providers from {len(categories)} categories and {len(page_urls)} additional pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
