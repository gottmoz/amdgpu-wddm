"""Read-only verifier for the pinned Nagi Python build dependencies.

The JSON report never carries a host-local absolute path: ``target`` is either
``None`` or a forward-slash label relative to the declared BC250 root.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import re

SCHEMA = "nagi-python-build-deps/1"
EXPECTED = {
    "meson": "1.12.0",
    "mako": "1.4.1",
    "markupsafe": "3.0.3",
    "pyyaml": "6.0.3",
    "packaging": "25.0",
}
DEFAULT_ROOT = Path(os.environ.get("BC250_ROOT", r"D:\BC250-Development"))
DEFAULT_TARGET = DEFAULT_ROOT / "scratch" / "py"
PINNAMES = tuple(EXPECTED)

# Any string starting with a drive letter, a POSIX root, or a UNC/Windows root.
_ABSOLUTE_PREFIX = re.compile(r"^(?:[A-Za-z]:[\\/]*|[\\/])")
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]*$")
_PROFILE_SEGMENT = re.compile(r"^(?:home|users|profiles|codex)$", re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    name: str
    expected: str
    actual: str | None

    @property
    def ok(self) -> bool:
        return self.actual == self.expected


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def relative_label(target: Path | str | None) -> str | None:
    """Stable, host-free label for a target: always relative, forward-slash form.

    Never emits a drive letter, UNC share, user-profile directory, or any other
    absolute local path. Absolute targets are only labelled when they sit under
    the declared BC250 root (reported relative to it); every other absolute
    path, including UNC shares and profile paths, is dropped to ``None``.
    """
    if target is None:
        return None
    raw = str(target).strip()
    if not raw or raw.startswith("~"):
        return None

    path = Path(raw)
    if _ABSOLUTE_PREFIX.match(raw):
        try:
            rel = path.relative_to(DEFAULT_ROOT)
        except ValueError:
            return None
    else:
        rel = path

    if not rel.parts or any(part in ("", "..") for part in rel.parts):
        return None

    label = rel.as_posix()
    if not label or label == ".":
        return None
    if "\\" in label or _DRIVE.match(label) or label.startswith(("/", "\\")):
        return None
    first = label.split("/", 1)[0]
    if first == "~" or _PROFILE_SEGMENT.match(first):
        return None
    return label


def installed_versions(target: Path) -> dict[str, str]:
    """Read only distribution metadata from the supplied isolated target."""
    result = {}
    for dist in distributions(path=[str(Path(target).resolve())]):
        name = dist.metadata.get("Name")
        if name:
            result[normalize(name)] = dist.version
    return result


def verify(expected: dict[str, str], actual: dict[str, str]) -> list[Check]:
    return [Check(name, version, actual.get(normalize(name))) for name, version in sorted(expected.items())]


def report_json(checks: list[Check], target: Path | None = None) -> dict:
    """Machine-readable report: expected/actual/missing plus mismatch detail."""
    return {
        "schema": SCHEMA,
        "target": relative_label(target),
        "ok": all(check.ok for check in checks),
        "expected": {check.name: check.expected for check in checks},
        "actual": {check.name: check.actual for check in checks if check.actual is not None},
        "missing": [check.name for check in checks if check.actual is None],
        "mismatched": [check.name for check in checks if check.actual is not None and not check.ok],
        "checks": [
            {"name": check.name, "expected": check.expected, "actual": check.actual, "ok": check.ok}
            for check in checks
        ],
    }


def format_report(checks: list[Check]) -> str:
    lines = ["distribution  expected  actual   status"]
    for check in checks:
        lines.append(f"{check.name:<12}  {check.expected:<9}  {(check.actual or 'missing'):<8}  {'OK' if check.ok else 'MISMATCH'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET,
                        help="isolated scratch/py package target; no packages are installed")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report instead of text")
    args = parser.parse_args(argv)
    checks = verify(EXPECTED, installed_versions(args.target))
    if args.json:
        print(json.dumps(report_json(checks, args.target), sort_keys=True))
    else:
        print(format_report(checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
