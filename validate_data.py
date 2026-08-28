"""Validate the insurance plan data files and optional network assignments."""

import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PLAN_INDEX = ROOT / "data" / "plans.json"
ASSIGNMENTS = ROOT / "data" / "network-assignments.json"
EMIRATES = {"AJM", "AUH", "DXB", "FUJ", "RAK", "SHJ", "UMQ", "ALAIN"}
PROVIDER_TYPES = {
    "CLINIC",
    "HOSPITAL",
    "PHARMACY",
    "DENTAL",
    "DIAGNOSTIC CENTRE",
    "DAYCARE",
}
PLAN_FIELDS = {"id", "name", "insurer", "coverage", "emirates", "file", "providers"}
PROVIDER_FIELDS = {
    "Index",
    "P",
    "PROVIDER TYPE",
    "PROVIDER NAME",
    "AREA",
    "ADDRESS",
    "TELEPHONE",
    "lat",
    "lon",
    "confidence",
    "formatted",
}
MIN_LATITUDE, MAX_LATITUDE = 22.0, 26.6
MIN_LONGITUDE, MAX_LONGITUDE = 51.0, 56.6


def load_json(path: Path) -> Any:
    """Load JSON and raise a readable validation error for malformed files."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"{path.relative_to(ROOT)} does not exist") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path.relative_to(ROOT)}: {error}") from error


def required_fields(record: Any, fields: set[str], label: str, errors: list[str]) -> None:
    """Add an error when a JSON object does not contain required fields."""
    if not isinstance(record, dict):
        errors.append(f"{label} must be an object")
        return
    missing = sorted(fields - record.keys())
    if missing:
        errors.append(f"{label} missing fields: {', '.join(missing)}")


def validate_provider(provider: Any, position: int, errors: list[str]) -> None:
    """Validate one provider record against the documented data contract."""
    label = f"provider {position}"
    required_fields(provider, PROVIDER_FIELDS, label, errors)
    if not isinstance(provider, dict):
        return
    if provider.get("P") not in EMIRATES:
        errors.append(f"{label} has invalid emirate code {provider.get('P')!r}")
    if provider.get("PROVIDER TYPE") not in PROVIDER_TYPES:
        errors.append(f"{label} has invalid provider type {provider.get('PROVIDER TYPE')!r}")
    for coordinate, lower, upper in (
        ("lat", MIN_LATITUDE, MAX_LATITUDE),
        ("lon", MIN_LONGITUDE, MAX_LONGITUDE),
    ):
        try:
            value = float(provider.get(coordinate))
        except (TypeError, ValueError):
            errors.append(f"{label} has non-numeric {coordinate}")
            continue
        if not math.isfinite(value) or not lower <= value <= upper:
            errors.append(f"{label} has out-of-bounds {coordinate}: {value}")


def validate_plan(plan: Any, errors: list[str]) -> tuple[str | None, set[int]]:
    """Validate one plan metadata record and its referenced provider file."""
    if not isinstance(plan, dict):
        errors.append("plan entry must be an object")
        return None, set()
    plan_id = plan.get("id")
    label = f"plan {plan_id!r}"
    required_fields(plan, PLAN_FIELDS, label, errors)
    if not isinstance(plan_id, str) or not isinstance(plan.get("file"), str):
        return plan_id if isinstance(plan_id, str) else None, set()
    if not isinstance(plan.get("emirates"), list) or any(code not in EMIRATES for code in plan["emirates"]):
        errors.append(f"{label} has invalid emirates")
    try:
        providers = load_json(ROOT / plan["file"])
    except ValueError as error:
        errors.append(str(error))
        return plan_id, set()
    if not isinstance(providers, list):
        errors.append(f"{label} file must contain a provider list")
        return plan_id, set()
    if plan.get("providers") != len(providers):
        errors.append(f"{label} provider count is {plan.get('providers')}, file has {len(providers)}")
    indexes: set[int] = set()
    for position, provider in enumerate(providers):
        validate_provider(provider, position, errors)
        if isinstance(provider, dict) and isinstance(provider.get("Index"), int) and not isinstance(provider.get("Index"), bool):
            indexes.add(provider["Index"])
    return plan_id, indexes


def validate_assignments(indexes_by_plan: dict[str, set[int]], errors: list[str]) -> None:
    """Check optional network assignment indexes against each plan's providers."""
    if not ASSIGNMENTS.exists():
        return
    try:
        data = load_json(ASSIGNMENTS)
    except ValueError as error:
        errors.append(str(error))
        return
    assignments = data.get("assignments") if isinstance(data, dict) else None
    if not isinstance(assignments, dict):
        errors.append("network assignments must contain an assignments object")
        return
    for plan_id, records in assignments.items():
        if plan_id not in indexes_by_plan or not isinstance(records, list):
            errors.append(f"network assignments has invalid plan {plan_id!r}")
            continue
        for position, record in enumerate(records):
            index = record.get("index") if isinstance(record, dict) else None
            if not isinstance(index, int) or isinstance(index, bool) or index not in indexes_by_plan[plan_id]:
                errors.append(f"assignment {plan_id}[{position}] references missing provider index {index!r}")


def main() -> int:
    """Validate all configured data and return a process exit status."""
    errors: list[str] = []
    try:
        plans = load_json(PLAN_INDEX)
    except ValueError as error:
        errors = [str(error)]
        plans = []
    if not isinstance(plans, list):
        errors.append("data/plans.json must contain a plan list")
        plans = []
    indexes_by_plan: dict[str, set[int]] = {}
    for plan in plans:
        plan_id, indexes = validate_plan(plan, errors)
        if plan_id is not None:
            indexes_by_plan[plan_id] = indexes
    validate_assignments(indexes_by_plan, errors)
    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Validation passed: {len(plans)} plans and {sum(len(indexes) for indexes in indexes_by_plan.values())} provider indexes checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
