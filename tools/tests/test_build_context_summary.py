import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.release.build_context_summary import main, summarize

RECEIPT = {
    "schema": 2,
    "host": {"platform": "win32", "build": "19045"},
    "environment": {"PATH": "C:\\Windows", "INCLUDE": "C:\\sdk"},
    "inputs": {
        "roots": [
            {"path": "C:\\build\\src\\core", "state": "directory", "files": 3},
            {"path": "C:\\build\\src\\missing.c", "state": "absent"},
            {"path": "C:\\build\\src\\tool", "state": "unreadable", "error": "OSError"},
            {"path": "C:\\build\\src\\link", "state": "unsupported-link"},
        ],
        "helpers": [
            {"identifier": "tools/release/provenance.py", "state": "file"},
            {"identifier": "tools/build/versionstamp.py", "state": "absent"},
        ],
    },
    "executables": [
        {"name": "python", "state": "file"},
        {"name": "cmake", "state": "absent"},
    ],
}

EXPECTED_MISSING = ["src/missing.c", "tools/build/versionstamp.py"]


class BuildContextSummaryTests(unittest.TestCase):
    def test_counts_and_missing(self):
        result = summarize(RECEIPT, base="C:\\build")
        self.assertEqual(result["schema"], 2)
        self.assertEqual(result["state_counts"], {
            "absent": 3, "directory": 1, "file": 2,
            "unsupported-link": 1, "unreadable": 1,
        })
        self.assertEqual(result["complete"], 3)
        self.assertEqual(result["missing"], 3)
        self.assertEqual(result["problem"], 2)
        self.assertEqual(result["missing_inputs"], EXPECTED_MISSING)

    def test_no_absolute_paths_or_environment(self):
        text = json.dumps(summarize(RECEIPT, base="C:\\build"))
        self.assertNotIn("C:\\", text)
        self.assertNotIn("C:/", text)
        self.assertNotIn("Windows", text)
        self.assertNotIn("PATH", text)

    def test_deterministic_and_deduplicated(self):
        self.assertEqual(summarize(RECEIPT, "C:\\build"), summarize(RECEIPT, "C:\\build"))
        dup = {"inputs": [{"path": "C:\\build\\a.c", "state": "absent"},
                          {"path": "C:\\build\\a.c", "state": "absent"}]}
        self.assertEqual(summarize(dup, "C:\\build")["missing_inputs"], ["a.c"])

    def test_absolute_and_escape_paths_are_dropped(self):
        result = summarize({"inputs": [
            {"path": "/tmp/x.c", "state": "absent"},
            {"path": "C:\\other\\y.c", "state": "absent"},
            {"path": "C:\\build\\..\\z.c", "state": "absent"},
        ]}, base="C:\\build")
        self.assertEqual(result["missing_inputs"], [])
        self.assertEqual(result["missing"], 3)

    def test_cli_emits_json(self):
        payload = io.StringIO(json.dumps(RECEIPT))
        buffer = io.StringIO()
        with patch("builtins.open", lambda *_a, **_k: payload), redirect_stdout(buffer):
            self.assertEqual(main(["receipt.json", "--base", "C:\\build"]), 0)
        emitted = json.loads(buffer.getvalue())
        self.assertEqual(emitted["missing"], 3)
        self.assertEqual(emitted["missing_inputs"], EXPECTED_MISSING)
        self.assertNotIn(" ", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
