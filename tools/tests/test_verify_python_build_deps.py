"""Tests for the read-only Python build dependency verifier.

Every test injects a temporary target directory. No test installs a package.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.release.verify_python_build_deps import (
    DECLARED_NAMES,
    MATCH,
    MISMATCH,
    MISSING,
    PINNED_VERSIONS,
    PIN_FILENAME,
    INSTALLED_FILENAME,
    VerificationError,
    discover_dist_info,
    format_report,
    load_installed,
    load_pins,
    main,
    normalize_name,
    resolve_actual,
    verify,
)

PINS = {
    "Meson": "1.4.0",
    "mako": "1.3.2",
    "pip": "24.2",
    "wheel": "0.45.1",
    "setuptools": "74.0.0",
}


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


class TargetMixin(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_pins(self, pins: dict) -> None:
        write_json(self.target / PIN_FILENAME, pins)

    def write_installed(self, installed: dict) -> None:
        write_json(self.target / INSTALLED_FILENAME, installed)


class NormalisationTests(unittest.TestCase):
    def test_normalize_name_collates_variants(self) -> None:
        self.assertEqual(normalize_name("  Setuptools_Doc "), "setuptools-doc")
        self.assertEqual(normalize_name("M.A.K.O"), "m-a-k-o")

    def test_declared_names_are_five(self) -> None:
        self.assertEqual(len(DECLARED_NAMES), 5)
        self.assertEqual(
            DECLARED_NAMES,
            ("meson", "mako", "markupsafe", "pyyaml", "packaging"),
        )


class PinLoadingTests(TargetMixin):
    def test_pins_are_normalized(self) -> None:
        self.write_pins({"Meson_Doc": "1.4.0", "mako": "1.3.2", "pip": "24.2",
                         "wheel": "0.45.1", "setuptools": "74.0.0"})
        self.assertEqual(
            load_pins(self.target),
            {
                "meson-doc": "1.4.0",
                "mako": "1.3.2",
                "pip": "24.2",
                "wheel": "0.45.1",
                "setuptools": "74.0.0",
            },
        )

    def test_documented_pins_are_default_when_no_override_exists(self) -> None:
        self.assertEqual(load_pins(self.target), PINNED_VERSIONS)

    def test_incomplete_pin_file_raises(self) -> None:
        self.write_pins({"meson": "1.4.0"})
        with self.assertRaises(VerificationError) as caught:
            load_pins(self.target)
        self.assertIn("expected 5 pins", str(caught.exception))

    def test_empty_version_raises(self) -> None:
        self.write_pins({"meson": "1.4.0", "mako": "1.3.2", "pip": "24.2",
                         "wheel": "0.45.1", "setuptools": ""})
        with self.assertRaises(VerificationError) as caught:
            load_pins(self.target)
        self.assertIn("empty version", str(caught.exception))

    def test_non_string_version_raises(self) -> None:
        self.write_pins({"meson": 1, "mako": "1.3.2", "pip": "24.2",
                         "wheel": "0.45.1", "setuptools": "74.0.0"})
        with self.assertRaises(VerificationError):
            load_pins(self.target)

    def test_non_object_payload_raises(self) -> None:
        self.write_pins(["meson"])
        with self.assertRaises(VerificationError):
            load_pins(self.target)


class InstalledAndDistInfoTests(TargetMixin):
    def test_installed_manifest_is_read(self) -> None:
        self.write_installed({"Meson": "1.4.0", "pip": None})
        self.assertEqual(load_installed(self.target), {"meson": "1.4.0"})

    def test_missing_installed_manifest_is_empty(self) -> None:
        self.assertEqual(load_installed(self.target), {})

    def test_bad_installed_manifest_raises(self) -> None:
        self.write_installed({"meson": 1})
        with self.assertRaises(VerificationError):
            load_installed(self.target)

    def test_dist_info_directories_are_discovered(self) -> None:
        (self.target / "meson-1.4.0.dist-info").mkdir()
        (self.target / "setuptools-74.0.0.dist-info").mkdir()
        (self.target / "not-a-dist-info").mkdir()
        self.assertEqual(
            discover_dist_info(self.target),
            {"meson": "1.4.0", "setuptools": "74.0.0"},
        )

    def test_missing_target_dir_yields_no_dist_info(self) -> None:
        self.assertEqual(discover_dist_info(self.target / "absent"), {})

    def test_resolution_order_prefers_installed(self) -> None:
        actual = resolve_actual("meson", {"meson": "1.4.0"}, {"meson": "1.3.0"},
                                lambda name: "9.9.9")
        self.assertEqual(actual, "1.4.0")

    def test_resolution_falls_back_to_resolver(self) -> None:
        actual = resolve_actual("mako", {}, {}, lambda name: "1.3.2")
        self.assertEqual(actual, "1.3.2")

    def test_resolution_returns_none_when_absent(self) -> None:
        self.assertIsNone(resolve_actual("wheel", {}, {}, lambda name: None))


class VerificationTests(TargetMixin):
    def test_all_matching_versions_report_ok(self) -> None:
        self.write_pins(PINS)
        self.write_installed({name: PINS[name] for name in PINS})
        report = verify(self.target)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"], {MATCH: 5, MISMATCH: 0, MISSING: 0})

    def test_mismatch_is_reported(self) -> None:
        self.write_pins(PINS)
        self.write_installed({"meson": "1.4.0", "mako": "1.3.2", "pip": "23.0",
                             "wheel": "0.45.1", "setuptools": "74.0.0"})
        report = verify(self.target)
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"], {MATCH: 4, MISMATCH: 1, MISSING: 0})
        pip_record = next(r for r in report["records"] if r["name"] == "pip")
        self.assertEqual(pip_record["status"], MISMATCH)
        self.assertEqual(pip_record["actual"], "23.0")

    def test_missing_actual_is_reported(self) -> None:
        self.write_pins(PINS)
        report = verify(self.target)
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"], {MATCH: 0, MISMATCH: 0, MISSING: 5})

    def test_injected_resolver_is_used_for_unresolved_names(self) -> None:
        self.write_pins(PINS)
        versions = {normalize_name(name): PINS[name] for name in PINS}
        report = verify(self.target, resolver=lambda name: versions.get(name))
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"], {MATCH: 5, MISMATCH: 0, MISSING: 0})

    def test_dist_info_is_used_when_no_manifest_exists(self) -> None:
        self.write_pins(PINS)
        for name, version in PINS.items():
            (self.target / f"{name}-{version}.dist-info").mkdir()
        report = verify(self.target)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"], {MATCH: 5, MISMATCH: 0, MISSING: 0})

    def test_report_is_rendered_as_text(self) -> None:
        self.write_pins(PINS)
        self.write_installed({name: PINS[name] for name in PINS})
        text = format_report(verify(self.target))
        self.assertIn("summary: 5 match, 0 mismatch, 0 missing", text)
        self.assertIn("result: ok", text)

    def test_target_is_recorded_in_report(self) -> None:
        self.write_pins(PINS)
        report = verify(self.target)
        self.assertEqual(report["target"], "custom target")
        self.assertEqual(report["declared_names"], [normalize_name(name) for name in PINS])

    def test_report_does_not_emit_absolute_target_path(self) -> None:
        self.write_pins(PINS)
        report = verify(self.target)
        self.assertNotIn(str(self.target), json.dumps(report))


class MainTests(TargetMixin):
    def test_main_returns_zero_when_ok(self) -> None:
        self.write_pins(PINS)
        self.write_installed({name: PINS[name] for name in PINS})
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--target", str(self.target)])
        self.assertEqual(code, 0)
        self.assertIn("result: ok", buffer.getvalue())

    def test_main_returns_one_when_mismatch(self) -> None:
        self.write_pins(PINS)
        self.write_installed({"meson": "1.4.0", "mako": "1.3.2", "pip": "23.0",
                             "wheel": "0.45.1", "setuptools": "74.0.0"})
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--target", str(self.target)])
        self.assertEqual(code, 1)
        self.assertIn("result: failed", buffer.getvalue())

    def test_main_returns_two_when_target_is_invalid(self) -> None:
        buffer = io.StringIO()
        error_buffer = io.StringIO()
        invalid_target = self.target / "not-a-directory"
        invalid_target.write_text("not a directory", encoding="utf-8")
        with redirect_stdout(buffer), redirect_stderr(error_buffer):
            code = main(["--target", str(invalid_target)])
        self.assertEqual(code, 2)
        self.assertIn("target directory is missing", error_buffer.getvalue())
        self.assertNotIn(str(self.target), error_buffer.getvalue())
        self.assertEqual(buffer.getvalue(), "")

    def test_main_emits_json_when_asked(self) -> None:
        self.write_pins(PINS)
        self.write_installed({name: PINS[name] for name in PINS})
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--target", str(self.target), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(len(payload["records"]), 5)
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
