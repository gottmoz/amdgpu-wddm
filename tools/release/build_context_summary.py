"""Deterministic summary of a build-context receipt.

Reports completion-state counts and missing relative input identifiers.
Absolute paths, environment values and host details are never emitted.
Tool names (resolved executables) are counted as missing states but are not
relative input identifiers.
"""
import argparse
import json
import os
import sys

COMPLETE_STATES = ("file", "directory")
MISSING_STATES = ("absent",)
PROBLEM_STATES = (
    "incomplete-directory", "unreadable", "changed-during-read",
    "unsupported-link", "unsupported-file-type",
)
DROP_KEYS = {"environment", "env", "host", "path_order", "problems"}


def _walk(value):
    if isinstance(value, dict):
        if "state" in value:
            yield value
        for key, item in value.items():
            if key not in DROP_KEYS:
                yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _relative(path, base):
    text = str(path).replace("\\", "/").strip()
    if not text or text.startswith("/") or text.startswith("\\"):
        return None
    root = str(base).replace("\\", "/").strip().rstrip("/")
    if root:
        try:
            text = os.path.relpath(text, root).replace("\\", "/")
        except ValueError:
            return None
    if os.path.isabs(text) or text in (".", "") or text.startswith(".."):
        return None
    return text


def summarize(receipt, base=""):
    counts = {}
    missing = []
    for entry in _walk(receipt):
        state = str(entry.get("state", "unknown"))
        counts[state] = counts.get(state, 0) + 1
        if state in MISSING_STATES:
            name = entry.get("identifier") or _relative(entry.get("path", ""), base)
            if name:
                missing.append(name)
    return {
        "schema": receipt.get("schema") if isinstance(receipt, dict) else None,
        "state_counts": dict(sorted(counts.items())),
        "complete": sum(counts.get(s, 0) for s in COMPLETE_STATES),
        "missing": sum(counts.get(s, 0) for s in MISSING_STATES),
        "problem": sum(counts.get(s, 0) for s in PROBLEM_STATES),
        "missing_inputs": sorted(set(missing)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize a build-context receipt.")
    parser.add_argument("receipt", help="path to a JSON receipt file")
    parser.add_argument("--base", default="", help="root used to make input identifiers relative")
    args = parser.parse_args(argv)
    with open(args.receipt, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    sys.stdout.write(json.dumps(summarize(receipt, args.base), sort_keys=True,
                                separators=(",", ":"), ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
