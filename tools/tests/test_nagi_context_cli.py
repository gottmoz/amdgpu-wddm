"""CLI regression tests for malformed / non-object build-context receipts."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tools.release.build_context_summary import load_receipt, main, summarize

SECRET = "LEAKY_RECEIPT_MARKER_9f2c"
CONCISE_ERRORS = ("receipt is empty", "receipt is not valid JSON",
                  "receipt must be a JSON object", "cannot read receipt")
LEAK_TOKENS = ("schema", "entries", "state", "absent", "file", "identifier",
               "environment", "host", "problems", "path_order")


def _write(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


def run_cli(path, base=None):
    out, err = io.StringIO(), io.StringIO()
    argv = [path] + (["--base", base] if base else [])
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def error_of(err_text):
    return json.loads(err_text)


class TestNagiContextCli(unittest.TestCase):
    MALFORMED = [
        "",
        "   \n\t  ",
        "{",
        '{"schema": "nagi/1",',
        '{"schema": "nagi/1" "entries": []}',
        '{"state": "file"}]',
        "not json at all",
        '{"state": "file"}, {"state": "absent"}',
        '{"schema": "nagi/1", "entries": [',
    ]
    NON_OBJECT = [
        "[]",
        "[1, 2, 3]",
        '"just a string"',
        "123",
        "1.5",
        "true",
        "false",
        "null",
    ]

    def test_malformed_json_is_rejected_concisely(self):
        for text in self.MALFORMED:
            path = _write(text)
            try:
                code, out, err = run_cli(path)
                self.assertEqual(code, 1, text)
                self.assertEqual(out, "", text)
                payload = error_of(err)
                self.assertEqual(list(payload), ["error"], text)
                message = payload["error"]
                self.assertTrue(message, text)
                self.assertLess(len(message), 60, text)
                self.assertIn(message, ("receipt is empty", "receipt is not valid JSON"))
            finally:
                os.unlink(path)

    def test_non_object_json_is_rejected(self):
        for text in self.NON_OBJECT:
            path = _write(text)
            try:
                code, out, err = run_cli(path)
                self.assertEqual(code, 1, text)
                self.assertEqual(out, "", text)
                self.assertEqual(error_of(err),
                                 {"error": "receipt must be a JSON object"}, text)
            finally:
                os.unlink(path)

    def test_api_raises_value_error(self):
        for text in self.MALFORMED + self.NON_OBJECT:
            path = _write(text)
            try:
                with self.assertRaises(ValueError):
                    load_receipt(path)
                with self.assertRaises(ValueError):
                    summarize(json.loads(text) if text.strip() else None)
                code, out, err = run_cli(path)
                self.assertEqual(code, 1, text)
                self.assertEqual(out, "", text)
            finally:
                os.unlink(path)
        for value in ([], "x", 1, None, True):
            with self.assertRaises(ValueError):
                summarize(value)

    def test_errors_do_not_emit_receipt_contents(self):
        for text in self.MALFORMED + self.NON_OBJECT:
            path = _write(text + SECRET)
            try:
                code, out, err = run_cli(path)
                self.assertEqual(code, 1, text)
                self.assertNotIn(SECRET, out, text)
                self.assertNotIn(SECRET, err, text)
                self.assertNotIn(path, err, text)
                payload = error_of(err)
                self.assertIn(payload["error"], CONCISE_ERRORS, text)
                for token in LEAK_TOKENS:
                    self.assertNotIn(token, err, text)
            finally:
                os.unlink(path)

    def test_missing_file_error_is_concise_and_path_free(self):
        code, out, err = run_cli("definitely-missing-receipt.json")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(error_of(err), {"error": "cannot read receipt"})
        self.assertNotIn("definitely-missing-receipt.json", err)

    def test_valid_object_still_summarizes(self):
        receipt = {
            "schema": "nagi-build-context/1",
            "environment": {"SECRET": "nope"},
            "entries": [
                {"state": "file", "path": "inputs/a.bin"},
                {"state": "directory", "path": "inputs"},
                {"state": "absent", "path": "inputs/../bad.bin"},
                {"state": "absent", "path": "/etc/passwd"},
                {"state": "absent", "identifier": "meson"},
                {"state": "unreadable", "path": "inputs/c.bin"},
            ],
        }
        path = _write(json.dumps(receipt))
        try:
            code, out, err = run_cli(path, base="/server/share/build")
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            report = json.loads(out)
            self.assertEqual(report["schema"], "nagi-build-context/1")
            self.assertEqual(report["complete"], 2)
            self.assertEqual(report["missing"], 3)
            self.assertEqual(report["problem"], 1)
            self.assertEqual(report["missing_inputs"], ["meson"])
            self.assertNotIn("nope", out)
            self.assertNotIn("environment", out)
            self.assertNotIn("passwd", out)
        finally:
            os.unlink(path)

    def test_cli_output_is_deterministic_and_compact(self):
        receipt = {"schema": "nagi-build-context/1",
                   "entries": [{"state": "absent", "path": "inputs/b.bin"},
                               {"state": "absent", "path": "inputs/a.bin"},
                               {"state": "file", "path": "inputs/a.bin"}]}
        path = _write(json.dumps(receipt))
        try:
            first = run_cli(path)[1]
            second = run_cli(path)[1]
            self.assertEqual(first, second)
            self.assertEqual(first, json.dumps(json.loads(first), sort_keys=True,
                                             separators=(",", ":")) + "\n")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
