"""End-to-end CLI regression tests for tools/firmware/elf_inventory_summary.py.

Covers: JSON inventory in -> JSON report out, source hash emission, duplicate
hash reporting, --out redirection, malformed input handling, and clean cleanup
of the temporary fixture directory.
"""

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.firmware.elf_inventory_summary import main, summarize

ROWS = [
    {
        "source_container": "A.pup.dec",
        "candidate": "elf_a",
        "architecture": "x86_64",
        "elf_type": "ELF64",
        "bounds_valid": True,
        "ghidra_functions": 3,
        "validated_executable_bytes": 100,
        "sha256": "aa" * 32,
    },
    {
        "source_container": "A.pup.dec",
        "candidate": "elf_b",
        "architecture": "arm64",
        "elf_type": "ELF64",
        "bounds_valid": False,
        "ghidra_functions": 0,
        "validated_executable_bytes": 50,
        "sha256": "AA" * 32,
    },
    {
        "source_container": "B.pup.dec",
        "candidate": "elf_c",
        "architecture": "arm64",
        "elf_type": "ELF32",
        "bounds_valid": True,
        "ghidra_functions": 7,
        "validated_executable_bytes": 25,
        "sha256": "bb" * 32,
    },
    {"source_container": "B.pup.dec", "candidate": "elf_d", "bounds_valid": None},
]


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class Ps5SummaryCliTest(unittest.TestCase):
    def test_cli_emits_report_and_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            path.write_bytes(json.dumps(ROWS).encode("utf-8"))
            raw = path.read_bytes()
            code, rendered = run_cli([str(path)])
            self.assertEqual(code, 0)
            self.assertTrue(rendered.endswith("\n"))
            report = json.loads(rendered)

            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["source_inventory_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report["candidate_count"], 4)
            self.assertEqual(report["bounds_valid_count"], 2)
            self.assertEqual(report["bounds_invalid_count"], 1)
            self.assertEqual(report["ghidra_zero_function_count"], 1)
            self.assertEqual(report["ghidra_positive_function_count"], 2)
            self.assertEqual(report["ghidra_function_total"], 10)
            self.assertEqual(report["distinct_candidate_hash_count"], 2)
            self.assertEqual(
                report["duplicate_candidate_hashes"],
                [{"sha256": "aa" * 32, "candidates": ["elf_a", "elf_b"]}],
            )
            self.assertEqual(sorted(report["by_source_container"]), ["A.pup.dec", "B.pup.dec"])
            self.assertEqual(report["by_source_container"]["A.pup.dec"]["candidate_count"], 2)
            self.assertEqual(
                report["by_source_container"]["A.pup.dec"]["architectures"],
                {"arm64": 1, "x86_64": 1},
            )
            self.assertEqual(len(report["limitations"]), 3)
        self.assertFalse(path.exists())

    def test_cli_out_file_is_deterministic_and_bom_tolerant(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            out = Path(tmp) / "report.json"
            path.write_bytes(json.dumps(ROWS).encode("utf-8-sig"))
            code, rendered = run_cli([str(path), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(rendered, "")
            first = out.read_text(encoding="utf-8")
            self.assertEqual(run_cli([str(path), "--out", str(out)])[0], 0)
            self.assertEqual(out.read_text(encoding="utf-8"), first)
            report = json.loads(first)
            # Hash is over the exact bytes on disk, BOM included.
            self.assertEqual(
                report["source_inventory_sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        self.assertFalse(path.exists())
        self.assertFalse(out.exists())

    def test_empty_inventory_still_hashes_its_source_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            path.write_text("[]", encoding="utf-8")
            code, rendered = run_cli([str(path)])
            self.assertEqual(code, 0)
            report = json.loads(rendered)
            self.assertEqual(
                report["source_inventory_sha256"], hashlib.sha256(b"[]").hexdigest()
            )
            self.assertEqual(report["candidate_count"], 0)
            self.assertEqual(report["by_source_container"], {})
            self.assertEqual(report["duplicate_candidate_hashes"], [])
        self.assertFalse(path.exists())

    def test_invalid_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            for payload in ("{not json}", '{"candidate": "elf"}', '["not-an-object"]'):
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises((json.JSONDecodeError, ValueError)):
                    run_cli([str(path)])
        self.assertFalse(path.exists())

    def test_missing_fixture_raises_clean_oserror(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            with self.assertRaises(OSError):
                run_cli([str(missing)])
        self.assertFalse(missing.exists())

    def test_summarize_is_pure_and_matches_cli(self):
        payload = json.dumps(ROWS).encode("utf-8")
        direct = summarize(json.loads(payload.decode("utf-8")), payload)
        self.assertEqual(direct["source_inventory_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(direct, json.loads(json.dumps(direct)))
        # No source bytes -> no source hash is emitted.
        self.assertIsNone(summarize(ROWS, b"")["source_inventory_sha256"])
        with self.assertRaises(ValueError):
            summarize({"rows": []})


if __name__ == "__main__":
    unittest.main()
