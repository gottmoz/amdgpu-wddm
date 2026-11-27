"""Read-only verifier for the pinned Python build distributions in scratch/py.

The verifier compares the five pinned build distributions declared by the release
manifest against what is present in the scratch target. It never installs,
downloads, or mutates anything. Actual versions come from an optional installed
manifest file, then from ``*.dist-info`` directories, then from an injected
resolver.

The default pins mirror the five distributions and versions in ``docs/build.md``.
An optional ``python-build-pins.json`` in the target can override them for a
separate development environment.

Output modes: the default mode prints plain text. ``--json`` prints the same
report as a machine-readable JSON object with the fields ``schema``, ``target``,
``declared_names``, ``records``, ``summary``, and ``ok``. Every record carries
``name``, ``expected``, ``actual``, and ``status``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

DEFAULT_TARGET = "scratch/py"
PIN_FILENAME = "python-build-pins.json"
INSTALLED_FILENAME = "python-build-installed.json"
EXPECTED_PIN_COUNT = 5
SCHEMA = "nagi-python-build-deps/1"

MATCH = "match"
MISMATCH = "mismatch"
MISSING = "missing"

PINNED_VERSIONS: Dict[str, str] = {
    "meson": "1.12.0",
    "mako": "1.4.1",
    "markupsafe": "3.0.3",
    "pyyaml": "6.0.3",
    "packaging": "25.0",
}
DECLARED_NAMES: Tuple[str, ...] = tuple(PINNED_VERSIONS)


class VerificationError(Exception):
    """Raised when the target cannot be verified from its declarations."""


def normalize_name(name: str) -> str:
    """Collate a distribution name to a comparison key."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def target_label(target: Path) -> str:
    """Return a stable non-sensitive label for report output."""
    if target.is_absolute() or ".." in target.parts:
        return "custom target"
    return target.as_posix()


def load_pins(target: Path) -> Dict[str, str]:
    """Read an optional override or use the versions documented by the project."""
    path = target / PIN_FILENAME
    if not path.is_file():
        return dict(PINNED_VERSIONS)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VerificationError(f"invalid json in {PIN_FILENAME}: {error}") from error

    if not isinstance(payload, dict):
        raise VerificationError(f"{PIN_FILENAME} must contain an object")

    pins: Dict[str, str] = {}
    for key, value in payload.items():
        name = normalize_name(str(key))
        if not isinstance(value, str):
            raise VerificationError(f"pin {name} must have a string version")
        version = value.strip()
        if not version:
            raise VerificationError(f"pin {name} has an empty version")
        pins[name] = version

    if len(pins) != EXPECTED_PIN_COUNT:
        raise VerificationError(
            f"expected {EXPECTED_PIN_COUNT} pins, found {len(pins)}"
        )

    return pins


def discover_dist_info(target: Path) -> Dict[str, str]:
    """Collect versions from ``name-version.dist-info`` directories."""
    found: Dict[str, str] = {}
    if not target.is_dir():
        return found

    for entry in sorted(target.iterdir()):
        if not entry.is_dir() or not entry.name.endswith(".dist-info"):
            continue
        stem = entry.name[: -len(".dist-info")]
        if "-" not in stem:
            continue
        name, version = stem.rsplit("-", 1)
        if not name or not version:
            continue
        found[normalize_name(name)] = version.strip()

    return found


def load_installed(target: Path) -> Dict[str, str]:
    """Read an optional installed-version manifest from the target."""
    path = target / INSTALLED_FILENAME
    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VerificationError(f"invalid json in {INSTALLED_FILENAME}: {error}") from error

    if not isinstance(payload, dict):
        raise VerificationError(f"{INSTALLED_FILENAME} must contain an object")

    installed: Dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise VerificationError(f"installed {normalize_name(str(key))} must be a string")
        version = value.strip()
        if version:
            installed[normalize_name(str(key))] = version

    return installed


def resolve_actual(
    name: str,
    installed: Dict[str, str],
    dist_info: Dict[str, str],
    resolver: Optional[Callable[[str], Optional[str]]],
) -> Optional[str]:
    """Find the actual version for one pinned name, in declared order."""
    if name in installed:
        return installed[name]
    if name in dist_info:
        return dist_info[name]
    if resolver is not None:
        value = resolver(name)
        if value is not None:
            return str(value).strip()
    return None


def verify(
    target: str | Path,
    resolver: Optional[Callable[[str], Optional[str]]] = None,
) -> Dict[str, object]:
    """Build a read-only verification report for the target."""
    target_path = Path(target)
    if not target_path.is_dir():
        raise VerificationError("target directory is missing")
    pins = load_pins(target_path)
    installed = load_installed(target_path)
    dist_info = discover_dist_info(target_path)

    records: List[Dict[str, object]] = []
    summary = {MATCH: 0, MISMATCH: 0, MISSING: 0}

    for name, expected in pins.items():
        actual = resolve_actual(name, installed, dist_info, resolver)
        if actual is None:
            status = MISSING
        elif actual == expected:
            status = MATCH
        else:
            status = MISMATCH
        summary[status] += 1
        records.append(
            {
                "name": name,
                "expected": expected,
                "actual": actual,
                "status": status,
            }
        )

    return {
        "schema": SCHEMA,
        "target": target_label(target_path),
        "declared_names": list(pins),
        "records": records,
        "summary": summary,
        "ok": summary[MISSING] == 0 and summary[MISMATCH] == 0,
    }


def to_json(report: Dict[str, object]) -> str:
    """Render a report as stable, machine-readable JSON."""
    return json.dumps(report, indent=2, sort_keys=True)


def error_json(message: str) -> str:
    """Render a verification failure as machine-readable JSON."""
    return to_json({"schema": SCHEMA, "error": message, "ok": False})


def format_report(report: Dict[str, object]) -> str:
    """Render the report as plain text lines."""
    lines = [f"target: {report['target']}"]
    for record in report["records"]:
        actual = record["actual"] if record["actual"] is not None else "none"
        lines.append(
            f"{record['name']}: expected {record['expected']} "
            f"actual {actual} status {record['status']}"
        )
    summary = report["summary"]
    lines.append(
        f"summary: {summary[MATCH]} match, "
        f"{summary[MISMATCH]} mismatch, {summary[MISSING]} missing"
    )
    lines.append("result: ok" if report["ok"] else "result: failed")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify pinned Python build distributions without installing."
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help="scratch target to verify",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the report as machine-readable JSON",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = verify(args.target)
    except VerificationError as error:
        if args.json:
            print(error_json(str(error)))
        else:
            print(f"error: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(to_json(report))
    else:
        print(format_report(report))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
