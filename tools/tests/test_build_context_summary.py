"""Synthetic tests for the build-context summary.

Fixtures are inline dicts. No real filesystem, environment, or host probe is used.
Stdin is replaced with an in-memory stream so the CLI path never blocks.
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.release.build_context_summary import (
    main,
    relative_identifier,
    summarize,
)


def receipt():
    return {
        "schema": 2,
        "inputs": [
            {"path": "C:\\work\\tools\\release\\build_context.py", "state": "file", "sha256": "A" * 64, "bytes": 10},
            {"path": "C:\\work\\tools\\release", "state": "directory", "sha256": "B" * 64, "bytes": 20, "files": 2},
            {"path": "C:\\work\\tools\\release\\missing.ps1", "state": "absent"},
            {"path": "C:\\work\\sdk\\glslangValidator.exe", "state": "absent"},
            {"path": "C:\\work\\tools\\build\\versionstamp.py", "state": "unreadable", "error": "PermissionError"},
            {"path": "C:\\work\\tools\\build\\tree", "state": "incomplete-directory", "bytes": 3, "files": 1},
            {"path": "C:\\work\\tools\\build\\link", "state": "unsupported-link"},
            {"path": "C:\\work\\tools\\build\\fresh.py", "state": "changed-during-read"},
        ],
        "host": {"platform": "win32", "build": "12345"},
    }


class RelativeIdentifierTests(unittest.TestCase):
    def test_strips_drive_and_root(self):
        self.assertEqual(relative_identifier("C:\\work\\tools\\release", "C:\\work"), "tools/release")
        self.assertEqual(relative_identifier("/srv/build/tools"), "srv/build/tools")

    def test_keeps_relative_input_unchanged(self):
        self.assertEqual(relative_identifier("tools/release/provenance.py"), "tools/release/provenance.py")

    def test_empty_path_falls_back_to_nothing(self):
        self.assertEqual(relative_identifier(""), "")

    def test_no_backslash_or_drive_in_output(self):
        value = relative_identifier("C:\\work\\a\\b\\c.py", "C:\\work")
        self.assertNotIn("\\", value)
        self.assertNotIn(":", value)
        self.assertEqual(value, "a/b/c.py")


class SummaryTests(unittest.TestCase):
    def test_counts_by_completion_state(self):
        result = summarize(receipt())
        self.assertEqual(result["completion"], {
            "complete": 2,
            "missing": 2,
            "incomplete": 2,
            "unreadable": 1,
            "unsupported": 1,
            "unknown": 0,
        })
        self.assertEqual(result["records"], 8)

    def test_missing_identifiers_are_relative_and_sorted(self):
        result = summarize(receipt(), root="C:\\work")
        self.assertEqual(result["missing"], ["sdk/glslangValidator.exe", "tools/release/missing.ps1"])

    def test_other_buckets_are_reported(self):
        result = summarize(receipt(), root="C:\\work")
        self.assertEqual(result["incomplete"], ["tools/build/fresh.py", "tools/build/tree"])
        self.assertEqual(result["unreadable"], ["tools/build/versionstamp.py"])
        self.assertEqual(result["unsupported"], ["tools/build/link"])
        self.assertFalse(result["complete"])

    def test_no_absolute_path_leaks(self):
        text = str(summarize(receipt(), root="C:\\work"))
        self.assertNotIn("C:\\", text)
        self.assertNotIn("C:/", text)

    def test_deterministic_across_runs(self):
        self.assertEqual(summarize(receipt(), root="C:\\work"), summarize(receipt(), root="C:\\work"))

    def test_root_inferred_from_common_prefix(self):
        result = summarize(receipt())
        self.assertEqual(result["missing"], ["sdk/glslangValidator.exe", "tools/release/missing.ps1"])

    def test_nested_records_are_found(self):
        context = {
            "schema": 2,
            "runtime": {"helpers": [{"path": "C:\\work\\a.py", "state": "file"}]},
            "executables": [{"name": "cmake", "state": "absent"}, {"name": "ninja", "state": "absent"}],
        }
        result = summarize(context, root="C:\\work")
        self.assertEqual(result["completion"]["complete"], 1)
        self.assertEqual(result["missing"], ["executables/0", "executables/1"])

    def test_clean_receipt_is_complete(self):
        context = {"schema": 2, "inputs": [{"path": "C:\\work\\a.py", "state": "file"}]}
        result = summarize(context, root="C:\\work")
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_unknown_state_is_counted(self):
        context = {"schema": 2, "inputs": [{"path": "C:\\work\\a.py", "state": "weird"}]}
        result = summarize(context, root="C:\\work")
        self.assertEqual(result["completion"]["unknown"], 1)
        self.assertEqual(result["unknown"], ["a.py"])
        self.assertFalse(result["complete"])

    def test_empty_context(self):
        result = summarize({"schema": 2})
        self.assertEqual(result["records"], 0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])


class CliTests(unittest.TestCase):
    def test_cli_reads_stdin_and_emits_relative_summary(self):
        payload = '{"schema": 2, "inputs": [{"path": "C:\\\\work\\\\x.ps1", "state": "absent"}]}'
        buffer = io.StringIO()
        with patch("sys.stdin", io.StringIO(payload)), redirect_stdout(buffer):
            code = main(["--root", "C:\\work", "-"])
        self.assertEqual(code, 0)
        emitted = buffer.getvalue().strip()
        self.assertEqual(json.loads(emitted)["missing"], ["x.ps1"])
        self.assertEqual(json.loads(emitted)["completion"]["missing"], 1)
        self.assertFalse(json.loads(emitted)["complete"])
        self.assertNotIn("C:\\", emitted)
        self.assertEqual(emitted, json.dumps(json.loads(emitted), sort_keys=True))


if __name__ == "__main__":
    unittest.main()
