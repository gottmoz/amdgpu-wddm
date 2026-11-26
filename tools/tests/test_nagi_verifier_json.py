"""Tests for the JSON output mode of the pinned Nagi dependency verifier."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import tools.release.verify_python_build_deps as verifier
from tools.release.verify_python_build_deps import EXPECTED, report_json, verify

# Synthetic metadata: correct pins, one wrong version, one absent distribution.
SYNTHETIC_ACTUAL = {
    "meson": "1.12.0",
    "mako": "1.4.1",
    "markupsafe": "3.0.3",
    "pyyaml": "6.0.2",
}


class VerifierJsonTest(unittest.TestCase):
    def test_verify_expected_actual_missing(self):
        checks = verify(EXPECTED, SYNTHETIC_ACTUAL)
        self.assertEqual([c.name for c in checks], sorted(EXPECTED))
        self.assertEqual({c.name: c.expected for c in checks}, EXPECTED)
        self.assertEqual({c.name: c.actual for c in checks if c.actual is not None}, SYNTHETIC_ACTUAL)
        self.assertEqual([c.name for c in checks if c.actual is None], ["packaging"])

    def test_normalize_collapses_separator_variants(self):
        # normalize() collapses runs of [-_.] to a single "-"; pin keys must be
        # written in that canonical form (e.g. "pyyaml", not "Py_YAML").
        self.assertEqual(verifier.normalize("Py_YAML"), "py-yaml")
        self.assertEqual(verifier.normalize("MarkupSafe"), "markupsafe")
        self.assertEqual(verifier.normalize("pyyaml"), "pyyaml")

    def test_report_json_fields(self):
        report = report_json(verify(EXPECTED, SYNTHETIC_ACTUAL), Path("scratch/py"))
        self.assertEqual(report["schema"], "nagi-python-build-deps/1")
        self.assertFalse(report["ok"])
        self.assertEqual(report["expected"], EXPECTED)
        self.assertEqual(report["actual"], SYNTHETIC_ACTUAL)
        self.assertEqual(report["missing"], ["packaging"])
        self.assertEqual(report["mismatched"], ["pyyaml"])
        self.assertEqual(len(report["checks"]), len(EXPECTED))
        self.assertTrue(all(set(c) == {"name", "expected", "actual", "ok"} for c in report["checks"]))
        self.assertTrue(report["target"].endswith("py"))

    def test_report_json_all_ok(self):
        report = report_json(verify(EXPECTED, dict(EXPECTED)), Path("scratch/py"))
        self.assertTrue(report["ok"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["mismatched"], [])
        self.assertEqual(report["actual"], EXPECTED)

    def test_report_json_target_none(self):
        report = report_json(verify(EXPECTED, {}), None)
        self.assertIsNone(report["target"])
        self.assertEqual(report["missing"], sorted(EXPECTED))
        self.assertEqual(report["actual"], {})

    def test_main_json_mode(self):
        original = verifier.installed_versions
        verifier.installed_versions = lambda target: SYNTHETIC_ACTUAL
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = verifier.main(["--json", "--target", "scratch/py"])
        finally:
            verifier.installed_versions = original
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["missing"], ["packaging"])
        self.assertEqual(payload["mismatched"], ["pyyaml"])
        self.assertEqual(payload["expected"]["meson"], "1.12.0")

    def test_main_text_mode_still_works(self):
        original = verifier.installed_versions
        verifier.installed_versions = lambda target: dict(EXPECTED)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = verifier.main(["--target", "scratch/py"])
        finally:
            verifier.installed_versions = original
        self.assertEqual(rc, 0)
        self.assertIn("distribution  expected  actual   status", buf.getvalue())
        self.assertNotIn("{", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
