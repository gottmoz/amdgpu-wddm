"""Read-only verifier for the pinned Nagi Python build dependencies."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib.metadata import distributions
import os
from pathlib import Path
import re

EXPECTED = {
    "meson": "1.12.0",
    "mako": "1.4.1",
    "markupsafe": "3.0.3",
    "pyyaml": "6.0.3",
    "packaging": "25.0",
}
DEFAULT_TARGET = Path(os.environ.get("BC250_ROOT", r"D:\BC250-Development")) / "scratch" / "py"
PINNAMES = tuple(EXPECTED)


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


def format_report(checks: list[Check]) -> str:
    lines = ["distribution  expected  actual   status"]
    for check in checks:
        lines.append(f"{check.name:<12}  {check.expected:<9}  {(check.actual or 'missing'):<8}  {'OK' if check.ok else 'MISMATCH'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET,
                        help="isolated scratch/py package target; no packages are installed")
    args = parser.parse_args(argv)
    checks = verify(EXPECTED, installed_versions(args.target))
    print(format_report(checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
