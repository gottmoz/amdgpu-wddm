"""Regression coverage for SHA-256 case folding and hash-less candidates.

Focus:
  1. `summarize()` must treat SHA-256 digests case-insensitively when counting
     distinct hashes and when reporting duplicate-hash candidate groups.
  2. Candidates that omit a hash (missing key, None, empty string, wrong type)
     must be rejected before any aggregation is attempted.

All fixtures are synthetic metadata dicts. No firmware bytes are read.
"""

import unittest

from tools.firmware.elf_inventory_summary import summarize


DIGEST = "a1b2c3d4e5f60123456789abcdefabcdefabcdefabcdefabcdefabcdefabcd12"
UPPER_DIGEST = DIGEST.upper()
MIXED_DIGEST = "A1B2c3D4e5F60123456789abcdefabcdefabcdefabcdefabcdefabcdefabcd12"
OTHER_DIGEST = "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f"


def row(candidate, sha256, container="sysconf", architecture="x86_64",
        elf_type="ELF64", bounds_valid=True, ghidra_functions=3,
        validated_executable_bytes=1024):
    """Build one synthetic inventory row (metadata only, no firmware bytes)."""
    return {
        "candidate": candidate,
        "sha256": sha256,
        "source_container": container,
        "architecture": architecture,
        "elf_type": elf_type,
        "bounds_valid": bounds_valid,
        "ghidra_functions": ghidra_functions,
        "validated_executable_bytes": validated_executable_bytes,
    }


