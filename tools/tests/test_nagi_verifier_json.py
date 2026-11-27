"""Tests for the JSON output mode of the pinned Python dependency verifier.

The tests use synthetic metadata written to a temporary directory. Nothing is
installed, downloaded, or read from the real scratch target.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, Iterable, Optional

from tools.release.verify_python_build_deps import (
    MATCH,
    MISMATCH,
    MISSING,
    SCHEMA,
    main,
    normalize_name,
    to_json,
    verify,
)

PINS: Dict[str, str] = {
    "meson": "1.4.0",
    "mako": "1.3.2",
    "pip": "24.0",
    "wheel": "0.43.0",
    "setuptools": "69.1.1",
}

RECORD_FIELDS = ("name", "expected", "actual", "status")
REPORT_FIELDS = ("schema", "target", "declared_names", "records", "summary", "ok")


def make_target(
    root: Path,
    pins: Optional[Dict[str, str]] = None,
    installed: Optional[Dict[str, Optional[str]]] = None,
    dist_info: Iterable[str] = (),
) -> Path:
    """Write synthetic pin and installed metadata into ``root``."""
    payload = pins if pins is not None else PINS
    (root / "python-build-pins.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    if installed is not None:
        (root / "python-build-installed.json").write_text(
            json.dumps(installed), encoding="utf-8"
        )

    for directory in dist_info:
        (root / directory).mkdir()

    return root


class JsonReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_json_report_exposes_expected_actual_and_missing_fields(self) -> None:
        target = make_target(
            self.root,
            installed={"meson": "1.4.0", "mako": "1.3.2", "pip": "24.0"},
        )
        report = verify(target)

        for record in report["records"]:
            for field in RECORD_FIELDS:
                self.assertIn(field, record)

        by_name = {record["name"]: record for record in report["records"]}
        self.assertEqual(by_name["meson"]["expected"], "1.4.0")
        self.assertEqual(by_name["meson"]["actual"], "1.4.0")
        self.assertEqual(by_name["meson"]["status"], MATCH)
        self.assertIsNone(by_name["wheel"]["actual"])
        self.assertEqual(by_name["wheel"]["status"], MISSING)

    def test_json_output_is_parseable_and_matches_the_report(self) -> None:
        target = make_target(
            self.root,
            installed={"meson": "1.4.0", "mako": "1.3.2", "pip": "24.0"},
        )
        report = verify(target)
        parsed = json.loads(to_json(report))

        self.assertEqual(parsed["schema"], SCHEMA)
        self.assertEqual(parsed["records"], report["records"])
        self.assertEqual(parsed["summary"], report["summary"])
        self.assertFalse(parsed["ok"])

    def test_summary_counts_match_mismatch_and_missing(self) -> None:
        target = make_target(
            self.root,
            installed={"meson": "1.4.0", "mako": "1.2.0"},
            dist_info=("wheel-0.43.0.dist-info",),
        )
        report = verify(target)

        self.assertEqual(report["summary"], {MATCH: 2, MISMATCH: 1, MISSING: 2})
        self.assertFalse(report["ok"])

        by_name = {record["name"]: record for record in report["records"]}
        self.assertEqual(by_name["mako"]["actual"], "1.2.0")
        self.assertEqual(by_name["mako"]["status"], MISMATCH)
        self.assertEqual(by_name["wheel"]["actual"], "0.43.0")
        self.assertEqual(by_name["wheel"]["status"], MATCH)
        self.assertIsNone(by_name["pip"]["actual"])
        self.assertEqual(by_name["pip"]["status"], MISSING)

    def test_cli_json_mode_prints_one_json_object(self) -> None:
        target = make_target(
            self.root,
            installed={name: PINS[name] for name in PINS},
        )

        with redirect_stdout(io.StringIO()) as stream:
            exit_code = main(["--target", str(target), "--json"])
        rendered = stream.getvalue()

        self.assertEqual(exit_code, 0)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], SCHEMA)
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["summary"], {MATCH: 5, MISMATCH: 0, MISSING: 0})
        self.assertEqual(len(parsed["records"]), 5)

    def test_cli_json_mode_uses_documented_pins_without_override_file(self) -> None:
        with redirect_stdout(io.StringIO()) as stream:
            exit_code = main(["--target", str(self.root), "--json"])
        rendered = stream.getvalue()

        self.assertEqual(exit_code, 1)
        parsed = json.loads(rendered)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["summary"][MISSING], 5)
        self.assertEqual(parsed["declared_names"], ["meson", "mako", "markupsafe", "pyyaml", "packaging"])
        self.assertNotIn(str(self.root), rendered)

    def test_cli_json_report_does_not_echo_custom_absolute_target(self) -> None:
        target = make_target(self.root, installed={name: PINS[name] for name in PINS})
        with redirect_stdout(io.StringIO()) as stream:
            exit_code = main(["--target", str(target), "--json"])
        rendered = stream.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertNotIn(str(target), rendered)
        self.assertEqual(json.loads(rendered)["target"], "custom target")

    def test_cli_text_mode_is_unchanged_by_json_flag(self) -> None:
        target = make_target(
            self.root,
            installed={"meson": "1.4.0", "mako": "1.3.2", "pip": "24.0"},
        )

        with redirect_stdout(io.StringIO()) as stream:
            exit_code = main(["--target", str(target)])
        text = stream.getvalue()

        self.assertEqual(exit_code, 1)
        self.assertIn("target:", text)
        self.assertIn("summary: 3 match, 0 mismatch, 2 missing", text)
        self.assertIn("result: failed", text)
        self.assertNotIn("{", text)

    def test_json_keys_are_sorted_and_stable(self) -> None:
        target = make_target(self.root, installed={"pip": "24.0"})
        rendered = to_json(verify(target))
        parsed = json.loads(rendered)

        self.assertEqual(list(parsed.keys()), sorted(parsed.keys()))
        self.assertEqual(rendered, to_json(parsed))

    def test_null_actual_is_emitted_as_json_null(self) -> None:
        target = make_target(self.root, installed={"setuptools": None})
        rendered = to_json(verify(target))

        self.assertIn('"actual": null', rendered)

    def test_injected_resolver_fills_unresolved_names(self) -> None:
        target = make_target(self.root)

        def resolver(name: str) -> Optional[str]:
            if name == "mako":
                return "1.3.2"
            return None

        report = verify(target, resolver=resolver)
        by_name = {record["name"]: record for record in report["records"]}

        self.assertEqual(by_name["mako"]["actual"], "1.3.2")
        self.assertEqual(by_name["mako"]["status"], MATCH)
        self.assertEqual(report["summary"][MISSING], 4)

    def test_normalisation_collates_name_variants(self) -> None:
        target = make_target(
            self.root,
            installed={"Mako": "1.3.2", "Setuptools": "69.1.1"},
            dist_info=("Wheel-0.43.0.dist-info",),
        )
        report = verify(target)
        by_name = {record["name"]: record for record in report["records"]}

        self.assertEqual(normalize_name("M_A.KO"), "m-a-ko")
        self.assertEqual(by_name["mako"]["status"], MATCH)
        self.assertEqual(by_name["setuptools"]["status"], MATCH)
        self.assertEqual(by_name["wheel"]["status"], MATCH)

    def test_declared_names_are_reported_in_order(self) -> None:
        target = make_target(self.root)
        parsed = json.loads(to_json(verify(target)))

        self.assertEqual(
            parsed["declared_names"],
            ["meson", "mako", "pip", "wheel", "setuptools"],
        )

    def test_invalid_pin_count_is_rejected(self) -> None:
        target = make_target(self.root, pins={"meson": "1.4.0"})
        with self.assertRaises(Exception) as raised:
            verify(target)
        self.assertIn("expected 5 pins", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
