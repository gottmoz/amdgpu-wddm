"""Tiny BC-250 smoke utility: print sorted top-level keys of a JSON file."""

from __future__ import annotations

import json
import sys
from typing import List


def top_level_keys(path: str) -> List[str]:
    """Return the sorted top-level keys of a JSON object stored at ``path``."""
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return sorted(data.keys())


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/v2_smoke.py <json_file>", file=sys.stderr)
        return 2
    for key in top_level_keys(argv[1]):
        print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
