#!/usr/bin/env python3
"""Convert Takafol Emarat XLSX network lists to a tracked CSV catalog.

The importer uses only Python's standard library because the source files are
downloaded manually from public insurer pages and may have different layouts.
It finds the header row by column names, keeps the source network identity, and
exports UAE providers in one stable schema for the assignment engine.
"""

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
EMIRATE_CODES = {
    "ABU DHABI": "AUH",
    "ABU DHABI CITY": "AUH",
    "AUH": "AUH",
    "DUBAI": "DXB",
    "DXB": "DXB",
    "SHARJAH": "SHJ",
    "SHJ": "SHJ",
    "AJMAN": "AJM",
    "AJM": "AJM",
    "FUJAIRAH": "FUJ",
    "FUJ": "FUJ",
    "RAS AL KHAIMAH": "RAK",
    "RAS AL KHAIMAH CITY": "RAK",
    "RAK": "RAK",
    "UMM AL QUWAIN": "UMQ",
    "UMM AL QAIWAIN": "UMQ",
    "UMQ": "UMQ",
    "AL AIN": "ALAIN",
    "ALAIN": "ALAIN",
}
OUTPUT_FIELDS = (
    "NETWORK_ID",
    "NETWORK_NAME",
    "TPA",
    "PROVIDER NAME",
    "EMIRATE",
    "PROVIDER TYPE",
    "AREA",
    "ADDRESS",
    "TELEPHONE",
    "lat",
    "lon",
)


