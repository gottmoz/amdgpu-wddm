"""Compare exact hashes of bounded executable segments in a PS5 ELF inventory."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


SCHEMA = "bc250.ps5-segment-comparison/v1"
VERSIONS = {
    "1100_PS5UPDATE1.PUP.dec": "11.00",
    "1120_PS5UPDATE1.PUP.dec": "11.20",
    "1140_PS5UPDATE1.PUP.dec": "11.40",
}
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")


def _integer(value, field, candidate):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} is invalid for {candidate}")
    return value


def compare_executable_segments(inventory):
    if not isinstance(inventory, list):
        raise ValueError("inventory must be a list")

    segments = []
    seen_candidates = set()
    for row in inventory:
        if not isinstance(row, dict):
            raise ValueError("inventory rows must be objects")
        container = row.get("source_container")
        if not isinstance(container, str) or not container.endswith(".PUP.dec"):
            continue
        if container not in VERSIONS:
            raise ValueError(f"unsupported PUP version container: {container}")

        if row.get("bounds_valid") is not True:
            raise ValueError(f"candidate boundary validation is not successful for {row.get('candidate', '<unknown>')}")
        if row.get("binary_audit_schema") != "bc250.firmware-audit/v1":
            raise ValueError("candidate inventory does not identify the supported binary audit schema")
        parser_version = row.get("binary_audit_parser_version")
        if not isinstance(parser_version, int) or isinstance(parser_version, bool) or parser_version < 2:
            raise ValueError("candidate inventory does not identify a supported parser version")

        candidate = row.get("candidate")
        if not isinstance(candidate, str) or not candidate:
            raise ValueError("PUP candidate name is missing")
        if candidate in seen_candidates:
            raise ValueError(f"duplicate PUP candidate: {candidate}")
        seen_candidates.add(candidate)

        source_offset = _integer(row.get("source_offset"), "source_offset", candidate)
        executable = row.get("executable_segments")
        if not isinstance(executable, list) or not executable:
            raise ValueError(f"executable segment metadata is missing for {candidate}")
        for segment in executable:
            if not isinstance(segment, dict):
                raise ValueError(f"executable segment record is invalid for {candidate}")
            digest = segment.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise ValueError(f"executable segment SHA-256 is invalid for {candidate}")
            record = {
                "version": VERSIONS[container],
                "candidate": candidate,
                "source_offset": source_offset,
                "segment_index": _integer(segment.get("index"), "segment index", candidate),
                "file_offset": _integer(segment.get("file_offset"), "file_offset", candidate),
                "virtual_address": _integer(segment.get("virtual_address"), "virtual_address", candidate),
                "file_size": _integer(segment.get("file_size"), "file_size", candidate),
                "flags": _integer(segment.get("flags"), "flags", candidate),
                "entropy_bits_per_byte": segment.get("entropy_bits_per_byte"),
                "sha256": digest.lower(),
            }
            if record["file_size"] == 0:
                raise ValueError(f"executable segment has zero file size for {candidate}")
            segments.append(record)

    if not segments:
        raise ValueError("inventory contains no executable PUP segments")
    segments.sort(key=lambda item: (item["version"], item["source_offset"], item["candidate"], item["segment_index"]))

    by_hash = defaultdict(list)
    by_version = defaultdict(list)
    for segment in segments:
        by_hash[segment["sha256"]].append(segment)
        by_version[segment["version"]].append(segment)

    cross_version_matches = []
    for digest, instances in sorted(by_hash.items()):
        versions = sorted({instance["version"] for instance in instances})
        if len(versions) > 1:
            cross_version_matches.append({
                "sha256": digest,
                "versions": versions,
                "instances": instances,
            })

    version_summary = [
        {
            "version": version,
            "candidate_count": len({item["candidate"] for item in items}),
            "segment_count": len(items),
            "unique_hash_count": len({item["sha256"] for item in items}),
        }
        for version, items in sorted(by_version.items())
    ]
    return {
        "schema": SCHEMA,
        "comparison": "exact SHA-256 equality of bounded executable segment file bytes",
        "summary": {
            "candidate_count": len(seen_candidates),
            "segment_count": len(segments),
            "unique_hash_count": len(by_hash),
            "cross_version_match_hash_count": len(cross_version_matches),
        },
        "versions": version_summary,
        "segments": segments,
        "cross_version_matches": cross_version_matches,
        "limitations": [
            "Only exact segment-byte hash matches are reported.",
            "A hash match does not establish component identity or loader compatibility.",
            "No approximate similarity score is computed.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    report = compare_executable_segments(inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {report['summary']['segment_count']} segment records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
