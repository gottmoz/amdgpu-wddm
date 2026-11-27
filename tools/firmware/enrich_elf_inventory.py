"""Join deterministic ELF audit output to a container inventory by exact hash."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


AUDIT_SCHEMA = "bc250.firmware-audit/v1"


def enrich_inventory(inventory: list[dict], audit: dict) -> list[dict]:
    if not isinstance(inventory, list) or not all(isinstance(row, dict) for row in inventory):
        raise ValueError("inventory must be a list of candidate records")
    if not isinstance(audit, dict) or audit.get("schema") != AUDIT_SCHEMA:
        raise ValueError("unsupported binary audit schema")
    parser_version = audit.get("parser_version")
    if not isinstance(parser_version, int) or isinstance(parser_version, bool):
        raise ValueError("binary audit parser version is invalid")
    files = audit.get("files")
    if not isinstance(files, list) or not all(isinstance(item, dict) for item in files):
        raise ValueError("binary audit files must be a list")

    audited = {}
    for item in files:
        name = Path(item.get("path", "")).name
        if not name or name in audited:
            raise ValueError("binary audit has a missing or duplicate candidate name")
        audited[name] = item

    candidates = {}
    for row in inventory:
        name = row.get("candidate")
        if not isinstance(name, str) or not name or name in candidates:
            raise ValueError("inventory has a missing or duplicate candidate name")
        candidates[name] = row
    if set(candidates) != set(audited):
        missing = sorted(set(candidates) - set(audited))
        extra = sorted(set(audited) - set(candidates))
        raise ValueError(f"candidate sets differ: missing audit={missing}, extra audit={extra}")

    enriched = []
    for name, row in candidates.items():
        item = audited[name]
        if row.get("size") != item.get("size"):
            raise ValueError(f"candidate size differs for {name}")
        if str(row.get("sha256", "")).lower() != str(item.get("sha256", "")).lower():
            raise ValueError(f"candidate SHA-256 differs for {name}")
        elf = item.get("elf")
        if not isinstance(elf, dict) or not isinstance(elf.get("type"), int):
            raise ValueError(f"ELF metadata is missing for {name}")

        e_type = elf["type"]
        if not 0 <= e_type <= 0xFFFF:
            raise ValueError(f"ELF e_type is outside u16 range for {name}")
        segments = [
            {
                "index": segment["index"],
                "file_offset": segment["offset"],
                "virtual_address": segment["vaddr"],
                "file_size": segment["filesz"],
                "memory_size": segment["memsz"],
                "flags": segment["flags"],
                "zero_initialized_bytes": segment["zero_initialized_bytes"],
                "sha256": segment["sha256"],
                "entropy_bits_per_byte": segment["entropy_bits_per_byte"],
            }
            for segment in elf.get("program_headers", [])
            if segment.get("type") == 1 and segment.get("executable")
            and segment.get("bounded") and segment.get("filesz", 0) > 0
        ]

        result = dict(row)
        result.update({
            "e_type": e_type,
            "e_type_hex": f"0x{e_type:04x}",
            "entry_point_mapped": bool(elf.get("entry_valid")),
            "executable_segments": segments,
            "binary_audit_schema": audit["schema"],
            "binary_audit_parser_version": parser_version,
        })
        enriched.append(result)
    return enriched


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    result = enrich_inventory(inventory, audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(result)} candidates to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
