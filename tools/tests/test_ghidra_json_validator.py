"""Synthetic fixtures for the Ghidra JSON metadata validator.

No firmware bytes are read or written; every fixture is inline JSON text.
"""

from __future__ import annotations

import json
import unittest

from tools.firmware.ghidra_json_validator import (
    REQUIRED_CONTAINER,
    REQUIRED_TOP_LEVEL,
    validate_json,
    validate_metadata,
)


def base_container(name="a.bin", count=4, arch="x86-64", elf="EXEC"):
    return {
        "candidate_count": count,
        "architectures": {arch: count},
        "elf_types": {elf: count},
        "bounds_valid_count": count,
        "bounds_invalid_count": 0,
        "ghidra_zero_function_count": count - 1,
        "ghidra_positive_function_count": 1,
        "ghidra_function_total": count,
        "validated_executable_bytes": 1000 * count,
        "distinct_candidate_hash_count": count,
    }


def base_metadata():
    containers = {
        "kdata1001.bin": base_container(count=6, elf="EXEC"),
        "1100_PS5UPDATE1.PUP.dec": base_container(count=10, elf="other"),
    }
    return {
        "schema_version": 1,
        "source_inventory_sha256": "4f812aefe17ad7cd5b66400841605013c42c57905fc307e28e96bee85e1360a4",
        "candidate_count": 16,
        "bounds_valid_count": 16,
        "bounds_invalid_count": 0,
        "ghidra_zero_function_count": 14,
        "ghidra_positive_function_count": 2,
        "ghidra_function_total": 16,
        "distinct_candidate_hash_count": 16,
        "duplicate_candidate_hashes": [],
        "by_source_container": containers,
        "limitations": ["synthetic fixture only"],
    }


class SchemaShapeTest(unittest.TestCase):
    def test_required_fields_are_stable_tuples(self):
        self.assertIsInstance(REQUIRED_TOP_LEVEL, tuple)
        self.assertIsInstance(REQUIRED_CONTAINER, tuple)
        self.assertEqual(len(REQUIRED_TOP_LEVEL), 12)
        self.assertEqual(len(REQUIRED_CONTAINER), 10)
        self.assertEqual(REQUIRED_TOP_LEVEL[0], "schema_version")
        self.assertEqual(REQUIRED_CONTAINER[0], "candidate_count")

    def test_empty_containers_is_accepted(self):
        payload = base_metadata()
        payload["by_source_container"] = {}
        for field in (
            "candidate_count",
            "bounds_valid_count",
            "ghidra_function_total",
            "ghidra_zero_function_count",
            "distinct_candidate_hash_count",
        ):
            payload[field] = 0
        payload["ghidra_positive_function_count"] = 0
        payload["bounds_invalid_count"] = 0
        report = validate_metadata(payload)
        self.assertTrue(report["ok"])
        self.assertEqual(report["container_count"], 0)
        self.assertEqual(report["block_counts"], {"valid": 0, "invalid": 0, "total": 0})
        self.assertEqual(report["function_counts"]["total"], 0)
        self.assertEqual(report["architecture_counts"], {})


class AcceptanceTest(unittest.TestCase):
    def test_valid_metadata_reports_counts(self):
        report = validate_metadata(base_metadata())
        self.assertTrue(report["ok"])
        self.assertEqual(report["schema"], "ghidra_json_metadata/1")
        self.assertEqual(report["container_count"], 2)
        self.assertEqual(report["candidate_count"], 16)
        self.assertEqual(report["block_counts"], {"valid": 16, "invalid": 0, "total": 16})
        self.assertEqual(
            report["function_counts"],
            {"zero_function_candidates": 14, "positive_function_candidates": 2, "total": 16},
        )
        self.assertEqual(report["architecture_counts"], {"x86-64": 16})
        self.assertEqual(report["elf_type_counts"], {"EXEC": 6, "other": 10})
        self.assertEqual(
            report["architecture_counts_by_container"],
            {"1100_PS5UPDATE1.PUP.dec": {"x86-64": 10}, "kdata1001.bin": {"x86-64": 6}},
        )
        self.assertEqual(report["validated_executable_bytes"], 16000)
        self.assertEqual(report["duplicate_candidate_hash_count"], 0)

    def test_mixed_architectures_are_aggregated(self):
        payload = base_metadata()
        payload["by_source_container"]["aarch64.bin"] = base_container(
            count=3, arch="AArch64", elf="DYN"
        )
        payload["candidate_count"] = 19
        payload["bounds_valid_count"] = 19
        payload["ghidra_zero_function_count"] = 16
        payload["ghidra_positive_function_count"] = 3
        payload["ghidra_function_total"] = 19
        payload["distinct_candidate_hash_count"] = 19
        report = validate_metadata(payload)
        self.assertEqual(report["architecture_counts"], {"AArch64": 3, "x86-64": 16})
        self.assertEqual(report["block_counts"]["total"], 19)

    def test_invalid_blocks_are_counted(self):
        payload = base_metadata()
        container = payload["by_source_container"]["kdata1001.bin"]
        container["bounds_valid_count"] = 4
        container["bounds_invalid_count"] = 2
        payload["bounds_valid_count"] = 14
        payload["bounds_invalid_count"] = 2
        report = validate_metadata(payload)
        self.assertEqual(report["block_counts"], {"valid": 14, "invalid": 2, "total": 16})

    def test_json_text_and_bytes_are_parsed(self):
        text = json.dumps(base_metadata())
        self.assertTrue(validate_json(text)["ok"])
        self.assertTrue(validate_json(text.encode("utf-8"))["ok"])

    def test_duplicates_are_reported(self):
        payload = base_metadata()
        payload["duplicate_candidate_hashes"] = ["aa"] * 2
        payload["distinct_candidate_hash_count"] = 14
        payload["by_source_container"]["1100_PS5UPDATE1.PUP.dec"]["distinct_candidate_hash_count"] = 8
        report = validate_metadata(payload)
        self.assertEqual(report["duplicate_candidate_hash_count"], 2)
        self.assertEqual(report["distinct_candidate_hash_count"], 14)

    def test_extra_keys_are_ignored(self):
        payload = base_metadata()
        payload["component"] = "unknown"
        payload["by_source_container"]["kdata1001.bin"]["notes"] = "n/a"
        self.assertTrue(validate_metadata(payload)["ok"])


