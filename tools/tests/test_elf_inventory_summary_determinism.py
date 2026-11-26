"""Prove the ELF inventory summary is deterministic and metadata-only."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.firmware.elf_inventory_summary import main, summarize

ROWS = [
    {"source_container": "b.bin", "candidate": "cand-b", "architecture": "x86-64",
     "elf_type": "EXEC", "bounds_valid": True, "ghidra_functions": 3,
     "validated_executable_bytes": 100, "sha256": "A" * 64},
    {"source_container": "a.pup", "candidate": "cand-a2", "architecture": "x86-64",
     "elf_type": "other", "bounds_valid": False, "ghidra_functions": 0,
     "validated_executable_bytes": 50, "sha256": "b" * 64},
    {"source_container": "a.pup", "candidate": "cand-a1", "architecture": "x86-64",
     "elf_type": "other", "bounds_valid": True, "ghidra_functions": 2,
     "validated_executable_bytes": 25, "sha256": "B" * 64},
    {"source_container": "unknown", "candidate": "cand-unknown", "architecture": "arm64",
     "elf_type": "unknown", "bounds_valid": True, "ghidra_functions": 0,
     "validated_executable_bytes": 0, "sha256": "c" * 64},
]
SOURCE_BYTES = json.dumps(ROWS).encode("utf-8")

EXPECTED_LIMITATIONS = [
    "Function counts are reported Ghidra metadata and do not establish analysis completeness.",
    "Valid parser bounds do not establish component identity or executable behavior.",
    "This report reads the JSON inventory only and does not open firmware bytes.",
    "Container names, hashes and counters are metadata; no component identity is inferred.",
]


class TestElfInventorySummaryDeterminism(unittest.TestCase):
    def _render(self, report):
        return json.dumps(report, indent=2, ensure_ascii=False)

    def test_repeat_runs_are_byte_identical(self):
        first = self._render(summarize(ROWS, SOURCE_BYTES))
        second = self._render(summarize(list(ROWS), SOURCE_BYTES))
        self.assertEqual(first, second)

    def test_input_row_order_does_not_change_output(self):
        base = self._render(summarize(ROWS, SOURCE_BYTES))
        for perm in (ROWS[::-1], ROWS[1:] + ROWS[:1], [ROWS[2], ROWS[0], ROWS[3], ROWS[1]]):
            self.assertEqual(base, self._render(summarize(perm, SOURCE_BYTES)),
                             "output must not depend on input row order")

    def test_source_inventory_hash_is_reported(self):
        report = summarize(ROWS, SOURCE_BYTES)
        self.assertEqual(report["source_inventory_sha256"],
                         hashlib.sha256(SOURCE_BYTES).hexdigest())
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["candidate_count"], len(ROWS))

    def test_missing_source_bytes_yield_null_hash(self):
        self.assertIsNone(summarize(ROWS)["source_inventory_sha256"])
        self.assertIsNone(summarize(ROWS, b"")["source_inventory_sha256"])

    def test_hash_change_in_source_is_visible(self):
        changed = SOURCE_BYTES + b" "
        self.assertNotEqual(summarize(ROWS, changed)["source_inventory_sha256"],
                           summarize(ROWS, SOURCE_BYTES)["source_inventory_sha256"])

    def test_duplicate_hashes_sorted_deterministically(self):
        report = summarize(ROWS, SOURCE_BYTES)
        dup = report["duplicate_candidate_hashes"]
        self.assertEqual(dup, [{"sha256": "b" * 64, "candidates": ["cand-a1", "cand-a2"]}])
        self.assertEqual(report["distinct_candidate_hash_count"], 3)

    def test_metadata_only_limitations_are_stated(self):
        report = summarize(ROWS, SOURCE_BYTES)
        self.assertEqual(report["limitations"], EXPECTED_LIMITATIONS)
        self.assertTrue(any("does not open firmware bytes" in text
                            for text in report["limitations"]))

    def test_cli_writes_same_report_as_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            out = Path(tmp) / "summary.json"
            inventory.write_bytes(SOURCE_BYTES)
            stdout = io.StringIO()
            original = __import__("sys").stdout
            __import__("sys").stdout = stdout
            try:
                self.assertEqual(main([str(inventory)]), 0)
            finally:
                __import__("sys").stdout = original
            self.assertEqual(main([str(inventory), "--out", str(out)]), 0)
            self.assertEqual(out.read_text(encoding="utf-8"), stdout.getvalue())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")),
                             summarize(json.loads(SOURCE_BYTES.decode("utf-8")), SOURCE_BYTES))

    def test_shipped_summary_matches_utility_limitations(self):
        shipped = Path("PS5_ELF_INVENTORY_SUMMARY.json")
        if not shipped.exists():
            self.skipTest("shipped summary not available in this workspace")
            return
        data = json.loads(shipped.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["limitations"], EXPECTED_LIMITATIONS)
        self.assertEqual(len(data["source_inventory_sha256"]), 64)
        self.assertEqual(data["candidate_count"],
                         sum(group["candidate_count"] for group in data["by_source_container"].values()))

    def test_invalid_inventory_rejected(self):
        with self.assertRaises(ValueError):
            summarize({"not": "a list"})
        with self.assertRaises(ValueError):
            summarize(["not an object"])


if __name__ == "__main__":
    unittest.main()
