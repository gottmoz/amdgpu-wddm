"""Deterministic JSON-only grouping of identical validated executable segment hashes.

Source limitation (documented): the declared source, PS5_ELF_INVENTORY_SUMMARY.json,
contains only aggregate counts (candidate_count, distinct_candidate_hash_count,
duplicate_candidate_hashes) and no per-segment hash records. This module therefore
accepts an explicit record list (or an inventory summary document) and groups hashes
deterministically; when no per-hash records exist it emits an empty group set plus the
source limitations rather than inventing hashes. No firmware bytes are read.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = "bc250-segment-hash-groups/1"

MISSING_REASONS = (
    "missing-hash-field",
    "null-hash",
    "empty-hash",
    "whitespace-only-hash",
    "non-string-hash",
)


def _normalize_hash(value: Any) -> Optional[str]:
    """Return a lowercase SHA-256 digest, or None when it is missing/invalid."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or not re.fullmatch(r"[0-9a-fA-F]{64}", text):
        return None
    return text.lower()


def _hash_reason(value: Any) -> str:
    if value is None:
        return "null-hash"
    if isinstance(value, bool) or not isinstance(value, str):
        return "non-string-hash"
    if not value.strip():
        return "empty-hash" if not value else "whitespace-only-hash"
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()):
        return "invalid-hash"
    return "invalid-hash"


def group_segment_hashes(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Group identical validated segment hashes across firmware versions.

    Records may carry: hash (or segment_hash), firmware_version (or version),
    container and validated=True. Only explicit validation and 64-character
    hexadecimal SHA-256 digests are grouped. Missing/invalid hashes and unvalidated
    records are reported separately and never grouped.
    """
    groups: Dict[str, Dict[str, Any]] = {}
    missing: List[Dict[str, Any]] = []
    unvalidated: List[Dict[str, Any]] = []
    record_count = 0

    for index, record in enumerate(records):
        record_count += 1
        if not isinstance(record, dict):
            missing.append({"index": index, "reason": "non-object-record"})
            continue

        raw_hash = record.get("hash", record.get("segment_hash"))
        normalized = _normalize_hash(raw_hash)
        if normalized is None:
            missing.append(
                {
                    "index": index,
                    "reason": _hash_reason(raw_hash) if "hash" in record or "segment_hash" in record
                    else "missing-hash-field",
                }
            )
            continue

        if record.get("validated") is not True:
            unvalidated.append({"index": index, "hash": normalized})
            continue

        version = record.get("firmware_version", record.get("version"))
        version = version.strip() if isinstance(version, str) and version.strip() else "unknown-version"
        container = record.get("container")
        container = container.strip() if isinstance(container, str) and container.strip() else "unknown-container"

        group = groups.setdefault(
            normalized,
            {"hash": normalized, "occurrences": 0, "firmware_versions": set(), "containers": set()},
        )
        group["occurrences"] += 1
        group["firmware_versions"].add(version)
        group["containers"].add(container)

    emitted_groups = []
    shared_count = 0
    for hash_value in sorted(groups):
        group = groups[hash_value]
        versions = sorted(group["firmware_versions"])
        shared = len(versions) > 1
        if shared:
            shared_count += 1
        emitted_groups.append(
            {
                "hash": hash_value,
                "occurrences": group["occurrences"],
                "firmware_version_count": len(versions),
                "firmware_versions": versions,
                "containers": sorted(group["containers"]),
                "shared_across_versions": shared,
            }
        )

    missing.sort(key=lambda item: (item["reason"], item["index"]))
    unvalidated.sort(key=lambda item: (item["hash"], item["index"]))

    return {
        "schema": SCHEMA,
        "record_count": record_count,
        "group_count": len(emitted_groups),
        "shared_group_count": shared_count,
        "unique_hash_count": len(emitted_groups),
        "groups": emitted_groups,
        "missing_hash_count": len(missing),
        "missing_hash_records": missing,
        "unvalidated_count": len(unvalidated),
        "unvalidated_records": unvalidated,
    }


def from_inventory_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Derive groups from the aggregate inventory summary; no per-hash records exist there."""
    records = summary.get("segments") or summary.get("segment_records") or []
    result = group_segment_hashes(records)
    result["source_inventory_sha256"] = summary.get("source_inventory_sha256")
    result["aggregate"] = {
        "candidate_count": summary.get("candidate_count"),
        "distinct_candidate_hash_count": summary.get("distinct_candidate_hash_count"),
        "duplicate_candidate_hashes": sorted(summary.get("duplicate_candidate_hashes") or []),
        "by_source_container": {
            name: summary["by_source_container"][name].get("distinct_candidate_hash_count")
            for name in sorted(summary.get("by_source_container", {}))
        },
    }
    if not records:
        result["limitations"] = [
            "Inventory summary exposes aggregate hash counts only; no per-segment hash values were available to group.",
            "Grouping is empty because no segment hash records were present in the declared source.",
        ]
    return result


def dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(dumps({"schema": SCHEMA, "error": "usage: segment_hash_groups.py <inventory.json>"}))
        return 2
    with open(argv[0], "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    print(dumps(from_inventory_summary(summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
