"""Normalized distribution-name matching tests for the Nagi build-dependency verifier.

Uses isolated synthetic dist-info directories only; no real packages or firmware are touched.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.release.verify_python_build_deps import (
    EXPECTED,
    installed_versions,
    main,
    normalize,
    report_json,
    verify,
)


def make_dist(target: Path, name: str, version: str) -> None:
    dist = target / f"{name}-{version}.dist-info"
    dist.mkdir(parents=True)
    (dist / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n", encoding="utf-8"
    )
    (dist / "RECORD").write_text("", encoding="utf-8")


class TestNormalize(unittest.TestCase):
    def test_case_and_separator_variants(self):
        self.assertEqual(normalize("PyYAML"), "pyyaml")
        self.assertEqual(normalize("MESON"), "meson")
        self.assertEqual(normalize("MarkupSafe"), "markupsafe")
        self.assertEqual(normalize("pyyaml"), "pyyaml")

    def test_runs_of_separators_collapse_to_single_hyphen(self):
        self.assertEqual(normalize("Markup_Safe"), "markup-safe")
        self.assertEqual(normalize("Markup__..-Safe"), "markup-safe")
        self.assertEqual(normalize("Markup-Safe"), "markup-safe")
        self.assertEqual(normalize("importlib_metadata"), "importlib-metadata")

    def test_normalize_is_idempotent_for_pin_keys(self):
        for name in EXPECTED:
            self.assertEqual(normalize(normalize(name)), name)


class TestInstalledVersions(unittest.TestCase):
    def test_synthetic_distinfo_resolves_case_and_hyphen_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            make_dist(target, "Meson", "1.12.0")
            make_dist(target, "Mako", "1.4.1")
            make_dist(target, "MarkupSafe", "3.0.3")
            make_dist(target, "PyYAML", "6.0.3")
            make_dist(target, "packaging", "25.0")
            actual = installed_versions(target)
            self.assertEqual(actual, EXPECTED)

            report = report_json(verify(EXPECTED, actual), target)
            self.assertTrue(report["ok"])
            self.assertEqual(report["missing"], [])
            self.assertEqual(report["mismatched"], [])
            self.assertEqual(report["schema"], "nagi-python-build-deps/1")
            self.assertEqual([c["name"] for c in report["checks"]], sorted(EXPECTED))

    def test_separator_variant_of_pin_key_is_not_matched(self):
        # Documented limitation: pins must be written in the verifier's canonical
        # form. "Markup_Safe" normalizes to "markup-safe", which does not equal the
        # pin key "markupsafe", so it is reported as missing rather than matched.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            make_dist(target, "Markup_Safe", "3.0.3")
            actual = installed_versions(target)
            self.assertEqual(actual, {"markup-safe": "3.0.3"})

            checks = verify(EXPECTED, actual)
            self.assertEqual([c.name for c in checks if c.actual is None], sorted(EXPECTED))
            report = report_json(checks, target)
            self.assertFalse(report["ok"])
            self.assertEqual(report["missing"], sorted(EXPECTED))
            self.assertEqual(report["actual"], {})

    def test_mismatch_is_reported_per_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            make_dist(target, "PyYAML", "6.0.2")
            make_dist(target, "MarkupSafe", "3.0.3")
            checks = verify(EXPECTED, installed_versions(target))
            report = report_json(checks, target)
            self.assertEqual(report["mismatched"], ["pyyaml"])
            self.assertEqual(report["missing"], ["mako", "meson", "packaging"])
            self.assertEqual(report["actual"], {"markupsafe": "3.0.3", "pyyaml": "6.0.2"})
            self.assertFalse(report["ok"])
            pyyaml_check = next(c for c in report["checks"] if c["name"] == "pyyaml")
            self.assertEqual(
                (pyyaml_check["expected"], pyyaml_check["actual"], pyyaml_check["ok"]),
                ("6.0.3", "6.0.2", False),
            )

    def test_target_none_in_json_report(self):
        report = report_json(verify(EXPECTED, {}), None)
        self.assertIsNone(report["target"])
        self.assertEqual(sorted(report["missing"]), sorted(EXPECTED))
        self.assertFalse(report["ok"])


class TestCli(unittest.TestCase):
    def test_cli_json_exit_zero_for_normalized_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name, version in (
                ("MESON", "1.12.0"),
                ("Mako", "1.4.1"),
                ("MarkupSafe", "3.0.3"),
                ("PyYAML", "6.0.3"),
                ("packaging", "25.0"),
            ):
                make_dist(target, name, version)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["--target", str(target), "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out.getvalue())
            self.assertTrue(report["ok"])
            self.assertEqual(sorted(report["actual"]), sorted(EXPECTED))
            self.assertEqual(report["target"], str(Path(target).resolve()))

    def test_cli_text_mode_flags_unmatched_separator_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            make_dist(target, "Markup_Safe", "3.0.3")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--target", str(target)])
            self.assertEqual(code, 1)
            self.assertIn("markupsafe", out.getvalue())
            self.assertIn("MISMATCH", out.getvalue())


if __name__ == "__main__":
    unittest.main()
