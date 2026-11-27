"""CLI regression tests for malformed and non-object build-context JSON."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr

from tools.release.build_context_summary import main, summarize


TOKEN = "RECEIPT-LEAK-CANARY-9f2c"
MAX_STDERR_CHARS = 160


def run_cli_captured(text, argv=None):
    """Run the CLI with stdin text and return (exit_code, stdout, stderr)."""
    argv = list(argv if argv is not None else ["-"])
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    out = io.StringIO()
    err = io.StringIO()
    sys.stdin = io.StringIO(text)
    sys.stdout = out
    try:
        with redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
    return code, out.getvalue(), err.getvalue()


class MalformedJsonTests(unittest.TestCase):
    def test_truncated_object_is_rejected(self):
        code, stdout, stderr = run_cli_captured('{"inputs": [{"path": "a/b", ' + TOKEN)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("error:"))

    def test_error_is_concise(self):
        code, stdout, stderr = run_cli_captured("{" + TOKEN * 200)
        self.assertEqual(code, 1)
        self.assertLessEqual(len(stderr), MAX_STDERR_CHARS)

    def test_error_has_no_receipt_content(self):
        for text in (
            '{"inputs": [{"path": "' + TOKEN + '"',
            '{"inputs": [' + TOKEN + "]}",
            "not json at all " + TOKEN,
        ):
            code, stdout, stderr = run_cli_captured(text)
            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertNotIn(TOKEN, stderr)
            self.assertNotIn(TOKEN, stdout)

    def test_empty_input_is_rejected(self):
        code, stdout, stderr = run_cli_captured("")
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("error:"))

    def test_trailing_garbage_is_rejected(self):
        code, stdout, stderr = run_cli_captured('{"inputs": []} ' + TOKEN)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertNotIn(TOKEN, stderr)


class NonObjectJsonTests(unittest.TestCase):
    def test_array_is_rejected(self):
        code, stdout, stderr = run_cli_captured('[{"path": "a/b", "state": "file"}]')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("must be a JSON object", stderr)

    def test_string_is_rejected_without_echo(self):
        code, stdout, stderr = run_cli_captured('"' + TOKEN + '"')
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertNotIn(TOKEN, stderr)
        self.assertNotIn(TOKEN, stdout)

    def test_number_and_null_are_rejected(self):
        for text in ("123", "null", "true", "3.5"):
            code, stdout, stderr = run_cli_captured(text)
            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertIn("must be a JSON object", stderr)

    def test_summarize_rejects_non_object(self):
        for value in ([1, 2], "text", 7, None):
            with self.assertRaises(Exception):
                summarize(value)


class ValidContextTests(unittest.TestCase):
    def test_valid_object_is_summarized(self):
        payload = {
            "inputs": [
                {"path": "/build/a.bin", "state": "file"},
                {"path": "/build/b.bin", "state": "missing"},
            ]
        }
        code, stdout, stderr = run_cli_captured(json.dumps(payload))
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        result = json.loads(stdout)
        self.assertEqual(result["records"], 2)
        self.assertFalse(result["complete"])
        self.assertEqual(result["completion"]["complete"], 1)
        self.assertEqual(result["completion"]["missing"], 1)
        self.assertEqual(len(result["missing"]), 1)
        for identifier in result["missing"]:
            self.assertFalse(identifier.startswith("/"))

    def test_help_is_not_an_error(self):
        code, stdout, stderr = run_cli_captured("", ["--help"])
        self.assertEqual(code, 0)
        self.assertIn("usage", stdout)

    def test_missing_file_error_is_concise(self):
        code, stdout, stderr = run_cli_captured("", ["definitely-missing-context.json"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertLessEqual(len(stderr), MAX_STDERR_CHARS)
        self.assertTrue(stderr.startswith("error:"))


if __name__ == "__main__":
    unittest.main()
