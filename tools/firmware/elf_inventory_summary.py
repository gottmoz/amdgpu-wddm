"""Summarize validated ELF metadata without opening firmware binaries.

Malformed summary rows and counters are rejected with explicit ValueError
messages before any aggregation is attempted. No firmware bytes are read.
The Markdown renderer is deterministic: identical reports always produce
byte-identical output, and it never infers component identity.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys


SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
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

REPORT_FIELDS = (
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
REPORT_COUNT_FIELDS = (
    "candidate_count",
    "bounds_valid_count",
    "bounds_invalid_count",
    "ghidra_zero_function_count",
    "ghidra_positive_function_count",
    "ghidra_function_total",
    "distinct_candidate_hash_count",
)
GROUP_FIELDS = (
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
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
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
            "Container names, hashes and counters are metadata; no component identity is inferred.",
        ],
    }


def _validate_report(report):
    if not isinstance(report, dict):
        raise ValueError(f"report must be an object, got {type(report).__name__}")

    missing = [field for field in REPORT_FIELDS if field not in report]
    if missing:
        raise ValueError(f"report is missing required field(s): {', '.join(missing)}")

    for field in REPORT_COUNT_FIELDS:
        value = report[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"report field {field!r} must be a non-negative integer, got {value!r}")

    digest = report["source_inventory_sha256"]
    if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
        raise ValueError(f"report field 'source_inventory_sha256' must be a 64-character hex string or null")

    containers = report["by_source_container"]
    if not isinstance(containers, dict):
        raise ValueError(f"report field 'by_source_container' must be an object, got {type(containers).__name__}")

    for name, group in containers.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"source container name must be a non-empty string, got {name!r}")
        if not isinstance(group, dict):
            raise ValueError(f"container group {name!r} must be an object, got {type(group).__name__}")
        missing_group = [field for field in GROUP_FIELDS if field not in group]
        if missing_group:
            raise ValueError(f"container group {name!r} is missing field(s): {', '.join(missing_group)}")
        for field in GROUP_FIELDS:
            if field in ("architectures", "elf_types"):
                value = group[field]
                if not isinstance(value, dict):
                    raise ValueError(f"container group {name!r} field {field!r} must be an object")
                for key, count in value.items():
                    if not isinstance(key, str) or not key.strip():
                        raise ValueError(f"container group {name!r} field {field!r} has an invalid key {key!r}")
                    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                        raise ValueError(
                            f"container group {name!r} field {field!r} count for {key!r} must be a "
                            f"non-negative integer, got {count!r}"
                        )
            else:
                value = group[field]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(
                        f"container group {name!r} field {field!r} must be a non-negative integer, got {value!r}"
                    )

    limitations = report["limitations"]
    if not isinstance(limitations, list) or not limitations:
        raise ValueError(f"report field 'limitations' must be a non-empty list, got {limitations!r}")
    for item in limitations:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"report limitation entries must be non-empty strings, got {item!r}")

    duplicates = report["duplicate_candidate_hashes"]
    if not isinstance(duplicates, list):
        raise ValueError(f"report field 'duplicate_candidate_hashes' must be a list, got {duplicates!r}")
    for entry in duplicates:
        if not isinstance(entry, dict) or "sha256" not in entry or "candidates" not in entry:
            raise ValueError(f"duplicate hash entry must contain 'sha256' and 'candidates', got {entry!r}")
        if not isinstance(entry["sha256"], str) or not SHA256_RE.fullmatch(entry["sha256"]):
            raise ValueError(f"duplicate hash entry 'sha256' must be a 64-character hex string, got {entry['sha256']!r}")
        if not isinstance(entry["candidates"], list) or not all(isinstance(c, str) for c in entry["candidates"]):
            raise ValueError(f"duplicate hash entry 'candidates' must be a list of strings, got {entry['candidates']!r}")

    container_total = sum(group["candidate_count"] for group in containers.values())
    if container_total != report["candidate_count"]:
        raise ValueError(
            f"container candidate counts sum to {container_total} but candidate_count is {report['candidate_count']}"
        )
    if report["bounds_valid_count"] + report["bounds_invalid_count"] != report["candidate_count"]:
        raise ValueError("bounds_valid_count + bounds_invalid_count does not equal candidate_count")
    if report["distinct_candidate_hash_count"] > report["candidate_count"]:
        raise ValueError("distinct_candidate_hash_count cannot exceed candidate_count")


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report):
    """Render a summary report as deterministic, metadata-only Markdown."""
    _validate_report(report)

    lines = ["# PS5 ELF Inventory Summary", ""]
    lines.append("Deterministic rendering of validated ELF inventory metadata.")
    lines.append("No firmware bytes were read and no component identity is inferred.")
    lines.append("")

    digest = report["source_inventory_sha256"]
    lines.append(f"- Schema version: {report['schema_version']}")
    lines.append(f"- Source inventory SHA-256: {digest if digest else 'not recorded'}")
    lines.append("")

    lines.append("## Totals")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    for label, field in (
        ("Candidates", "candidate_count"),
        ("Bounds valid", "bounds_valid_count"),
        ("Bounds invalid", "bounds_invalid_count"),
        ("Ghidra zero-function candidates", "ghidra_zero_function_count"),
        ("Ghidra positive-function candidates", "ghidra_positive_function_count"),
        ("Ghidra function total", "ghidra_function_total"),
        ("Distinct candidate hashes", "distinct_candidate_hash_count"),
    ):
        lines.append(f"| {label} | {report[field]} |")
    lines.append(f"| Duplicate candidate hash entries | {len(report['duplicate_candidate_hashes'])} |")
    lines.append(f"| Source containers | {len(report['by_source_container'])} |")
    lines.append("")

    containers = sorted(report["by_source_container"].items())
    lines.append("## By source container")
    lines.append("")
    if not containers:
        lines.append("No containers in the inventory.")
        lines.append("")
    else:
        header = (
            "| Source container | Candidates | Distinct hashes | Bounds valid | Bounds invalid | "
            "Zero-function | Positive-function | Function total | Validated executable bytes |"
        )
        lines.append(header)
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name, group in containers:
            lines.append(
                f"| {_cell(name)} | {group['candidate_count']} | {group['distinct_candidate_hash_count']} | "
                f"{group['bounds_valid_count']} | {group['bounds_invalid_count']} | "
                f"{group['ghidra_zero_function_count']} | {group['ghidra_positive_function_count']} | "
                f"{group['ghidra_function_total']} | {group['validated_executable_bytes']} |"
            )
        lines.append("")

        lines.append("## Container metadata detail")
        lines.append("")
        for name, group in containers:
            lines.append(f"### {_cell(name)}")
            lines.append("")
            architectures = ", ".join(f"{key}={group['architectures'][key]}" for key in sorted(group["architectures"]))
            elf_types = ", ".join(f"{key}={group['elf_types'][key]}" for key in sorted(group["elf_types"]))
            lines.append(f"- Architectures: {architectures or 'none'}")
            lines.append(f"- ELF types: {elf_types or 'none'}")
            lines.append("")

    lines.append("## Duplicate candidate hashes")
    lines.append("")
    duplicates = report["duplicate_candidate_hashes"]
    if not duplicates:
        lines.append("None detected.")
    else:
        for entry in sorted(duplicates, key=lambda item: item["sha256"].lower()):
            candidates = ", ".join(_cell(candidate) for candidate in sorted(entry["candidates"]))
            lines.append(f"- `{entry['sha256'].lower()}`: {candidates}")
    lines.append("")

    lines.append("## Limitations (metadata only)")
    lines.append("")
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")

    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="render the summary as deterministic Markdown instead of JSON",
    )
    args = parser.parse_args(argv)

    raw = args.inventory.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"inventory {args.inventory} is not valid JSON: {exc}") from exc

    report = summarize(payload, raw)
    if args.markdown:
        rendered = render_markdown(report)
    else:
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
