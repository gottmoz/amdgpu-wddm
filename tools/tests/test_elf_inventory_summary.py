import unittest

from tools.firmware.elf_inventory_summary import summarize


class ElfInventorySummaryTests(unittest.TestCase):
    def test_groups_metadata_and_duplicate_hashes(self):
        report = summarize([
            {"candidate": "pup-a", "source_container": "update.pup", "architecture": "x86-64",
             "elf_type": "other", "bounds_valid": True, "ghidra_functions": 0,
             "validated_executable_bytes": 100, "sha256": "aa"},
            {"candidate": "pup-b", "source_container": "update.pup", "architecture": "x86-64",
             "elf_type": "other", "bounds_valid": True, "ghidra_functions": 0,
             "validated_executable_bytes": 50, "sha256": "AA"},
            {"candidate": "kdata-a", "source_container": "kdata.bin", "architecture": "x86-64",
             "elf_type": "EXEC", "bounds_valid": False, "ghidra_functions": 2,
             "validated_executable_bytes": 20, "sha256": "bb"},
        ], b"fixture")

        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["bounds_invalid_count"], 1)
        self.assertEqual(report["ghidra_function_total"], 2)
        self.assertEqual(report["distinct_candidate_hash_count"], 2)
        self.assertEqual(report["duplicate_candidate_hashes"], [{"sha256": "aa", "candidates": ["pup-a", "pup-b"]}])
        self.assertEqual(report["by_source_container"]["update.pup"]["validated_executable_bytes"], 150)
        self.assertIn("do not establish analysis completeness", report["limitations"][0])

    def test_rejects_invalid_inventory_shape(self):
        with self.assertRaisesRegex(ValueError, "JSON list"):
            summarize({"rows": []})
        with self.assertRaisesRegex(ValueError, "row 0"):
            summarize([None])


if __name__ == "__main__":
    unittest.main()
