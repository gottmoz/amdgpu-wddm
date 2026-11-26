"""Synthetic regression tests for cross-version candidate hash comparison.

Scope and constraints:
- All payloads are constructed in memory; no firmware bytes are read or hashed.
- The declared summary metadata (PS5_ELF_INVENTORY_SUMMARY.json) carries only
  per-container *counts*, not per-candidate digests. Exact-match cross-version
  grouping therefore needs synthetic inventories; the tests below pin both the
  count-level behaviour of ``elf_inventory_summary.summarize`` and the exact
  digest-set behaviour of the local comparison helpers.
- "Exact match" means byte-identical SHA-256 after ASCII case normalisation.
  Near-misses (one differing hex digit) are never grouped.
- Missing digests are rejected before any grouping is attempted.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import defaultdict
from pathlib import Path

from tools.firmware.elf_inventory_summary import summarize


SUMMARY_PATH = Path(__file__).resolve().parents[2] / "PS5_ELF_INVENTORY_SUMMARY.json"

V1100 = "1100_PS5UPDATE1.PUP.dec"
V1120 = "1120_PS5UPDATE1.PUP.dec"
V1140 = "1140_PS5UPDATE1.PUP.dec"
KDATA = "kdata1001.bin"

# Embedded copy of the declared summary's container counters. Used as a
# deterministic fixture when the JSON file is not reachable from the test cwd.
DECLARED_CONTAINER_COUNTS = {
    V1100: {"candidate_count": 10, "distinct_candidate_hash_count": 10},
    V1120: {"candidate_count": 10, "distinct_candidate_hash_count": 10},
    V1140: {"candidate_count": 14, "distinct_candidate_hash_count": 14},
    KDATA: {"candidate_count": 6, "distinct_candidate_hash_count": 6},
}


class MissingDigestError(ValueError):
    """Raised when a cross-version comparison cannot be made exactly."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row(candidate, sha256, container, functions=0, size=0, elf_type="other",
         bounds_valid=True, architecture="x86-64"):
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


def _flip_last_char(digest: str) -> str:
    return digest[:-1] + ("0" if digest[-1] != "0" else "1")


def _load_declared_summary():
    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": 1,
            "source_inventory_sha256": None,
            "candidate_count": 40,
            "by_source_container": {
                container: dict(counts) for container, counts in DECLARED_CONTAINER_COUNTS.items()
            },
            "duplicate_candidate_hashes": [],
        }


def _synthetic_inventory():
    """Three 'versions' with deliberate overlap, duplicates and a near-miss."""
    a = _digest("candidate-a")
    b = _digest("candidate-b")
    c = _digest("candidate-c")
    d = _digest("candidate-d")
    e = _digest("candidate-e")
    near_miss_a = _flip_last_char(a)

    rows = [
        _row("1100-elf-1", a, V1100),
        _row("1100-elf-2", b, V1100),
        _row("1100-elf-3", c, V1100),
        _row("1120-elf-1", a, V1120),
        _row("1120-elf-2", b, V1120),
        _row("1120-elf-3", d, V1120),
        # Same digest as "1100-elf-1" written in upper case: exact match.
        _row("1140-elf-1", a.upper(), V1140),
        # Same digest as "1120-elf-3": cross-container duplicate.
        _row("1140-elf-2", d, V1140),
        _row("1140-elf-3", e, V1140),
        # One hex digit away from "a": must never group with it.
        _row("1140-elf-4", near_miss_a, V1140),
        _row("kdata-1", _digest("syscall-1"), KDATA, functions=1, size=1024, elf_type="EXEC"),
    ]
    return rows, {"a": a, "b": b, "c": c, "d": d, "e": e, "near_miss_a": near_miss_a}


def container_digest_sets(rows):
    """Exact, case-normalised digest sets keyed by source_container."""
    sets = defaultdict(set)
    for index, row in enumerate(rows):
        digest = row.get("sha256")
        if digest is None:
            raise MissingDigestError(
                f"inventory row {index} ({row.get('candidate')!r}) has no sha256 digest; "
                "exact cross-version matching requires a digest"
            )
        sets[row["source_container"]].add(digest.lower())
    return dict(sets)


def version_delta(rows, left_container, right_container):
    """Exact-match-only delta between two containers (versions)."""
    sets = container_digest_sets(rows)
    for container in (left_container, right_container):
        if container not in sets:
            raise MissingDigestError(f"container {container!r} is absent from the inventory")
    left, right = sets[left_container], sets[right_container]
    shared = left & right
    return {
        "left_container": left_container,
        "right_container": right_container,
        "shared": sorted(shared),
        "shared_count": len(shared),
        "only_in_left": sorted(left - right),
        "only_in_right": sorted(right - left),
        "left_total": len(left),
        "right_total": len(right),
    }


