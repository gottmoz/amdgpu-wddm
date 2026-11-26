"""Summarize validated ELF metadata without opening firmware binaries."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys


SCHEMA_VERSION = 1


def summarize(rows, source_bytes=b""):
    if not isinstance(rows, list):
        raise ValueError("inventory must be a JSON list")
    groups = defaultdict(list)
    hashes = defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"inventory row {index} must be an object")
        source = str(row.get("source_container", "unknown"))
        groups[source].append(row)
        digest = row.get("sha256")
        if isinstance(digest, str) and digest:
            hashes[digest.lower()].append(row.get("candidate", f"row-{index}"))

    group_report = {}
    for source, items in sorted(groups.items()):
        functions = [row.get("ghidra_functions") for row in items]
        group_report[source] = {
            "candidate_count": len(items),
            "architectures": dict(sorted(Counter(row.get("architecture", "unknown") for row in items).items())),
            "elf_types": dict(sorted(Counter(row.get("elf_type", "unknown") for row in items).items())),
            "bounds_valid_count": sum(row.get("bounds_valid") is True for row in items),
            "bounds_invalid_count": sum(row.get("bounds_valid") is False for row in items),
            "ghidra_zero_function_count": sum(value == 0 for value in functions),
            "ghidra_positive_function_count": sum(isinstance(value, int) and value > 0 for value in functions),
            "ghidra_function_total": sum(value for value in functions if isinstance(value, int) and value >= 0),
            "validated_executable_bytes": sum(row.get("validated_executable_bytes", 0) or 0 for row in items),
            "distinct_candidate_hash_count": len({row.get("sha256", "").lower() for row in items if row.get("sha256")}),
        }

    duplicate_hashes = [
        {"sha256": digest, "candidates": sorted(candidates)}
        for digest, candidates in sorted(hashes.items()) if len(candidates) > 1
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source_inventory_sha256": hashlib.sha256(source_bytes).hexdigest() if source_bytes else None,
        "candidate_count": len(rows),
        "bounds_valid_count": sum(row.get("bounds_valid") is True for row in rows),
        "bounds_invalid_count": sum(row.get("bounds_valid") is False for row in rows),
        "ghidra_zero_function_count": sum(row.get("ghidra_functions") == 0 for row in rows),
        "ghidra_positive_function_count": sum(isinstance(row.get("ghidra_functions"), int) and row["ghidra_functions"] > 0 for row in rows),
        "ghidra_function_total": sum(row["ghidra_functions"] for row in rows if isinstance(row.get("ghidra_functions"), int) and row["ghidra_functions"] >= 0),
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
    report = summarize(json.loads(raw.decode("utf-8-sig")), raw)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
