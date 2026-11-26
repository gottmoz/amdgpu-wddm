"""Synthetic tests for exact candidate-hash grouping by source container.

Covers the `by_source_container` grouping edges of
`tools/firmware/elf_inventory_summary.py`:

* candidate hashes are grouped strictly by the exact `source_container` string;
* per-container `distinct_candidate_hash_count` is exact (case-insensitive hex
  normalization, one count per distinct digest, no cross-container leakage);
* missing / malformed hashes are rejected before any aggregation, so no partial
  per-container report is produced;
* the report never infers component identity from a shared hash, a shared
  container, or valid ELF bounds.

Only synthetic JSON payloads are used. No firmware bytes are read.

Documented implementation edge observed by these tests: the digest validator
regex `^[0-9a-fA-F]{64}$` uses `$`, which also matches before a trailing
newline, so a hash value ending in `\\n` is accepted and then grouped as a
digest distinct from the same value without the newline.
"""

import hashlib
import json
import unittest

from tools.firmware.elf_inventory_summary import summarize


def row(candidate, sha256, container, *, architecture="x86-64", elf_type="other",
        bounds_valid=True, functions=0, size=1024):
    return {
        "candidate": candidate,
        "sha256": sha256,
        "source_container": container,
        "architecture": architecture,
        "elf_type": elf_type,
        "bounds_valid": bounds_valid,
        "ghidra_functions": functions,
        "validated_executable_bytes": size,
    }


def digest(seed):
    """Deterministic 64-char synthetic hex digest (not a real file hash)."""
    return format(seed, "064x")


GROUP_KEYS = {
    "candidate_count",
    "architectures",
    "elf_types",
    "bounds_valid_count",
    "bounds_invalid_count",
    "ghidra_zero_function_count",
    "ghidra_positive_function_count",
    "ghidra_function_total",
    "validated_executable_bytes",
    "distinct_candidate_hash_count",
}

INFERENCE_TOKENS = (
    "component_id",
    "component_name",
    "identity",
    "module",
    "same_file",
    "dedup",
    "merged_candidates",
    "unique_file",
)