def summary_digest_sets(summary):
    """Derive digest sets from summary metadata, or fail loudly if absent."""
    containers = summary.get("by_source_container")
    if not isinstance(containers, dict):
        raise MissingDigestError(
            "summary metadata must contain a 'by_source_container' object, "
            f"got {type(containers).__name__}"
        )
    sets = {}
    missing = []
    for container, meta in containers.items():
        if not isinstance(meta, dict):
            raise MissingDigestError(f"summary metadata for {container!r} must be an object")
        digests = meta.get("candidate_hashes")
        if digests is None:
            missing.append(container)
            continue
        sets[container] = {digest.lower() for digest in digests}
    if missing:
        raise MissingDigestError(
            "summary metadata reports counts only and carries no candidate digests for: "
            + ", ".join(sorted(missing))
            + "; exact cross-version matching cannot be derived from counts alone"
        )
    return sets


class DeclaredSummaryMetadataTest(unittest.TestCase):
    def setUp(self):
        self.summary = _load_declared_summary()

    def test_schema_and_container_keys_are_stable(self):
        self.assertEqual(self.summary["schema_version"], 1)
        self.assertEqual(
            sorted(self.summary["by_source_container"]),
            sorted(DECLARED_CONTAINER_COUNTS),
        )

    def test_declared_counts_match_expected_container_counters(self):
        for container, expected in DECLARED_CONTAINER_COUNTS.items():
            meta = self.summary["by_source_container"][container]
            self.assertEqual(meta["candidate_count"], expected["candidate_count"], container)
            self.assertEqual(
                meta["distinct_candidate_hash_count"],
                expected["distinct_candidate_hash_count"],
                container,
            )

    def test_declared_summary_has_no_digests_so_exact_matching_is_unavailable(self):
        with self.assertRaises(MissingDigestError) as exc:
            summary_digest_sets(self.summary)
        message = str(exc.exception)
        self.assertIn("counts only", message)
        for container in DECLARED_CONTAINER_COUNTS:
            self.assertIn(container, message)

    def test_declared_summary_reports_no_duplicate_hashes(self):
        self.assertEqual(self.summary["duplicate_candidate_hashes"], [])

    def test_global_distinct_count_cannot_reveal_cross_version_overlap(self):
        # 40 candidates, 40 distinct digests: the declared metadata gives no
        # way to know whether a digest is shared between 1100 and 1120.
        summed = sum(
            meta["distinct_candidate_hash_count"]
            for meta in self.summary["by_source_container"].values()
        )
        self.assertEqual(summed, self.summary["candidate_count"])
        self.assertEqual(self.summary["distinct_candidate_hash_count"], summed)


class ExactMatchGroupingTest(unittest.TestCase):
    def setUp(self):
        self.rows, self.digests = _synthetic_inventory()

    def test_case_normalised_digests_group_as_one_exact_match(self):
        sets = container_digest_sets(self.rows)
        self.assertIn(self.digests["a"], sets[V1140])
        self.assertEqual(len(sets[V1140]), 4)

    def test_single_hex_digit_difference_is_not_an_exact_match(self):
        delta = version_delta(self.rows, V1100, V1140)
        self.assertIn(self.digests["near_miss_a"], delta["only_in_right"])
        self.assertNotIn(self.digests["near_miss_a"], delta["shared"])
        self.assertEqual(delta["shared_count"], 1)

    def test_shared_digests_are_reported_sorted_and_deterministic(self):
        first = version_delta(self.rows, V1100, V1120)
        second = version_delta(self.rows, V1100, V1120)
        self.assertEqual(first, second)
        self.assertEqual(first["shared"], sorted(first["shared"]))
        self.assertEqual(first["shared_count"], 2)
        self.assertEqual(first["only_in_left"], [self.digests["c"]])
        self.assertEqual(first["only_in_right"], [self.digests["d"]])

    def test_delta_is_symmetric(self):
        left_right = version_delta(self.rows, V1100, V1120)
        right_left = version_delta(self.rows, V1120, V1100)
        self.assertEqual(left_right["shared"], right_left["shared"])
        self.assertEqual(left_right["only_in_left"], right_left["only_in_right"])
        self.assertEqual(left_right["only_in_right"], right_left["only_in_left"])

    def test_container_matches_itself_only_by_shared_set(self):
        delta = version_delta(self.rows, V1120, V1120)
        self.assertEqual(delta["only_in_left"], [])
        self.assertEqual(delta["only_in_right"], [])
        self.assertEqual(delta["shared_count"], delta["right_total"])

    def test_unrelated_containers_share_nothing(self):
        delta = version_delta(self.rows, V1140, KDATA)
        self.assertEqual(delta["shared_count"], 0)
        self.assertEqual(delta["shared"], [])

    def test_container_keys_are_exact_not_prefix_normalised(self):
        rows = [
            _row("a", _digest("a"), "PUP.dec"),
            _row("b", _digest("a"), "PUP.dec2"),
            _row("c", _digest("a"), "PUP.dec "),
        ]
        sets = container_digest_sets(rows)
        self.assertEqual(sorted(sets), ["PUP.dec", "PUP.dec ", "PUP.dec2"])
        self.assertEqual(len(sets), 3)

    def test_grouping_is_stable_across_repeated_calls(self):
        self.assertEqual(container_digest_sets(self.rows), container_digest_sets(self.rows))


class SummaryCountConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.rows, self.digests = _synthetic_inventory()
        self.report = summarize(self.rows, json.dumps(self.rows).encode("utf-8"))

    def test_per_container_distinct_counts_match_exact_sets(self):
        sets = container_digest_sets(self.rows)
        for container, meta in self.report["by_source_container"].items():
            self.assertEqual(meta["distinct_candidate_hash_count"], len(sets[container]), container)

    def test_global_distinct_count_is_union_not_sum(self):
        summed = sum(
            meta["distinct_candidate_hash_count"]
            for meta in self.report["by_source_container"].values()
        )
        self.assertEqual(summed, 11)
        self.assertEqual(self.report["distinct_candidate_hash_count"], 7)
        self.assertLess(self.report["distinct_candidate_hash_count"], summed)

    def test_cross_container_duplicate_is_reported_once_with_sorted_candidates(self):
        duplicates = self.report["duplicate_candidate_hashes"]
        self.assertEqual(len(duplicates), 3)
        entry = next(item for item in duplicates if item["sha256"] == self.digests["d"])
        self.assertEqual(entry["candidates"], ["1120-elf-3", "1140-elf-2"])

    def test_case_insensitive_duplicate_is_reported_as_one_digest(self):
        entry = next(item for item in self.report["duplicate_candidate_hashes"]
                     if item["sha256"] == self.digests["a"])
        self.assertEqual(len(entry["candidates"]), 3)
        self.assertEqual(
            entry["candidates"],
            ["1100-elf-1", "1120-elf-1", "1140-elf-1"],
        )

    def test_container_aggregates_do_not_leak_across_versions(self):
        meta = self.report["by_source_container"][KDATA]
        self.assertEqual(meta["ghidra_function_total"], 1)
        self.assertEqual(meta["ghidra_positive_function_count"], 1)
        self.assertEqual(meta["validated_executable_bytes"], 1024)
        self.assertEqual(self.report["ghidra_function_total"], 1)

    def test_source_inventory_sha256_is_recorded_when_bytes_are_supplied(self):
        raw = json.dumps(self.rows).encode("utf-8")
        report = summarize(self.rows, raw)
        self.assertEqual(report["source_inventory_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIsNone(summarize(self.rows, b"")["source_inventory_sha256"])

    def test_summary_metadata_with_candidate_hashes_supports_exact_delta(self):
        synthetic_summary = {
            "schema_version": 1,
            "by_source_container": {
                V1100: {
                    "candidate_count": 3,
                    "distinct_candidate_hash_count": 3,
                    "candidate_hashes": [self.digests["a"], self.digests["b"], self.digests["c"]],
                },
                V1120: {
                    "candidate_count": 3,
                    "distinct_candidate_hash_count": 3,
                    "candidate_hashes": [self.digests["a"].upper(), self.digests["b"], self.digests["d"]],
                },
            },
        }
        sets = summary_digest_sets(synthetic_summary)
        self.assertEqual(sets[V1100] & sets[V1120], {self.digests["a"], self.digests["b"]})
        self.assertEqual(sets[V1100] ^ sets[V1120], {self.digests["c"], self.digests["d"]})


class MissingDigestTest(unittest.TestCase):
    def test_none_digest_is_rejected_by_summarize(self):
        rows = [_row("a", None, V1100)]
        with self.assertRaises(ValueError) as exc:
            summarize(rows)
        self.assertIn("64-character hex string", str(exc.exception))
        self.assertIn("got None", str(exc.exception))

    def test_absent_digest_field_is_rejected_by_summarize(self):
        row = _row("a", _digest("a"), V1100)
        del row["sha256"]
        with self.assertRaises(ValueError) as exc:
            summarize([row])
        self.assertIn("missing required field(s): sha256", str(exc.exception))

    def test_empty_digest_is_rejected(self):
        with self.assertRaises(ValueError) as exc:
            summarize([_row("a", "", V1100)])
        self.assertIn("64-character hex string", str(exc.exception))

    def test_non_hex_and_wrong_length_digests_are_rejected(self):
        bad = ["0" * 63, "0" * 65, "g" * 64, "not-a-digest", 12345, ["0" * 64]]
        for digest in bad:
            with self.assertRaises(ValueError) as exc:
                summarize([_row("a", digest, V1100)])
            self.assertIn("sha256", str(exc.exception))

    def test_whitespace_padded_digest_is_rejected(self):
        digest = _digest("a")
        with self.assertRaises(ValueError) as exc:
            summarize([_row("a", " " + digest, V1100)])
        self.assertIn("64-character hex string", str(exc.exception))

    def test_missing_digest_blocks_cross_version_delta(self):
        rows = [_row("a", _digest("a"), V1100), _row("b", None, V1120)]
        with self.assertRaises(MissingDigestError) as exc:
            version_delta(rows, V1100, V1120)
        self.assertIn("no sha256 digest", str(exc.exception))

    def test_absent_container_blocks_delta(self):
        rows, _ = _synthetic_inventory()
        with self.assertRaises(MissingDigestError) as exc:
            version_delta(rows, V1100, "1150_PS5UPDATE1.PUP.dec")
        self.assertIn("absent from the inventory", str(exc.exception))

    def test_summary_metadata_with_partial_digests_is_rejected(self):
        summary = {
            "schema_version": 1,
            "by_source_container": {
                V1100: {"candidate_count": 1, "candidate_hashes": [_digest("a")]},
                V1120: {"candidate_count": 1},
            },
        }
        with self.assertRaises(MissingDigestError) as exc:
            summary_digest_sets(summary)
        self.assertIn(V1120, str(exc.exception))
        self.assertNotIn(V1100, str(exc.exception))

    def test_summary_metadata_without_container_block_is_rejected(self):
        with self.assertRaises(MissingDigestError) as exc:
            summary_digest_sets({"schema_version": 1})
        self.assertIn("by_source_container", str(exc.exception))

    def test_empty_container_block_yields_no_sets(self):
        self.assertEqual(summary_digest_sets({"by_source_container": {}}), {})
        self.assertEqual(container_digest_sets([]), {})


class VersionDeltaEdgeTest(unittest.TestCase):
    def test_identical_versions_delta_to_zero(self):
        rows = [
            _row("a", _digest("a"), V1100),
            _row("b", _digest("b"), V1100),
            _row("a'", _digest("a"), V1120),
            _row("b'", _digest("b"), V1120),
        ]
        delta = version_delta(rows, V1100, V1120)
        self.assertEqual(delta["shared_count"], 2)
        self.assertEqual(delta["only_in_left"], [])
        self.assertEqual(delta["only_in_right"], [])

    def test_candidate_renamed_but_hash_unchanged_is_not_a_delta(self):
        digest = _digest("same-payload")
        rows = [_row("1100-elf", digest, V1100), _row("1140-elf-renamed", digest, V1140)]
        delta = version_delta(rows, V1100, V1140)
        self.assertEqual(delta["shared_count"], 1)
        self.assertEqual(delta["only_in_left"] + delta["only_in_right"], [])

    def test_duplicate_candidates_within_one_version_collapse_to_one_hash(self):
        digest = _digest("dup")
        rows = [_row("x1", digest, V1100), _row("x2", digest, V1100)]
        report = summarize(rows)
        meta = report["by_source_container"][V1100]
        self.assertEqual(meta["candidate_count"], 2)
        self.assertEqual(meta["distinct_candidate_hash_count"], 1)
        self.assertEqual(len(container_digest_sets(rows)[V1100]), 1)

    def test_zero_byte_candidate_still_needs_a_digest(self):
        rows = [_row("empty", _digest(""), V1100, size=0)]
        report = summarize(rows)
        self.assertEqual(report["by_source_container"][V1100]["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["by_source_container"][V1100]["validated_executable_bytes"], 0)

    def test_delta_counts_match_reported_container_counters(self):
        rows, _ = _synthetic_inventory()
        report = summarize(rows)
        delta = version_delta(rows, V1100, V1140)
        self.assertEqual(
            delta["left_total"],
            report["by_source_container"][V1100]["distinct_candidate_hash_count"],
        )
        self.assertEqual(
            delta["right_total"],
            report["by_source_container"][V1140]["distinct_candidate_hash_count"],
        )
        self.assertEqual(
            delta["shared_count"] + len(delta["only_in_left"]) + len(delta["only_in_right"]),
            delta["left_total"] + delta["right_total"] - delta["shared_count"],
        )

    def test_limitations_are_documented_and_do_not_claim_identity(self):
        report = summarize(_synthetic_inventory()[0])
        joined = " ".join(report["limitations"])
        self.assertIn("do not establish component identity", joined)
        self.assertIn("does not open firmware bytes", joined)


if __name__ == "__main__":
    unittest.main()
