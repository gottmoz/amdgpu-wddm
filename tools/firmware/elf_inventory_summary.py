"""Summarize validated ELF metadata without opening firmware binaries.

Malformed summary rows and counters are rejected with explicit ValueError
messages before any aggregation is attempted. No firmware bytes are read.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys


SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED_FIELDS = (
    "candidate",
    "sha256",
    "source_container",
    "architecture",
    "elf_type",
    "bounds_valid",
    "ghidra_functions",
    "validated_executable_bytes",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _validate_row(row, index):
    if not isinstance(row, dict):
        raise ValueError(f"inventory row {index} must be an object, got {type(row).__name__}")

    missing = [field for field in REQUIRED_FIELDS if field not in row]
    if missing:
        raise ValueError(f"inventory row {index} is missing required field(s): {', '.join(missing)}")

    candidate = row["candidate"]
    _require(isinstance(candidate, str) and candidate.strip(),
             f"inventory row {index} field 'candidate' must be a non-empty string")

    digest = row["sha256"]
    if digest is None:
        raise ValueError(f"inventory row {index} field 'sha256' must be a 64-character hex string, got None")
    if not isinstance(digest, str) or not SHA256_RE.match(digest):
        raise ValueError(
            f"inventory row {index} field 'sha256' must be a 64-character hex string, got {digest!r}"
        )

    for field in ("source_container", "architecture", "elf_type"):
        value = row[field]
        _require(isinstance(value, str) and value.strip(),
                f"inventory row {index} field {field!r} must be a non-empty string, got {value!r}")

    bounds = row["bounds_valid"]
    if not isinstance(bounds, bool):
        raise ValueError(
            f"inventory row {index} field 'bounds_valid' must be a boolean, got {bounds!r}"
        )

    functions = row["ghidra_functions"]
    if isinstance(functions, bool) or not isinstance(functions, int):
        raise ValueError(
            f"inventory row {index} field 'ghidra_functions' must be an integer, got {functions!r}"
        )
    if functions < 0:
        raise ValueError(
            f"inventory row {index} field 'ghidra_functions' must be >= 0, got {functions}"
        )

    size = row["validated_executable_bytes"]
    if isinstance(size, bool) or not isinstance(size, int):
        raise ValueError(
            f"inventory row {index} field 'validated_executable_bytes' must be an integer, got {size!r}"
        )
    if size < 0:
        raise ValueError(
            f"inventory row {index} field 'validated_executable_bytes' must be >= 0, got {size}"
        )

    return row


def _validate_rows(rows):
    if not isinstance(rows, list):
        raise ValueError(f"inventory must be a JSON list, got {type(rows).__name__}")
    for index, row in enumerate(rows):
        _validate_row(row, index)
    return rows


def summarize(rows, source_bytes=b""):
    rows = _validate_rows(rows)

    if not isinstance(source_bytes, (bytes, bytearray)):
        raise ValueError(f"source_inventory bytes must be bytes, got {type(source_bytes).__name__}")

    groups = defaultdict(list)
    hashes = defaultdict(list)
    for index, row in enumerate(rows):
        groups[row["source_container"]].append(row)
        hashes[row["sha256"].lower()].append(row["candidate"])

    group_report = {}
    for source, items in sorted(groups.items()):
        functions = [row["ghidra_functions"] for row in items]
        group_report[source] = {
            "candidate_count": len(items),
            "architectures": dict(sorted(Counter(row["architecture"] for row in items).items())),
            "elf_types": dict(sorted(Counter(row["elf_type"] for row in items).items())),
            "bounds_valid_count": sum(row["bounds_valid"] for row in items),
            "bounds_invalid_count": sum(not row["bounds_valid"] for row in items),
            "ghidra_zero_function_count": sum(value == 0 for value in functions),
            "ghidra_positive_function_count": sum(value > 0 for value in functions),
            "ghidra_function_total": sum(functions),
            "validated_executable_bytes": sum(row["validated_executable_bytes"] for row in items),
            "distinct_candidate_hash_count": len({row["sha256"].lower() for row in items}),
        }

    duplicate_hashes = [
        {"sha256": digest, "candidates": sorted(candidates)}
        for digest, candidates in sorted(hashes.items()) if len(candidates) > 1
    ]

    total_functions = sum(row["ghidra_functions"] for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_inventory_sha256": hashlib.sha256(source_bytes).hexdigest() if source_bytes else None,
        "candidate_count": len(rows),
        "bounds_valid_count": sum(row["bounds_valid"] for row in rows),
        "bounds_invalid_count": sum(not row["bounds_valid"] for row in rows),
        "ghidra_zero_function_count": sum(row["ghidra_functions"] == 0 for row in rows),
        "ghidra_positive_function_count": sum(row["ghidra_functions"] > 0 for row in rows),
        "ghidra_function_total": total_functions,
        "distinct_candidate_hash_count": len(hashes),
        "duplicate_candidate_hashes": duplicate_hashes,
        "by_source_container": group_report,
        "limitations": [
            "Function counts are reported Ghidra metadata and do not establish analysis completeness.",
            "Valid parser bounds do not establish component identity or executable behavior.",
            "This report reads the JSON inventory only and does not open firmware bytes.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    raw = args.inventory.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"inventory {args.inventory} is not valid JSON: {exc}") from exc
    report = summarize(payload, raw)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