def normalize_header(value: str) -> str:
    """Return a comparison key for varied workbook header spellings."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def normalize_emirate(value: str) -> str:
    """Map a workbook emirate label to the project's short code.

    Country names intentionally return an empty string because they are not
    sufficient to identify an emirate.
    """
    key = re.sub(r"\s+", " ", (value or "").strip().upper())
    key = re.sub(r"\s*\([^)]*\)$", "", key).strip()
    return EMIRATE_CODES.get(key, "")


def network_id_for(filename: str) -> str:
    """Create a stable slug used by plans and assignment records."""
    stem = Path(filename).stem.lower()
    return re.sub(r"[^a-z0-9]+", "-", stem).strip("-")


def network_name_for(filename: str) -> str:
    """Return a readable network name without the workbook extension."""
    return re.sub(r"\s+", " ", Path(filename).stem.replace("_", " ")).strip()


def tpa_for(filename: str) -> str:
    """Extract the administrator prefix used in a Takafol filename."""
    prefix = re.split(r"\s*-\s*", Path(filename).stem, maxsplit=1)[0]
    return prefix.split()[0].upper()


def column_number(reference: str) -> int:
    """Convert an XLSX cell reference to a zero-based column number."""
    letters = re.match(r"[A-Z]+", reference.upper())
    if not letters:
        return -1
    number = 0
    for character in letters.group(0):
        number = number * 26 + ord(character) - ord("A") + 1
    return number - 1


def shared_strings(book: ZipFile) -> list[str]:
    """Read shared strings, including rich-text runs, from an XLSX archive."""
    try:
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
            for item in root.findall(f"{{{MAIN_NS}}}si")]


def first_sheet_path(book: ZipFile) -> str | None:
    """Resolve the first workbook sheet without depending on its name."""
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    relationships = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    sheet = workbook.find(f"{{{MAIN_NS}}}sheets/{{{MAIN_NS}}}sheet")
    if sheet is None:
        return None
    target = targets.get(sheet.attrib.get(f"{{{REL_NS}}}id", ""))
    if not target:
        return None
    return target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"


def sheet_rows(book: ZipFile) -> list[dict[int, str]]:
    """Read worksheet cells while preserving sparse column positions."""
    path = first_sheet_path(book)
    if not path:
        return []
    strings = shared_strings(book)
    root = ET.fromstring(book.read(path))
    rows: list[dict[int, str]] = []
    for row in root.iter(f"{{{MAIN_NS}}}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            column = column_number(cell.attrib.get("r", ""))
            value = cell.find(f"{{{MAIN_NS}}}v")
            if value is None:
                value = cell.find(f"{{{MAIN_NS}}}is")
            if value is None:
                continue
            if cell.attrib.get("t") == "s":
                try:
                    text = strings[int(value.text or "0")]
                except (ValueError, IndexError):
                    text = ""
            elif cell.attrib.get("t") == "inlineStr":
                text = "".join(node.text or "" for node in value.iter(f"{{{MAIN_NS}}}t"))
            else:
                text = "".join(node.text or "" for node in value.iter(f"{{{MAIN_NS}}}t"))
                if not text:
                    text = value.text or ""
            values[column] = re.sub(r"\s+", " ", text).strip()
        rows.append(values)
    return rows


HEADER_ALIASES = {
    "provider": {"PROVIDERNAME", "PROVIDER", "NAME", "FACILITYNAME", "NAMEOFTHEPROVIDER"},
    "country": {"COUNTRY", "EMIRATESCOUNTRY", "COUNTRYNAME", "EMIRATES"},
    "emirate": {"EMIRATE", "REGION", "CITY", "EMIRATECITY"},
    "type": {"PROVIDERTYPE", "TYPE", "FACILITYTYPE"},
    "area": {"AREA", "SUBREGION", "DISTRICT"},
    "address": {"ADDRESS", "BUILDINGADDRESS", "LOCATION"},
    "phone": {"TELEPHONE", "PHONE", "TEL", "MOBILE"},
    "lat": {"LATITUDE", "LAT"},
    "lon": {"LONGITUDE", "LON", "LONG"},
}


def header_mapping(rows: list[dict[int, str]]) -> tuple[int, dict[str, int]] | None:
    """Find the first row containing a provider and location identity."""
    for row_number, row in enumerate(rows):
        normalized = {normalize_header(value): column for column, value in row.items()}
        mapping: dict[str, int] = {}
        for field, aliases in HEADER_ALIASES.items():
            column = next((normalized[alias] for alias in aliases if alias in normalized), None)
            if column is not None:
                mapping[field] = column
        if "provider" in mapping and ("emirate" in mapping or "country" in mapping):
            return row_number, mapping
    return None


def row_value(row: dict[int, str], mapping: dict[str, int], field: str) -> str:
    """Read a mapped source field or return an empty value."""
    return row.get(mapping.get(field, -1), "").strip()


def is_uae(country: str, emirate: str) -> bool:
    """Return whether a source row identifies a UAE provider."""
    country_key = re.sub(r"[^A-Z]", "", (country or "").upper())
    return (not country and bool(emirate)) or country_key in {
        "UAE", "UNITEDARABEMIRATES", "EMIRATES"
    }


def import_workbook(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Extract UAE provider rows and metadata from one workbook."""
    metadata = {
        "NETWORK_ID": network_id_for(path.name),
        "NETWORK_NAME": network_name_for(path.name),
        "TPA": tpa_for(path.name),
        "SOURCE_FILE": path.name,
    }
    with ZipFile(path) as book:
        mapping_result = header_mapping(sheet_rows(book))
        if mapping_result is None:
            return metadata, []
        header_row, mapping = mapping_result
        rows = sheet_rows(book)[header_row + 1:]
    records: list[dict[str, str]] = []
    for row in rows:
        provider = row_value(row, mapping, "provider")
        explicit_emirate = row_value(row, mapping, "emirate")
        country = row_value(row, mapping, "country")
        emirate = normalize_emirate(explicit_emirate)
        if not emirate and not explicit_emirate:
            emirate = normalize_emirate(country)
            country = "" if emirate else country
        if not provider or not is_uae(country, emirate) or not emirate:
            continue
        records.append({
            "NETWORK_ID": metadata["NETWORK_ID"],
            "NETWORK_NAME": metadata["NETWORK_NAME"],
            "TPA": metadata["TPA"],
            "PROVIDER NAME": provider,
            "EMIRATE": emirate,
            "PROVIDER TYPE": row_value(row, mapping, "type").upper(),
            "AREA": row_value(row, mapping, "area"),
            "ADDRESS": row_value(row, mapping, "address"),
            "TELEPHONE": row_value(row, mapping, "phone"),
            "lat": row_value(row, mapping, "lat"),
            "lon": row_value(row, mapping, "lon"),
        })
    return metadata, records


def write_outputs(input_dir: Path, members_path: Path, catalog_path: Path) -> tuple[int, int]:
    """Import all XLSX files and write the member and catalog CSV files."""
    files = sorted(input_dir.glob("*.xlsx"), key=lambda path: path.name.casefold())
    members: list[dict[str, str]] = []
    catalog: list[dict[str, str]] = []
    for path in files:
        metadata, records = import_workbook(path)
        members.extend(records)
        catalog.append({**metadata, "RECORDS": str(len(records))})
        print(f"  {path.name}: {len(records)} UAE providers")
    members_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with members_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(members)
    with catalog_path.open("w", newline="", encoding="utf-8") as stream:
        fields = ("NETWORK_ID", "NETWORK_NAME", "TPA", "SOURCE_FILE", "RECORDS")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(catalog)
    return len(files), len(members)


def main() -> int:
    """Run the importer from a download directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--members", type=Path, default=Path("sources/csv/takafol-network-members.csv"))
    parser.add_argument("--catalog", type=Path, default=Path("sources/csv/takafol-network-catalog.csv"))
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        print(f"Input directory does not exist: {args.input_dir}", file=sys.stderr)
        return 2
    files, records = write_outputs(args.input_dir, args.members, args.catalog)
    print(f"Imported {records} UAE providers from {files} workbooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