class MissingFieldRejectionTest(unittest.TestCase):
    def test_each_missing_top_level_field_is_rejected(self):
        for field in REQUIRED_TOP_LEVEL:
            payload = base_metadata()
            del payload[field]
            with self.assertRaises(ValueError) as ctx:
                validate_metadata(payload)
            self.assertIn(
                f"metadata root is missing required field(s): {field}",
                str(ctx.exception),
            )

    def test_each_missing_container_field_is_rejected(self):
        for field in REQUIRED_CONTAINER:
            payload = base_metadata()
            del payload["by_source_container"]["kdata1001.bin"][field]
            with self.assertRaises(ValueError) as ctx:
                validate_metadata(payload)
            self.assertIn(
                f"container 'kdata1001.bin' is missing required field(s): {field}",
                str(ctx.exception),
            )

    def test_multiple_missing_fields_are_listed_in_schema_order(self):
        payload = base_metadata()
        del payload["candidate_count"]
        del payload["limitations"]
        with self.assertRaises(ValueError) as ctx:
            validate_metadata(payload)
        self.assertIn(
            "metadata root is missing required field(s): candidate_count, limitations",
            str(ctx.exception),
        )

    def test_null_and_empty_values_are_rejected_not_defaulted(self):
        payload = base_metadata()
        payload["candidate_count"] = None
        with self.assertRaises(ValueError):
            validate_metadata(payload)

        payload = base_metadata()
        payload["source_inventory_sha256"] = ""
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_missing_field_is_not_rescued_by_extra_keys(self):
        payload = base_metadata()
        del payload["ghidra_function_total"]
        payload["ghidra_function_total_note"] = "see containers"
        with self.assertRaises(ValueError):
            validate_metadata(payload)


class InvalidValueRejectionTest(unittest.TestCase):
    def test_non_object_root(self):
        for bad in ([], "text", 3, None):
            with self.assertRaises(ValueError):
                validate_metadata(bad)

    def test_bad_json_text(self):
        with self.assertRaises(ValueError):
            validate_json("{not json")

    def test_wrong_schema_version(self):
        payload = base_metadata()
        payload["schema_version"] = 2
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_bad_sha256(self):
        for bad in ("4F812AEFE17AD7CD5B66400841605013C42C57905FC307E28E96BEE85E1360A4", "abc", 123, "a" * 64 + "\n"):
            payload = base_metadata()
            payload["source_inventory_sha256"] = bad
            with self.assertRaises(ValueError):
                validate_metadata(payload)

    def test_negative_and_bool_counts(self):
        for bad in (-1, True, 1.0, "4"):
            payload = base_metadata()
            payload["by_source_container"]["kdata1001.bin"]["candidate_count"] = bad
            with self.assertRaises(ValueError):
                validate_metadata(payload)

    def test_architectures_must_be_object_of_counts(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["architectures"] = ["x86-64"]
        with self.assertRaises(ValueError):
            validate_metadata(payload)

        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["architectures"] = {"x86-64": -2}
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_container_must_be_object(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"] = "not-an-object"
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_empty_container_name(self):
        payload = base_metadata()
        payload["by_source_container"][""] = base_container(count=1)
        payload["candidate_count"] = 17
        payload["bounds_valid_count"] = 17
        payload["ghidra_zero_function_count"] = 15
        payload["ghidra_positive_function_count"] = 3
        payload["ghidra_function_total"] = 17
        payload["distinct_candidate_hash_count"] = 17
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_limitations_must_be_list_of_strings(self):
        payload = base_metadata()
        payload["limitations"] = [None]
        with self.assertRaises(ValueError):
            validate_metadata(payload)


class ConsistencyRejectionTest(unittest.TestCase):
    def test_block_counts_must_sum_to_candidate_count(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["bounds_invalid_count"] = 1
        with self.assertRaises(ValueError) as ctx:
            validate_metadata(payload)
        self.assertIn("bounds_valid_count + bounds_invalid_count", str(ctx.exception))

    def test_function_counts_must_sum_to_total(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["ghidra_positive_function_count"] = 3
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_architecture_counts_must_sum_to_candidate_count(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["architectures"] = {"x86-64": 5}
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_root_totals_must_match_container_sums(self):
        payload = base_metadata()
        payload["candidate_count"] = 17
        with self.assertRaises(ValueError) as ctx:
            validate_metadata(payload)
        self.assertIn("does not match container sum", str(ctx.exception))

    def test_distinct_hashes_cannot_exceed_candidates(self):
        payload = base_metadata()
        payload["by_source_container"]["kdata1001.bin"]["distinct_candidate_hash_count"] = 7
        payload["distinct_candidate_hash_count"] = 17
        with self.assertRaises(ValueError):
            validate_metadata(payload)

    def test_duplicate_list_length_must_match(self):
        payload = base_metadata()
        payload["duplicate_candidate_hashes"] = ["aa"]
        with self.assertRaises(ValueError):
            validate_metadata(payload)


if __name__ == "__main__":
    unittest.main()
