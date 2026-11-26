"""Deterministic PS5 candidate-metadata delta across version containers.

Reports only exact hash equality and declared field deltas. It never infers
component identity, ownership, or executable behavior.
"""

from __future__ import annotations

import json
import hashlib
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = "bc250-ps5-version-delta/1"
_RECORD_KEYS = ("records", "candidates", "entries")
_CONTAINER_KEYS = ("by_source_container", "containers", "by_container")
_HASH_KEYS = ("sha256", "hash", "candidate_hash")
_CONTAINER_FIELD_KEYS = ("container", "source_container", "version", "source")
_HASH_LIST_KEYS = ("candidate_hashes", "hashes")


def _norm_hash(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if re.fullmatch(r"[0-9a-f]{64}", value) else None


def _records(summary: Any) -> List[Dict[str, Any]]:
    if isinstance(summary, list):
        return [record for record in summary if isinstance(record, dict)]
    if not isinstance(summary, dict):
        return []
    for key in _RECORD_KEYS:
        value = summary.get(key)
        if isinstance(value, list):
            return [r for r in value if isinstance(r, dict)]
    return []


def _containers(summary: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(summary, list):
        grouped: Dict[str, Dict[str, Any]] = {}
        for record in _records(summary):
            name = _container_of(record)
            if name is None:
                continue
            fields = grouped.setdefault(name, {"candidate_count": 0, "bounds_valid_count": 0,
                                                "bounds_invalid_count": 0, "ghidra_zero_function_count": 0,
                                                "ghidra_positive_function_count": 0,
                                                "ghidra_function_total": 0,
                                                "validated_executable_bytes": 0})
            fields["candidate_count"] += 1
            if record.get("bounds_valid") is True:
                fields["bounds_valid_count"] += 1
            elif record.get("bounds_valid") is False:
                fields["bounds_invalid_count"] += 1
            functions = record.get("ghidra_functions")
            if isinstance(functions, int) and not isinstance(functions, bool) and functions >= 0:
                fields["ghidra_function_total"] += functions
                key = "ghidra_zero_function_count" if functions == 0 else "ghidra_positive_function_count"
                fields[key] += 1
            executable_bytes = record.get("validated_executable_bytes")
            if isinstance(executable_bytes, int) and not isinstance(executable_bytes, bool) and executable_bytes >= 0:
                fields["validated_executable_bytes"] += executable_bytes
        return grouped
    if not isinstance(summary, dict):
        return {}
    for key in _CONTAINER_KEYS:
        value = summary.get(key)
        if isinstance(value, dict):
            return {k: v for k, v in value.items() if isinstance(v, dict)}
    return {}


def _container_of(record: Dict[str, Any]) -> Optional[str]:
    for key in _CONTAINER_FIELD_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _hashes(container: Dict[str, Any], records: List[Dict[str, Any]], name: str) -> List[str]:
    found = []
    for record in records:
        if _container_of(record) != name:
            continue
        for key in _HASH_KEYS:
            digest = _norm_hash(record.get(key))
            if digest:
                found.append(digest)
                break
    if found:
        return sorted(set(found))
    for key in _HASH_LIST_KEYS:
        value = container.get(key)
        if isinstance(value, list):
            return sorted({h for h in map(_norm_hash, value) if h})
    return []


def _field_deltas(base: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
    deltas: Dict[str, Any] = {}
    for key in sorted(set(base) | set(target)):
        b, t = base.get(key), target.get(key)
        if b == t:
            continue
        numeric = (isinstance(b, (int, float)) and isinstance(t, (int, float))
                   and not isinstance(b, bool) and not isinstance(t, bool))
        deltas[key] = {"base": b, "target": t, "delta": t - b if numeric else None}
    return deltas


def compare_containers(summary: Any, base: str, target: str) -> Dict[str, Any]:
    containers = _containers(summary)
    for name in (base, target):
        if name not in containers:
            raise ValueError(f"unknown container: {name}")

    records = _records(summary)
    base_hashes = _hashes(containers[base], records, base)
    target_hashes = _hashes(containers[target], records, target)

    shared = sorted(set(base_hashes) & set(target_hashes))
    only_base = sorted(set(base_hashes) - set(target_hashes))
    only_target = sorted(set(target_hashes) - set(base_hashes))

    return {
        "schema": SCHEMA,
        "base": base,
        "target": target,
        "hash_equality": {
            "available": bool(base_hashes or target_hashes),
            "identical_count": len(shared),
            "identical_hashes": shared,
            "only_in_base": only_base,
            "only_in_target": only_target,
            "exact_match": bool(base_hashes or target_hashes) and not only_base and not only_target,
        },
        "field_deltas": _field_deltas(containers[base], containers[target]),
        "equal_fields": sorted(k for k in set(containers[base]) & set(containers[target])
                               if containers[base][k] == containers[target][k]),
        "limitations": [
            "Hash equality is byte-level only and does not establish component identity.",
            "Field deltas reflect declared metadata, not inferred semantics.",
        ],
    }


def inventory_summary(summary: Any, versions: Iterable[str]) -> Dict[str, Any]:
    """Summarize candidate counts and pairwise exact-hash deltas for versions."""
    containers = _containers(summary)
    names = list(versions)
    missing = [name for name in names if name not in containers]
    if missing:
        raise ValueError("unknown container(s): " + ", ".join(missing))
    pairs = []
    for index, base in enumerate(names):
        for target in names[index + 1:]:
            result = compare_containers(summary, base, target)
            equality = result["hash_equality"]
            pairs.append({
                "base": base,
                "target": target,
                "identical_hash_count": equality["identical_count"],
                "only_in_base_count": len(equality["only_in_base"]),
                "only_in_target_count": len(equality["only_in_target"]),
                "candidate_count_delta": result["field_deltas"].get("candidate_count", {}).get("delta", 0),
                "validated_executable_bytes_delta": result["field_deltas"].get("validated_executable_bytes", {}).get("delta", 0),
            })
    return {
        "schema": SCHEMA,
        "versions": {name: containers[name] for name in names},
        "pairwise_comparison": pairs,
        "limitations": [
            "SHA-256 equality compares complete candidate files, not individual ELF segments.",
            "Hash equality is byte-level only and does not establish component identity.",
            "Candidate counts can differ because extraction yielded different numbers of bounded candidates.",
        ],
    }


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print("usage: ps5_version_delta.py <summary.json> <base> <target>", file=sys.stderr)
        return 2
    try:
        with open(argv[0], "rb") as fh:
            raw = fh.read()
        summary = json.loads(raw.decode("utf-8-sig"))
        result = compare_containers(summary, argv[1], argv[2])
        result["source_inventory_sha256"] = hashlib.sha256(raw).hexdigest()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