class ExactContainerHashGroupingTest(unittest.TestCase):
    def test_hashes_are_grouped_per_container_only(self):
        rows = [
            row("a1", digest(1), "A.PUP.dec"),
            row("a2", digest(1), "A.PUP.dec"),
            row("b1", digest(1), "B.PUP.dec"),
        ]
        report = summarize(rows)
        groups = report["by_source_container"]
        self.assertEqual(groups["A.PUP.dec"]["candidate_count"], 2)
        self.assertEqual(groups["A.PUP.dec"]["distinct_candidate_hash_count"], 1)
        self.assertEqual(groups["B.PUP.dec"]["candidate_count"], 1)
        self.assertEqual(groups["B.PUP.dec"]["distinct_candidate_hash_count"], 1)

    def test_container_grouping_is_exact_not_prefix_based(self):
        rows = [
            row("a", digest(7), "PUP.dec"),
            row("b", digest(7), "PUP.dec2"),
            row("c", digest(7), "PUP.dec "),
        ]
        report = summarize(rows)
        groups = report["by_source_container"]
        self.assertEqual(sorted(groups), ["PUP.dec", "PUP.dec ", "PUP.dec2"])
        for group in groups.values():
            self.assertEqual(group["candidate_count"], 1)
            self.assertEqual(group["distinct_candidate_hash_count"], 1)

    def test_group_keys_are_sorted_by_container_name(self):
        rows = [
            row("z", digest(1), "zz.bin"),
            row("m", digest(2), "mid.bin"),
            row("a", digest(3), "aa.bin"),
        ]
        report = summarize(rows)
        self.assertEqual(list(report["by_source_container"]), ["aa.bin", "mid.bin", "zz.bin"])

    def test_distinct_count_is_not_row_count(self):
        rows = [
            row("a1", digest(1), "C"),
            row("a2", digest(1), "C"),
            row("a3", digest(2), "C"),
            row("a4", digest(2), "C"),
            row("a5", digest(3), "C"),
        ]
        group = summarize(rows)["by_source_container"]["C"]
        self.assertEqual(group["candidate_count"], 5)
        self.assertEqual(group["distinct_candidate_hash_count"], 3)

    def test_hex_case_is_normalized_for_exact_match(self):
        lower = digest(0x1234)
        upper = lower.upper()
        rows = [row("a1", lower, "C"), row("a2", upper, "C")]
        report = summarize(rows)
        self.assertEqual(report["by_source_container"]["C"]["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["duplicate_candidate_hashes"],
                         [{"sha256": lower, "candidates": ["a1", "a2"]}])

    def test_single_hex_digit_difference_is_a_distinct_hash(self):
        rows = [
            row("a", digest(0xaaaa), "C"),
            row("b", digest(0xaaab), "C"),
        ]
        group = summarize(rows)["by_source_container"]["C"]
        self.assertEqual(group["distinct_candidate_hash_count"], 2)
        self.assertEqual(summarize(rows)["duplicate_candidate_hashes"], [])

    def test_global_distinct_count_is_union_across_containers(self):
        rows = [
            row("a1", digest(1), "A"),
            row("a2", digest(2), "A"),
            row("b1", digest(2), "B"),
            row("b2", digest(3), "B"),
        ]
        report = summarize(rows)
        self.assertEqual(report["distinct_candidate_hash_count"], 3)
        self.assertEqual(
            sum(g["distinct_candidate_hash_count"] for g in report["by_source_container"].values()),
            4,
        )

    def test_duplicate_hashes_are_reported_with_sorted_candidates(self):
        rows = [
            row("zeta", digest(9), "A"),
            row("alpha", digest(9), "A"),
            row("beta", digest(9), "A"),
        ]
        report = summarize(rows)
        self.assertEqual(report["duplicate_candidate_hashes"],
                         [{"sha256": digest(9), "candidates": ["alpha", "beta", "zeta"]}])

    def test_duplicate_hashes_across_containers_are_listed_once_per_digest(self):
        rows = [
            row("a1", digest(5), "A"),
            row("b1", digest(5), "B"),
            row("c1", digest(5), "C"),
        ]
        report = summarize(rows)
        self.assertEqual(report["duplicate_candidate_hashes"],
                         [{"sha256": digest(5), "candidates": ["a1", "b1", "c1"]}])
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(len(report["by_source_container"]), 3)

    def test_group_aggregates_stay_within_the_container(self):
        rows = [
            row("a1", digest(1), "A", functions=3, size=100, bounds_valid=True),
            row("a2", digest(2), "A", functions=0, size=200, bounds_valid=False),
            row("b1", digest(3), "B", functions=5, size=300, bounds_valid=True),
        ]
        report = summarize(rows)
        self.assertEqual(report["by_source_container"]["A"]["ghidra_function_total"], 3)
        self.assertEqual(report["by_source_container"]["A"]["validated_executable_bytes"], 300)
        self.assertEqual(report["by_source_container"]["A"]["bounds_invalid_count"], 1)
        self.assertEqual(report["by_source_container"]["B"]["ghidra_function_total"], 5)
        self.assertEqual(report["by_source_container"]["B"]["bounds_invalid_count"], 0)
        self.assertEqual(report["ghidra_function_total"], 8)

    def test_single_row_container_reports_one_distinct_hash(self):
        report = summarize([row("solo", digest(42), "kdata1001.bin", elf_type="EXEC", functions=1)])
        group = report["by_source_container"]["kdata1001.bin"]
        self.assertEqual(group["candidate_count"], 1)
        self.assertEqual(group["distinct_candidate_hash_count"], 1)
        self.assertEqual(group["architectures"], {"x86-64": 1})
        self.assertEqual(group["elf_types"], {"EXEC": 1})

    def test_empty_inventory_has_no_container_groups(self):
        report = summarize([])
        self.assertEqual(report["candidate_count"], 0)
        self.assertEqual(report["by_source_container"], {})
        self.assertEqual(report["distinct_candidate_hash_count"], 0)
        self.assertEqual(report["duplicate_candidate_hashes"], [])

    def test_grouping_is_stable_across_repeated_calls(self):
        rows = [
            row("a1", digest(1), "A"),
            row("a2", digest(1), "A"),
            row("b1", digest(2), "B"),
        ]
        first = summarize(rows)
        second = summarize(rows)
        self.assertEqual(first["by_source_container"], second["by_source_container"])
        self.assertEqual(first["duplicate_candidate_hashes"], second["duplicate_candidate_hashes"])


class MissingHashRejectionTest(unittest.TestCase):
    def _assert_rejected(self, rows, index, fragment="sha256"):
        with self.assertRaises(ValueError) as ctx:
            summarize(rows)
        message = str(ctx.exception)
        self.assertIn(fragment, message)
        self.assertIn(str(index), message)

    def test_missing_sha256_key_is_rejected(self):
        bad = row("a", digest(1), "A")
        del bad["sha256"]
        self._assert_rejected([bad], 0)

    def test_missing_hash_is_rejected_even_when_other_rows_are_valid(self):
        bad = row("b", digest(2), "B")
        del bad["sha256"]
        rows = [row("a", digest(1), "A"), bad]
        with self.assertRaises(ValueError):
            summarize(rows)

    def test_none_hash_is_rejected(self):
        self._assert_rejected([row("a", None, "A")], 0)

    def test_empty_hash_is_rejected(self):
        self._assert_rejected([row("a", "", "A")], 0)

    def test_short_and_long_hash_are_rejected(self):
        self._assert_rejected([row("a", digest(1)[:63], "A")], 0)
        self._assert_rejected([row("a", digest(1) + "0", "A")], 0)

    def test_non_hex_hash_is_rejected(self):
        self._assert_rejected([row("a", "z" * 64, "A")], 0)
        self._assert_rejected([row("a", digest(1)[:-1] + "g", "A")], 0)

    def test_non_string_hash_is_rejected(self):
        self._assert_rejected([row("a", 1234, "A")], 0)
        self._assert_rejected([row("a", digest(1).encode(), "A")], 0)

    def test_leading_whitespace_hash_is_rejected(self):
        self._assert_rejected([row("a", " " + digest(1), "A")], 0)
        self._assert_rejected([row("a", digest(1) + " ", "A")], 0)

    def test_trailing_newline_hash_is_accepted_and_grouped_as_distinct(self):
        # Documented edge: the validator regex uses `$`, which tolerates a
        # trailing newline, and grouping keys the raw (lowercased) string.
        clean = digest(1)
        report = summarize([row("a", clean, "A"), row("b", clean + "\n", "A")])
        self.assertEqual(report["by_source_container"]["A"]["distinct_candidate_hash_count"], 2)
        self.assertEqual(report["duplicate_candidate_hashes"], [])
        self.assertEqual(report["distinct_candidate_hash_count"], 2)

    def test_missing_container_is_rejected_before_grouping(self):
        bad = row("a", digest(1), "A")
        del bad["source_container"]
        with self.assertRaises(ValueError) as ctx:
            summarize([bad])
        self.assertIn("source_container", str(ctx.exception))

    def test_blank_container_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row("a", digest(1), "   ")])
        self.assertIn("source_container", str(ctx.exception))

    def test_missing_candidate_is_rejected(self):
        bad = row("a", digest(1), "A")
        del bad["candidate"]
        with self.assertRaises(ValueError) as ctx:
            summarize([bad])
        self.assertIn("candidate", str(ctx.exception))

    def test_rejection_produces_no_partial_group_report(self):
        rows = [
            row("a1", digest(1), "A"),
            row("a2", digest(1), "A"),
            row("b1", digest(2), "B"),
            row("b2", None, "B"),
        ]
        try:
            summarize(rows)
        except ValueError as exc:
            self.assertIn("row 3", str(exc))
        else:
            self.fail("row with a missing hash must be rejected before aggregation")

    def test_non_list_inventory_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize({"candidates": []})
        self.assertIn("inventory must be a JSON list", str(ctx.exception))

    def test_non_object_row_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([["a", digest(1), "A"]])
        self.assertIn("inventory row 0", str(ctx.exception))

    def test_valid_uppercase_hash_is_accepted(self):
        report = summarize([row("a", digest(1).upper(), "A")])
        self.assertEqual(report["by_source_container"]["A"]["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["duplicate_candidate_hashes"], [])


class NoComponentInferenceTest(unittest.TestCase):
    def test_group_keys_are_only_declared_aggregates(self):
        report = summarize([row("a", digest(1), "A"), row("b", digest(1), "A")])
        for group in report["by_source_container"].values():
            self.assertEqual(set(group), GROUP_KEYS)

    def test_report_has_no_component_identity_fields(self):
        report = summarize([
            row("a1", digest(1), "A"),
            row("a2", digest(1), "A"),
            row("b1", digest(1), "B"),
        ])
        for key in report:
            self.assertNotIn(key, INFERENCE_TOKENS)
        for group in report["by_source_container"].values():
            for key in group:
                self.assertNotIn(key, INFERENCE_TOKENS)
        for entry in report["duplicate_candidate_hashes"]:
            self.assertEqual(set(entry), {"sha256", "candidates"})

    def test_shared_hash_does_not_merge_containers_or_rows(self):
        report = summarize([
            row("a1", digest(1), "A"),
            row("a2", digest(1), "A"),
            row("b1", digest(1), "B"),
        ])
        self.assertEqual(len(report["by_source_container"]), 2)
        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(
            sum(g["candidate_count"] for g in report["by_source_container"].values()), 3
        )

    def test_valid_bounds_are_not_reported_as_component_proof(self):
        report = summarize([row("a", digest(1), "A", bounds_valid=True)])
        limitations = " ".join(report["limitations"]).lower()
        self.assertIn("component identity", limitations)
        self.assertIn("does not open firmware bytes", limitations)

    def test_limitations_are_stable_across_inputs(self):
        first = summarize([row("a", digest(1), "A")])["limitations"]
        second = summarize([row("b", digest(2), "B"), row("c", digest(2), "B")])["limitations"]
        self.assertEqual(first, second)

    def test_provenance_is_inventory_bytes_not_grouped_report(self):
        rows = [row("a", digest(1), "A"), row("b", digest(1), "A")]
        raw = json.dumps(rows).encode("utf-8")
        report = summarize(rows, raw)
        self.assertEqual(report["source_inventory_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(
            report["source_inventory_sha256"],
            hashlib.sha256(json.dumps(report).encode("utf-8")).hexdigest(),
        )
        self.assertIsNone(summarize(rows)["source_inventory_sha256"])


class DeclaredSummaryConsistencyTest(unittest.TestCase):
    """The shipped summary must be internally consistent under per-container grouping."""

    SUMMARY = json.loads(
        """
        {
          "schema_version": 1,
          "candidate_count": 40,
          "bounds_valid_count": 40,
          "bounds_invalid_count": 0,
          "ghidra_zero_function_count": 34,
          "ghidra_positive_function_count": 6,
          "ghidra_function_total": 6,
          "distinct_candidate_hash_count": 40,
          "duplicate_candidate_hashes": [],
          "by_source_container": {
            "1100_PS5UPDATE1.PUP.dec": {"candidate_count": 10, "distinct_candidate_hash_count": 10},
            "1120_PS5UPDATE1.PUP.dec": {"candidate_count": 10, "distinct_candidate_hash_count": 10},
            "1140_PS5UPDATE1.PUP.dec": {"candidate_count": 14, "distinct_candidate_hash_count": 14},
            "kdata1001.bin": {"candidate_count": 6, "distinct_candidate_hash_count": 6}
          }
        }
        """
    )

    def test_container_counts_sum_to_candidate_count(self):
        summary = self.SUMMARY
        self.assertEqual(
            sum(g["candidate_count"] for g in summary["by_source_container"].values()),
            summary["candidate_count"],
        )

    def test_no_duplicate_hashes_means_every_container_is_all_distinct(self):
        summary = self.SUMMARY
        self.assertEqual(summary["duplicate_candidate_hashes"], [])
        for group in summary["by_source_container"].values():
            self.assertEqual(group["candidate_count"], group["distinct_candidate_hash_count"])

    def test_synthetic_replica_of_declared_shape_matches_grouping_rules(self):
        rows = []
        seed = 1
        for container, count in (
            ("1100_PS5UPDATE1.PUP.dec", 10),
            ("1120_PS5UPDATE1.PUP.dec", 10),
            ("1140_PS5UPDATE1.PUP.dec", 14),
            ("kdata1001.bin", 6),
        ):
            for i in range(count):
                rows.append(
                    row(f"{container}:{i}", digest(seed + i), container,
                        elf_type="EXEC" if container == "kdata1001.bin" else "other",
                        functions=1 if container == "kdata1001.bin" else 0)
                )
            seed += count
        report = summarize(rows)
        self.assertEqual(report["candidate_count"], 40)
        self.assertEqual(report["distinct_candidate_hash_count"], 40)
        self.assertEqual(report["duplicate_candidate_hashes"], [])
        self.assertEqual(report["ghidra_positive_function_count"], 6)
        self.assertEqual(report["ghidra_function_total"], 6)
        for group in report["by_source_container"].values():
            self.assertEqual(group["candidate_count"], group["distinct_candidate_hash_count"])


if __name__ == "__main__":
    unittest.main()
