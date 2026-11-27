"""Deterministic summary of a build-context receipt.

Reads a build-context JSON document from a file or stdin. Reports counts by
completion state and the relative identifiers of missing inputs. No absolute
paths, drive letters, environment values, or host probes are emitted.

Malformed JSON and non-object documents are rejected with a concise error.
The error text never echoes the receipt body.

The declared source `tools/release/build_context.py` was read only in part, so
the state vocabulary below is a bounded superset. Any state not listed here is
counted as `unknown` instead of being guessed.
"""

from __future__ import annotations

import json
import sys

COMPLETE_STATES = frozenset({"file", "directory", "present", "ok", "readable", "hashed"})
MISSING_STATES = frozenset({"absent", "missing", "not-found", "notfound", "none"})
INCOMPLETE_STATES = frozenset({"incomplete", "incomplete-directory", "partial", "truncated", "changed-during-read", "stale"})
UNREADABLE_STATES = frozenset({"unreadable", "error", "denied", "permission-error"})
UNSUPPORTED_STATES = frozenset({"unsupported", "unsupported-link", "link", "symlink", "skipped"})

BUCKETS = ("complete", "missing", "incomplete", "unreadable", "unsupported")

MAX_ERROR_CHARS = 120


class ContextError(Exception):
    """Concise, content-free build-context loading failure."""


def normalize_path(value):
    """Return a forward-slash path with no drive letter or backslash."""
    text = str(value).strip().replace("\\", "/")
    if len(text) >= 2 and text[1] == ":":
        text = text[2:]
    while text.startswith("/"):
        text = text[1:]
    return text


def relative_identifier(value, root=None):
    """Return a relative identifier for an input path."""
    if value is None:
        return ""
    path = normalize_path(value)
    if not path:
        return ""
    if root:
        prefix = normalize_path(root)
        if prefix and path.startswith(prefix + "/"):
            path = path[len(prefix) + 1:]
    return path


def infer_root(records):
    """Infer a common root from the absolute paths of the records."""
    parts = []
    for _, _, record in records:
        if not isinstance(record, dict):
            continue
        raw = record.get("path")
        if not raw:
            continue
        pieces = normalize_path(raw).split("/")
        if len(pieces) > 1:
            parts.append(pieces[:-1])
    if not parts:
        return ""
    common = []
    for piece in zip(*parts):
        if all(item == piece[0] for item in piece):
            common.append(piece[0])
        else:
            break
    return "/".join(common)


def classify(record):
    """Map a record to one bucket name."""
    if not isinstance(record, dict):
        return "unknown"
    state = str(record.get("state", "")).strip().lower()
    if record.get("error"):
        return "unreadable"
    if state in COMPLETE_STATES:
        return "complete"
    if state in MISSING_STATES:
        return "missing"
    if state in INCOMPLETE_STATES:
        return "incomplete"
    if state in UNREADABLE_STATES:
        return "unreadable"
    if state in UNSUPPORTED_STATES:
        return "unsupported"
    return "unknown"


def _walk(node, key, index, records):
    if isinstance(node, dict):
        if "path" in node or "state" in node or "name" in node:
            records.append((key, index, node))
        for child_key, child in node.items():
            if child_key in ("schema", "root", "host", "notes"):
                continue
            _walk(child, child_key, 0, records)
    elif isinstance(node, list):
        for position, item in enumerate(node):
            _walk(item, key, position, records)


def collect_records(context):
    """Collect candidate input records from a nested context document."""
    records = []
    _walk(context, "inputs", 0, records)
    return records


def summarize(context, root=None):
    """Return a deterministic summary of one build-context document."""
    if not isinstance(context, dict):
        raise ContextError("build context must be a JSON object")

    records = collect_records(context)
    if root is None:
        root = infer_root(records)

    counts = {bucket: 0 for bucket in BUCKETS}
    counts["unknown"] = 0
    buckets = {bucket: [] for bucket in ("missing", "incomplete", "unreadable", "unsupported", "unknown", "complete")}

    for key, index, record in records:
        bucket = classify(record)
        counts[bucket] += 1
        identifier = relative_identifier(record.get("path"), root)
        if not identifier:
            identifier = f"{key}/{index}"
        buckets[bucket].append(identifier)

    for bucket in buckets:
        buckets[bucket] = sorted(set(buckets[bucket]))

    complete = not any(buckets[name] for name in ("missing", "incomplete", "unreadable", "unsupported", "unknown"))

    return {
        "records": len(records),
        "completion": counts,
        "missing": buckets["missing"],
        "incomplete": buckets["incomplete"],
        "unreadable": buckets["unreadable"],
        "unsupported": buckets["unsupported"],
        "unknown": buckets["unknown"],
        "complete": complete,
    }


def load(path):
    """Load a build-context JSON object from a path or from stdin when path is '-'."""
    try:
        if path == "-":
            text = sys.stdin.read()
        else:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
    except OSError as error:
        raise ContextError(f"could not read build context from {path}") from error

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ContextError(f"invalid JSON at line {error.lineno} column {error.colno}") from error

    if not isinstance(document, dict):
        raise ContextError("build context must be a JSON object")
    return document


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = None
    source = "-"
    positional = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--root":
            index += 1
            root = argv[index] if index < len(argv) else None
        elif item in ("--help", "-h"):
            print("usage: build_context_summary.py [--root ROOT] [PATH|-]")
            return 0
        else:
            positional.append(item)
        index += 1
    if positional:
        source = positional[0]

    try:
        context = load(source)
        result = summarize(context, root=root)
    except ContextError as error:
        message = str(error)[:MAX_ERROR_CHARS]
        print(f"error: {message}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