class HashCaseGroupingTest(unittest.TestCase):
    def test_mixed_case_digests_count_as_one_distinct_hash(self):
        rows = [
            row("candidate-a", DIGEST),
            row("candidate-b", UPPER_DIGEST),
            row("candidate-c", MIXED_DIGEST),
        ]
        report = summarize(rows)
        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["distinct_candidate_hash_count"], 1)

    def test_duplicate_group_lists_all_candidates_with_normalized_digest(self):
        rows = [
            row("candidate-z", UPPER_DIGEST),
            row("candidate-a", DIGEST),
            row("candidate-m", MIXED_DIGEST),
        ]
        report = summarize(rows)
        duplicates = report["duplicate_candidate_hashes"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["sha256"], DIGEST)
        self.assertEqual(duplicates[0]["candidates"],
                         ["candidate-a", "candidate-m", "candidate-z"])

    def test_single_candidate_mixed_case_hash_is_not_a_duplicate(self):
        report = summarize([row("candidate-a", MIXED_DIGEST)])
        self.assertEqual(report["duplicate_candidate_hashes"], [])
        self.assertEqual(report["distinct_candidate_hash_count"], 1)

    def test_case_insensitive_grouping_is_per_container_too(self):
        rows = [
            row("a1", DIGEST, container="sysconf"),
            row("a2", UPPER_DIGEST, container="sysconf"),
            row("b1", MIXED_DIGEST, container="boot"),
        ]
        report = summarize(rows)
        by_container = report["by_source_container"]
        self.assertEqual(by_container["sysconf"]["distinct_candidate_hash_count"], 1)
        self.assertEqual(by_container["sysconf"]["candidate_count"], 2)
        self.assertEqual(by_container["boot"]["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(len(report["duplicate_candidate_hashes"]), 1)
        self.assertEqual(report["duplicate_candidate_hashes"][0]["candidates"],
                         ["a1", "a2", "b1"])

    def test_distinct_digests_are_not_folded_together(self):
        rows = [row("a", DIGEST), row("b", OTHER_DIGEST)]
        report = summarize(rows)
        self.assertEqual(report["distinct_candidate_hash_count"], 2)
        self.assertEqual(report["duplicate_candidate_hashes"], [])

    def test_duplicate_groups_are_sorted_by_normalized_digest(self):
        rows = [
            row("late", OTHER_DIGEST),
            row("late2", OTHER_DIGEST.upper()),
            row("early", DIGEST),
            row("early2", MIXED_DIGEST),
        ]
        report = summarize(rows)
        digests = [entry["sha256"] for entry in report["duplicate_candidate_hashes"]]
        self.assertEqual(digests, sorted(digests))
        self.assertEqual(digests, [OTHER_DIGEST, DIGEST])

    def test_candidate_names_are_not_case_folded(self):
        rows = [row("Candidate-A", DIGEST), row("candidate-a", UPPER_DIGEST)]
        report = summarize(rows)
        self.assertEqual(report["duplicate_candidate_hashes"][0]["candidates"],
                         ["Candidate-A", "candidate-a"])

    def test_counters_are_unaffected_by_hash_case(self):
        rows = [
            row("a", DIGEST, bounds_valid=True, ghidra_functions=0,
                validated_executable_bytes=100),
            row("b", UPPER_DIGEST, bounds_valid=False, ghidra_functions=5,
                validated_executable_bytes=200),
        ]
        report = summarize(rows)
        self.assertEqual(report["bounds_valid_count"], 1)
        self.assertEqual(report["bounds_invalid_count"], 1)
        self.assertEqual(report["ghidra_zero_function_count"], 1)
        self.assertEqual(report["ghidra_positive_function_count"], 1)
        self.assertEqual(report["ghidra_function_total"], 5)
        self.assertEqual(report["by_source_container"]["sysconf"]["validated_executable_bytes"], 300)

    def test_source_inventory_sha256_is_reported_when_bytes_supplied(self):
        report = summarize([row("a", MIXED_DIGEST)], source_bytes=b"synthetic-inventory")
        self.assertEqual(len(report["source_inventory_sha256"]), 64)
        self.assertEqual(report["source_inventory_sha256"].lower(),
                         report["source_inventory_sha256"])
        self.assertIsNone(summarize([row("a", DIGEST)])["source_inventory_sha256"])


class MissingHashTest(unittest.TestCase):
    def test_missing_sha256_key_is_rejected(self):
        bad = row("candidate-a", DIGEST)
        del bad["sha256"]
        with self.assertRaises(ValueError) as ctx:
            summarize([bad])
        message = str(ctx.exception)
        self.assertIn("inventory row 0", message)
        self.assertIn("sha256", message)

    def test_none_sha256_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row("candidate-a", None)])
        self.assertIn("inventory row 0 field 'sha256'", str(ctx.exception))

    def test_empty_sha256_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row("candidate-a", "")])
        self.assertIn("64-character hex string", str(ctx.exception))

    def test_short_and_non_hex_sha256_are_rejected(self):
        for digest in (DIGEST[:63], "z" * 64, DIGEST + "0"):
            with self.assertRaises(ValueError):
                summarize([row("candidate-a", digest)])

    def test_non_string_sha256_is_rejected(self):
        for digest in (1234, 1, True, [DIGEST], DIGEST.encode()):
            with self.assertRaises(ValueError):
                summarize([row("candidate-a", digest)])

    def test_omitted_hash_row_is_reported_with_its_own_index(self):
        rows = [row("ok", DIGEST), row("no-hash", None), row("also-ok", OTHER_DIGEST)]
        with self.assertRaises(ValueError) as ctx:
            summarize(rows)
        self.assertIn("inventory row 1", str(ctx.exception))

    def test_rejection_happens_before_any_aggregation(self):
        rows = [row("ok", DIGEST), row("no-hash", "")]
        original = [dict(r) for r in rows]
        with self.assertRaises(ValueError):
            summarize(rows)
        self.assertEqual(rows, original)

    def test_valid_mixed_case_inventory_still_summarizes_after_rejection(self):
        rows = [row("a", MIXED_DIGEST), row("b", UPPER_DIGEST)]
        with self.assertRaises(ValueError):
            summarize(rows + [row("c", None)])
        report = summarize(rows)
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["duplicate_candidate_hashes"][0]["candidates"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
