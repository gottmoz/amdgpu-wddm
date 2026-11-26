"""Validator for exported Ghidra JSON metadata (BC-250 tooling).

The validator reads only JSON metadata text/objects. It never opens firmware
bytes; all fixtures used by the tests are synthetic.

Reported aggregates:
  * architecture counts (per architecture, and per source container)
  * block counts (parser-bounds blocks: valid / invalid / total)
  * function counts (zero-function candidates, positive-function candidates,
    total reported Ghidra functions)

Any missing required field, wrong type, negative count, or internally
inconsistent counter raises ValueError with a stable message.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Mapping, Tuple

SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TOP_LEVEL: Tuple[str, ...] = (
    "schema_version",
    "source_inventory_sha256",
    "candidate_count",
    "bounds_valid_count",
    "bounds_invalid_count",
    "ghidra_zero_function_count",
    "ghidra_positive_function_count",
    "ghidra_function_total",
    "distinct_candidate_hash_count",
    "duplicate_candidate_hashes",
    "by_source_container",
    "limitations",
)

REQUIRED_CONTAINER: Tuple[str, ...] = (
    "candidate_count",
    "architectures",
    "elf_types",
    "bounds_valid_count",
    "bounds_invalid_count",
    "ghidra_zero_function_count",
    "ghidra_positive_function_count",
    "ghidra_function_total",
    "validated_executable_bytes",
    "distinct_candidate_hash_count",
)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require(payload: Mapping[str, Any], fields: Tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"{label} is missing required field(s): {', '.join(missing)}")


def _count(payload: Mapping[str, Any], field: str, label: str) -> int:
    value = payload[field]
    if not _is_count(value):
        raise ValueError(f"{label} field {field!r} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{label} field {field!r} must be a non-negative integer")
    return value


def _count_map(payload: Mapping[str, Any], field: str, label: str) -> Dict[str, int]:
    value = payload[field]
    if not isinstance(value, dict):
        raise ValueError(f"{label} field {field!r} must be a JSON object")
    result: Dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} field {field!r} keys must be non-empty strings")
        if not _is_count(raw) or raw < 0:
            raise ValueError(
                f"{label} field {field!r} value for {key!r} must be a non-negative integer"
            )
        result[key] = raw
    return result


def validate_metadata(payload: Any) -> Dict[str, Any]:
    """Validate one exported Ghidra metadata document and return its report."""
    if not isinstance(payload, dict):
        raise ValueError("metadata root must be a JSON object")

    _require(payload, REQUIRED_TOP_LEVEL, "metadata root")

    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {payload['schema_version']!r}")

    sha = payload["source_inventory_sha256"]
    if not isinstance(sha, str) or not SHA256_RE.match(sha):
        raise ValueError("source_inventory_sha256 must be a lowercase 64-char hex digest")

    limitations = payload["limitations"]
    if not isinstance(limitations, list) or not all(isinstance(x, str) for x in limitations):
        raise ValueError("limitations must be a list of strings")

    duplicates = payload["duplicate_candidate_hashes"]
    if not isinstance(duplicates, list):
        raise ValueError("duplicate_candidate_hashes must be a JSON array")

    containers = payload["by_source_container"]
    if not isinstance(containers, dict):
        raise ValueError("by_source_container must be a JSON object")

    arch_counts: Dict[str, int] = {}
    elf_counts: Dict[str, int] = {}
    per_container_arch: Dict[str, Dict[str, int]] = {}
    blocks_valid = blocks_invalid = 0
    zero_functions = positive_functions = function_total = 0
    candidates = distinct_hashes = executable_bytes = 0

    for name, container in containers.items():
        if not isinstance(name, str) or not name:
            raise ValueError("container name must be a non-empty string")
        if not isinstance(container, dict):
            raise ValueError(f"container {name!r} must be a JSON object")

        _require(container, REQUIRED_CONTAINER, f"container {name!r}")

        label = f"container {name!r}"
        count = _count(container, "candidate_count", label)
        valid = _count(container, "bounds_valid_count", label)
        invalid = _count(container, "bounds_invalid_count", label)
        zero = _count(container, "ghidra_zero_function_count", label)
        positive = _count(container, "ghidra_positive_function_count", label)
        total = _count(container, "ghidra_function_total", label)
        byte_count = _count(container, "validated_executable_bytes", label)
        distinct = _count(container, "distinct_candidate_hash_count", label)

        arch = _count_map(container, "architectures", label)
        elf = _count_map(container, "elf_types", label)

        if valid + invalid != count:
            raise ValueError(
                f"{label}: bounds_valid_count + bounds_invalid_count must equal candidate_count"
            )
        if zero + positive != total:
            raise ValueError(
                f"{label}: ghidra_zero_function_count + ghidra_positive_function_count "
                "must equal ghidra_function_total"
            )
        if sum(arch.values()) != count:
            raise ValueError(f"{label}: architectures counts must sum to candidate_count")
        if sum(elf.values()) != count:
            raise ValueError(f"{label}: elf_types counts must sum to candidate_count")
        if distinct > count:
            raise ValueError(
                f"{label}: distinct_candidate_hash_count cannot exceed candidate_count"
            )

        blocks_valid += valid
        blocks_invalid += invalid
        zero_functions += zero
        positive_functions += positive
        function_total += total
        candidates += count
        distinct_hashes += distinct
        executable_bytes += byte_count

        for key, value in arch.items():
            arch_counts[key] = arch_counts.get(key, 0) + value
        for key, value in elf.items():
            elf_counts[key] = elf_counts.get(key, 0) + value
        per_container_arch[name] = dict(sorted(arch.items()))

    declared = {
        "candidate_count": _count(payload, "candidate_count", "metadata root"),
        "bounds_valid_count": _count(payload, "bounds_valid_count", "metadata root"),
        "bounds_invalid_count": _count(payload, "bounds_invalid_count", "metadata root"),
        "ghidra_zero_function_count": _count(
            payload, "ghidra_zero_function_count", "metadata root"
        ),
        "ghidra_positive_function_count": _count(
            payload, "ghidra_positive_function_count", "metadata root"
        ),
        "ghidra_function_total": _count(payload, "ghidra_function_total", "metadata root"),
        "distinct_candidate_hash_count": _count(
            payload, "distinct_candidate_hash_count", "metadata root"
        ),
    }

    computed = {
        "candidate_count": candidates,
        "bounds_valid_count": blocks_valid,
        "bounds_invalid_count": blocks_invalid,
        "ghidra_zero_function_count": zero_functions,
        "ghidra_positive_function_count": positive_functions,
        "ghidra_function_total": function_total,
        "distinct_candidate_hash_count": distinct_hashes,
    }
    for field, expected in computed.items():
        if declared[field] != expected:
            raise ValueError(
                f"metadata root field {field!r} = {declared[field]} does not match "
                f"container sum {expected}"
            )

    if len(duplicates) != declared["candidate_count"] - declared["distinct_candidate_hash_count"]:
        raise ValueError(
            "duplicate_candidate_hashes length must equal candidate_count - "
            "distinct_candidate_hash_count"
        )

    return {
        "schema": "ghidra_json_metadata/1",
        "ok": True,
        "source_inventory_sha256": sha,
        "container_count": len(containers),
        "candidate_count": declared["candidate_count"],
        "architecture_counts": dict(sorted(arch_counts.items())),
        "architecture_counts_by_container": per_container_arch,
        "elf_type_counts": dict(sorted(elf_counts.items())),
        "block_counts": {
            "valid": declared["bounds_valid_count"],
            "invalid": declared["bounds_invalid_count"],
            "total": declared["bounds_valid_count"] + declared["bounds_invalid_count"],
        },
        "function_counts": {
            "zero_function_candidates": declared["ghidra_zero_function_count"],
            "positive_function_candidates": declared["ghidra_positive_function_count"],
            "total": declared["ghidra_function_total"],
        },
        "distinct_candidate_hash_count": declared["distinct_candidate_hash_count"],
        "duplicate_candidate_hash_count": len(duplicates),
        "validated_executable_bytes": executable_bytes,
        "limitations": list(limitations),
    }


def validate_json(source: Any) -> Dict[str, Any]:
    """Parse JSON text/bytes, then validate it as Ghidra metadata."""
    if isinstance(source, (bytes, bytearray)):
        source = source.decode("utf-8")
    if not isinstance(source, str):
        raise ValueError("metadata source must be a JSON string or bytes")
    try:
        payload = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError(f"metadata is not valid JSON: {exc}") from exc
    return validate_metadata(payload)


def validate_file(path: str) -> Dict[str, Any]:
    """Validate a metadata file path (JSON text only)."""
    with open(path, "r", encoding="utf-8") as handle:
        return validate_json(handle.read())


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate exported Ghidra JSON metadata.")
    parser.add_argument("path", help="path to a Ghidra metadata JSON file")
    args = parser.parse_args()
    try:
        report = validate_file(args.path)
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
