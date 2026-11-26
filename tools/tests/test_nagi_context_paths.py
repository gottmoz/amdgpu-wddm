"""Path-safety tests for tools/release/build_context_summary.py.

Covers UNC roots, absolute paths and parent traversal in build-context
summaries, and asserts that no host path or host detail is emitted.
The source utility is not modified.
"""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.release.build_context_summary import _relative, main, summarize

UNC_BASE = "\\\\server\\share\\build"
UNC_PATH = "\\\\server\\share\\build\\inputs\\a.bin"


class TestRelativePaths(unittest.TestCase):
    def test_unc_root_is_rejected(self):
        self.assertIsNone(_relative(UNC_PATH, UNC_BASE))
        self.assertIsNone(_relative("//server/share/build/inputs/a.bin", "//server/share"))
        self.assertIsNone(_relative("\\\\server\\share", ""))

    def test_absolute_paths_are_rejected(self):
        for path in ("/etc/passwd", "/tmp/a.bin", "\\\\host\\x"):
            self.assertIsNone(_relative(path, ""))

    def test_parent_traversal_is_rejected(self):
        for path in ("../secret", "..", "./..", "inputs/../../x", "inputs/../a.bin"):
            self.assertIsNone(_relative(path, "inputs"))

    def test_normal_relative_paths_survive(self):
        self.assertEqual(_relative("inputs/a.bin", "inputs"), "a.bin")
        self.assertEqual(_relative("build\\inputs\\a.bin", "build"), "inputs/a.bin")
        self.assertEqual(_relative("a.bin", ""), "a.bin")
        self.assertIsNone(_relative(".", "build"))
        self.assertIsNone(_relative("", "build"))

    def test_cross_root_relative_never_leaks_absolute_path(self):
        result = _relative(os.path.join(os.sep, "etc", "passwd"), "build")
        self.assertTrue(result is None or not os.path.isabs(result))


class TestSummary(unittest.TestCase):
    def _receipt(self):
        return {
            "schema": "build-context/1",
            "host": "DESKTOP-HOST",
            "environment": {"HOME": "/home/user"},
            "path_order": [UNC_PATH, "/etc/passwd"],
            "problems": [{"path": "\\\\server\\share\\build\\inputs\\locked.bin"}],
            "entries": [
                {"state": "file", "path": UNC_PATH},
                {"state": "absent", "path": UNC_PATH},
                {"state": "absent", "path": "/etc/passwd"},
                {"state": "absent", "path": "../outside/secret.bin"},
                {"state": "absent", "path": "inputs/missing.bin"},
                {"state": "absent", "path": "inputs/missing.bin"},
                {"state": "absent", "identifier": "toolchain/meson", "path": UNC_PATH},
                {"state": "unreadable", "path": "inputs/locked.bin"},
            ],
        }

    def test_summary_drops_unsafe_paths(self):
        report = summarize(self._receipt(), UNC_BASE)
        self.assertEqual(report["missing_inputs"], ["toolchain/meson"])
        self.assertEqual(report["missing"], 6)
        self.assertEqual(report["complete"], 1)
        self.assertEqual(report["problem"], 1)
        self.assertEqual(report["schema"], "build-context/1")

    def test_no_host_path_or_host_detail_emitted(self):
        rendered = json.dumps(summarize(self._receipt(), UNC_BASE), sort_keys=True)
        for forbidden in ("server", "share", "etc", "passwd", "outside", "DESKTOP-HOST",
                          "HOME", "environment", "host", "path_order", "problems"):
            self.assertNotIn(forbidden, rendered)
        self.assertNotIn("\\\\", rendered)
        self.assertNotIn(os.getcwd(), rendered)

    def test_deterministic_and_sorted(self):
        first = json.dumps(summarize(self._receipt(), UNC_BASE),
                           sort_keys=True, separators=(",", ":"))
        second = json.dumps(summarize(self._receipt(), UNC_BASE),
                            sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)
        self.assertEqual(first.count('"missing_inputs":["toolchain/meson"]'), 1)

    def test_cli_writes_json_without_host_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "receipt.json")
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(self._receipt(), stream)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main([path, "--base", UNC_BASE])
            text = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("toolchain/meson", text)
        self.assertNotIn("server", text)
        self.assertNotIn(os.getcwd(), text)
        self.assertEqual(json.loads(text)["missing_inputs"], ["toolchain/meson"])


if __name__ == "__main__":
    unittest.main()
