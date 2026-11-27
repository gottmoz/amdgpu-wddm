import unittest

from tools.firmware.elf_inventory_summary import render_markdown, summarize


class ElfInventorySummaryTests(unittest.TestCase):
    def test_groups_metadata_and_duplicate_hashes(self):
        report = summarize([
            {"candidate": "pup-a", "source_container": "update.pup", "architecture": "x86-64",
             "elf_type": "other", "bounds_valid": True, "ghidra_functions": 0,
             "validated_executable_bytes": 100, "sha256": "a" * 64},
            {"candidate": "pup-b", "source_container": "update.pup", "architecture": "x86-64",
             "elf_type": "other", "bounds_valid": True, "ghidra_functions": 0,
             "validated_executable_bytes": 50, "sha256": "A" * 64},
            {"candidate": "kdata-a", "source_container": "kdata.bin", "architecture": "x86-64",
             "elf_type": "EXEC", "bounds_valid": False, "ghidra_functions": 2,
             "validated_executable_bytes": 20, "sha256": "b" * 64},
        ], b"fixture")

        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["bounds_invalid_count"], 1)
        self.assertEqual(report["ghidra_function_total"], 2)
        self.assertEqual(report["distinct_candidate_hash_count"], 2)
        self.assertEqual(report["duplicate_candidate_hashes"], [{"sha256": "a" * 64, "candidates": ["pup-a", "pup-b"]}])
        self.assertEqual(report["by_source_container"]["update.pup"]["validated_executable_bytes"], 150)
        self.assertIn("do not establish analysis completeness", report["limitations"][0])

    def test_rejects_invalid_inventory_shape(self):
        with self.assertRaisesRegex(ValueError, "JSON list"):
            summarize({"rows": []})
        with self.assertRaisesRegex(ValueError, "row 0"):
            summarize([None])

    def test_renderer_rejects_newline_suffixed_report_hashes(self):
        duplicate_rows = [
            {"candidate": name, "source_container": "update.pup", "architecture": "x86-64",
             "elf_type": "other", "bounds_valid": True, "ghidra_functions": 0,
             "validated_executable_bytes": 100, "sha256": "a" * 64}
            for name in ("pup-a", "pup-b")
        ]
        valid = summarize(duplicate_rows, b"inventory")
        bad_reports = []

        bad_source_hash = dict(valid)
        bad_source_hash["source_inventory_sha256"] += "\n"
        bad_reports.append(bad_source_hash)

        bad_duplicate_hash = dict(valid)
        bad_duplicate_hash["duplicate_candidate_hashes"] = [
            dict(valid["duplicate_candidate_hashes"][0], sha256="a" * 64 + "\n")
        ]
        bad_reports.append(bad_duplicate_hash)

        for report in bad_reports:
            with self.subTest(field="source_inventory_sha256" if report is bad_source_hash else "duplicate sha256"):
                with self.assertRaisesRegex(ValueError, "64-character hex string"):
                    render_markdown(report)


if __name__ == "__main__":
    unittest.main()
