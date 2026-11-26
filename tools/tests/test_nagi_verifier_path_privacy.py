"""Path-privacy tests for the Nagi dependency verifier JSON report.

The verifier must never serialize an absolute local target path (drive letter,
POSIX absolute path, UNC share, or user-profile directory) into the report.
All fixtures are synthetic strings/paths; no firmware bytes or host state are
read.
"""
from __future__ import annotations

import io
import json
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import tools.release.verify_python_build_deps as verifier
from tools.release.verify_python_build_deps import EXPECTED, relative_label, report_json, verify

SYNTHETIC_ACTUAL = {
    "meson": "1.12.0",
    "mako": "1.4.1",
    "markupsafe": "3.0.3",
    "pyyaml": "6.0.2",
}

DRIVE_LETTER = re.compile(r"[A-Za-z]:[\\/]*")
ABSOLUTE_POSIX = re.compile(r"(^|[^A-Za-z0-9_-])/[A-Za-z0-9_.-]+/")
PROFILE_PATH = re.compile(r"(?:^|/)(?:home|users|profiles|codex)/", re.IGNORECASE)

REPORT_KEYS = ["actual", "checks", "expected", "mismatched", "missing", "ok", "schema", "target"]

HOST_LOCAL_TARGETS = [
    "/home/jimmy/.codex/scratch/py",
    "/Users/jimmy/.codex/scratch/py",
    "C:\\Users\\jimmy\\.codex\\scratch\\py",
    "C:\\BC250-Development\\scratch\\py",
    "D:\\BC250-Development\\scratch\\py\\..",
    "\\\\share\\scratch\\py",
    "//share/scratch/py",
    "~/.codex/scratch/py",
    "/tmp/scratch/py",
    "/absolute/scratch/py",
]


class VerifierPathPrivacyTest(unittest.TestCase):
    def test_relative_label_is_relative_and_forward_slash(self):
        for raw in ("scratch/py", "scratch/py/", "./scratch/py"):
            label = relative_label(raw)
            self.assertIsNotNone(label, f"expected a label for relative target {raw!r}")
            self.assertFalse(Path(label).is_absolute(), f"label {label!r} is absolute")
            self.assertNotIn("\\", label, f"label {label!r} contains a backslash")
            self.assertNotIn(":", label, f"label {label!r} contains a drive letter")

    def test_default_target_is_labelled_relative_to_root(self):
        label = relative_label(verifier.DEFAULT_TARGET)
        self.assertEqual(label, "scratch/py")

    def test_absolute_and_profile_targets_are_dropped(self):
        for raw in HOST_LOCAL_TARGETS:
            label = relative_label(raw)
            self.assertIsNone(label, f"expected no label for {raw!r}, got {label!r}")

    def test_none_and_empty_targets_are_none(self):
        self.assertIsNone(relative_label(None))
        self.assertIsNone(relative_label(""))
        self.assertIsNone(relative_label("."))
        self.assertIsNone(relative_label("scratch/../py"))

    def test_label_is_stable_across_repeats(self):
        first = relative_label("scratch/py")
        second = relative_label(Path("scratch/py"))
        self.assertEqual(first, second)
        self.assertEqual(first, relative_label("scratch/py"))

    def test_json_payload_contains_no_host_path(self):
        for raw in [None] + HOST_LOCAL_TARGETS + ["scratch/py"]:
            payload = json.dumps(report_json(verify(EXPECTED, SYNTHETIC_ACTUAL), raw), sort_keys=True)
            self.assertNotIn("\\", payload, f"serialized report for {raw!r} contains a backslash")
            for match in re.findall(r"\"target\":\s*\"([^\"]*)\"", payload):
                self.assertFalse(DRIVE_LETTER.search(match), f"drive letter in target label {match!r}")
                self.assertFalse(ABSOLUTE_POSIX.search(match), f"absolute path in target label {match!r}")
                self.assertFalse(PROFILE_PATH.search(match), f"profile path in target label {match!r}")

    def test_schema_and_keys_unchanged(self):
        report = report_json(verify(EXPECTED, SYNTHETIC_ACTUAL), "scratch/py")
        self.assertEqual(sorted(report), REPORT_KEYS)
        self.assertEqual(report["schema"], "nagi-python-build-deps/1")
        self.assertFalse(report["ok"])
        self.assertEqual(report["expected"], EXPECTED)
        self.assertEqual(report["actual"], SYNTHETIC_ACTUAL)
        self.assertEqual(report["missing"], ["packaging"])
        self.assertEqual(report["mismatched"], ["pyyaml"])
        self.assertTrue(all(set(c) == {"name", "expected", "actual", "ok"} for c in report["checks"]))

    def test_target_none_is_preserved(self):
        report = report_json(verify(EXPECTED, {}), None)
        self.assertIsNone(report["target"])
        self.assertEqual(report["missing"], sorted(EXPECTED))
        self.assertEqual(report["actual"], {})

    def test_main_json_mode_redacts_absolute_target(self):
        original = verifier.installed_versions
        verifier.installed_versions = lambda target: dict(EXPECTED)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = verifier.main(["--json", "--target", "/home/jimmy/.codex/scratch/py"])
        finally:
            verifier.installed_versions = original
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertIsNone(payload["target"])
        self.assertNotIn("\\", buf.getvalue())

    def test_main_json_mode_keeps_relative_target(self):
        original = verifier.installed_versions
        verifier.installed_versions = lambda target: dict(EXPECTED)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = verifier.main(["--json", "--target", "scratch/py"])
        finally:
            verifier.installed_versions = original
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["target"], "scratch/py")


if __name__ == "__main__":
    unittest.main()
