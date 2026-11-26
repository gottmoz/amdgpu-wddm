"""Sparse-row behaviour tests for tools/firmware/elf_inventory_summary.py.

Objective: characterise what happens when inventory rows are sparse (fields
absent) and pin down the stable defaults the summariser exposes through
assertions. The source schema declares no optional fields, so the documented
stable behaviour is:

  * an absent field is rejected with a deterministic ValueError naming the row
    index and the missing field(s), in REQUIRED_FIELDS order;
  * no default value is substituted for an absent field;
  * extra/unknown keys (e.g. "component", "notes") are neither required nor
    used to invent names;
  * the only genuine defaults are the function signature default
    (source_bytes=b"") and the derived empty/zero aggregates.

All fixtures are synthetic metadata. No firmware bytes are read or written.
"""

import unittest

from tools.firmware.elf_inventory_summary import (
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    summarize,
)


def full_row(candidate="candidate-1", container="container-a", **overrides):
    """Return a complete, schema-valid row using neutral, non-component labels."""
    row = {
        "candidate": candidate,
        "sha256": "a" * 64,
        "source_container": container,
        "architecture": "x86_64",
        "elf_type": "elf-unknown",
        "bounds_valid": True,
        "ghidra_functions": 0,
        "validated_executable_bytes": 0,
    }
    row.update(overrides)
    return row


def sparse_row(missing_fields):
    """Return a full row with the given fields removed."""
    row = full_row()
    for field in missing_fields:
        row.pop(field, None)
    return row


class SchemaShapeTest(unittest.TestCase):
    def test_required_fields_are_a_stable_tuple(self):
        self.assertIsInstance(REQUIRED_FIELDS, tuple)
        self.assertEqual(
            REQUIRED_FIELDS,
            (
                "candidate",
                "sha256",
                "source_container",
                "architecture",
                "elf_type",
                "bounds_valid",
                "ghidra_functions",
                "validated_executable_bytes",
            ),
        )

    def test_schema_declares_no_optional_fields(self):
        # Every field the summariser touches is in REQUIRED_FIELDS, so a sparse
        # row can never rely on an implicit default.
        self.assertEqual(len(REQUIRED_FIELDS), 8)
        self.assertEqual(len(set(REQUIRED_FIELDS)), len(REQUIRED_FIELDS))

    def test_empty_inventory_is_accepted(self):
        report = summarize([])
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        self.assertEqual(report["candidate_count"], 0)
        self.assertEqual(report["bounds_valid_count"], 0)
        self.assertEqual(report["bounds_invalid_count"], 0)
        self.assertEqual(report["ghidra_zero_function_count"], 0)
        self.assertEqual(report["ghidra_positive_function_count"], 0)
        self.assertEqual(report["ghidra_function_total"], 0)
        self.assertEqual(report["distinct_candidate_hash_count"], 0)
        self.assertEqual(report["duplicate_candidate_hashes"], [])
        self.assertEqual(report["by_source_container"], {})
        self.assertIsNone(report["source_inventory_sha256"])


class AbsentFieldRejectionTest(unittest.TestCase):
    def test_each_required_field_absent_is_rejected(self):
        for field in REQUIRED_FIELDS:
            with self.assertRaises(ValueError) as ctx:
                summarize([sparse_row([field])])
            self.assertEqual(
                str(ctx.exception),
                f"inventory row 0 is missing required field(s): {field}",
            )

    def test_missing_fields_are_reported_in_schema_order(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([sparse_row(["elf_type", "candidate", "bounds_valid"])])
        self.assertEqual(
            str(ctx.exception),
            "inventory row 0 is missing required field(s): candidate, elf_type, bounds_valid",
        )

    def test_row_index_is_stable_for_sparse_rows(self):
        rows = [
            full_row(candidate="candidate-1"),
            full_row(candidate="candidate-2", sha256="b" * 64),
            sparse_row(["ghidra_functions"]),
        ]
        with self.assertRaises(ValueError) as ctx:
            summarize(rows)
        self.assertEqual(
            str(ctx.exception),
            "inventory row 2 is missing required field(s): ghidra_functions",
        )

    def test_all_fields_absent_lists_every_field(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([{}])
        self.assertEqual(
            str(ctx.exception),
            "inventory row 0 is missing required field(s): " + ", ".join(REQUIRED_FIELDS),
        )

    def test_null_is_not_treated_as_an_absent_field_default(self):
        # Explicit nulls are rejected too; they are not coerced to defaults.
        for field in ("sha256", "bounds_valid", "ghidra_functions", "validated_executable_bytes"):
            with self.assertRaises(ValueError) as ctx:
                summarize([full_row(**{field: None})])
            self.assertIn(field, str(ctx.exception))

    def test_empty_string_fields_are_rejected_not_defaulted(self):
        for field in ("candidate", "source_container", "architecture", "elf_type"):
            with self.assertRaises(ValueError) as ctx:
                summarize([full_row(**{field: ""})])
            self.assertIn(field, str(ctx.exception))

    def test_sparse_row_is_not_rescued_by_extra_keys(self):
        # An unrelated key that looks like it could stand in for a missing field
        # is ignored, never substituted.
        row = sparse_row(["source_container"])
        row["component"] = "unknown-module"
        row["notes"] = "container inferred from context"
        with self.assertRaises(ValueError) as ctx:
            summarize([row])
        self.assertEqual(
            str(ctx.exception),
            "inventory row 0 is missing required field(s): source_container",
        )

    def test_non_object_sparse_row_is_rejected_before_field_checks(self):
        for bad_row in (None, [], "candidate-1", 7):
            with self.assertRaises(ValueError) as ctx:
                summarize([bad_row])
            self.assertIn("inventory row 0 must be an object", str(ctx.exception))

    def test_non_list_inventory_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize({"candidate": "candidate-1"})
        self.assertEqual(str(ctx.exception), "inventory must be a JSON list, got dict")


class StableDefaultsTest(unittest.TestCase):
    def test_source_bytes_default_yields_null_digest(self):
        report_default = summarize([full_row()])
        report_explicit_empty = summarize([full_row()], source_bytes=b"")
        self.assertEqual(report_default, report_explicit_empty)
        self.assertIsNone(report_default["source_inventory_sha256"])

    def test_source_bytes_digest_is_lowercase_and_stable(self):
        payload = b'{"rows": []}'
        report = summarize([full_row()], source_bytes=payload)
        digest = report["source_inventory_sha256"]
        self.assertIsInstance(digest, str)
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        self.assertEqual(
            digest,
            summarize([full_row()], source_bytes=payload)["source_inventory_sha256"],
        )

    def test_non_bytes_source_inventory_is_rejected(self):
        for bad in (None, "{}", 0):
            with self.assertRaises(ValueError) as ctx:
                summarize([full_row()], source_bytes=bad)
            self.assertIn("source_inventory bytes must be bytes", str(ctx.exception))

    def test_zero_counters_are_stable_defaults_for_sparse_values(self):
        report = summarize(
            [
                full_row(ghidra_functions=0, validated_executable_bytes=0),
                full_row(candidate="candidate-2", sha256="b" * 64, bounds_valid=False),
            ]
        )
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["bounds_valid_count"], 1)
        self.assertEqual(report["bounds_invalid_count"], 1)
        self.assertEqual(report["ghidra_zero_function_count"], 2)
        self.assertEqual(report["ghidra_positive_function_count"], 0)
        self.assertEqual(report["ghidra_function_total"], 0)
        self.assertEqual(report["distinct_candidate_hash_count"], 2)
        self.assertEqual(report["duplicate_candidate_hashes"], [])

    def test_group_counters_default_to_zero(self):
        report = summarize([full_row(ghidra_functions=0, validated_executable_bytes=0)])
        group = report["by_source_container"]["container-a"]
        self.assertEqual(
            group,
            {
                "candidate_count": 1,
                "architectures": {"x86_64": 1},
                "elf_types": {"elf-unknown": 1},
                "bounds_valid_count": 1,
                "bounds_invalid_count": 0,
                "ghidra_zero_function_count": 1,
                "ghidra_positive_function_count": 0,
                "ghidra_function_total": 0,
                "validated_executable_bytes": 0,
                "distinct_candidate_hash_count": 1,
            },
        )

    def test_report_key_set_is_fixed(self):
        report = summarize([full_row()])
        self.assertEqual(
            set(report),
            {
                "schema_version",
                "source_inventory_sha256",
                "candidate_count",
                "bounds_valid_count",
                "bounds_invalid_count",
                "ghidra_zero_function_count",
                "ghidra_positive_function_count",
                "ghidra_function_total",
                "distinct_candidate_hash_count",
                "duplicate_candidate_hashes",
                "by_source_container",
                "limitations",
            },
        )

    def test_limitations_are_stable_and_name_no_component(self):
        report = summarize([full_row()])
        self.assertEqual(
            report["limitations"],
            [
                "Function counts are reported Ghidra metadata and do not establish analysis completeness.",
                "Valid parser bounds do not establish component identity or executable behavior.",
                "This report reads the JSON inventory only and does not open firmware bytes.",
            ],
        )
        for line in report["limitations"]:
            self.assertNotIn("PS5", line)
            self.assertNotIn("firmware component", line)


class NoInferredNamesTest(unittest.TestCase):
    def test_container_keys_come_only_from_declared_field(self):
        report = summarize(
            [
                full_row(candidate="candidate-1", container="container-a", sha256="a" * 64),
                full_row(candidate="candidate-2", container="container-b", sha256="b" * 64),
            ]
        )
        self.assertEqual(sorted(report["by_source_container"]), ["container-a", "container-b"])
        self.assertNotIn("candidate-1", report["by_source_container"])
        self.assertNotIn("unknown", report["by_source_container"])

    def test_duplicate_groups_use_declared_candidate_strings(self):
        report = summarize(
            [
                full_row(candidate="candidate-b", container="container-a", sha256="c" * 64),
                full_row(candidate="candidate-a", container="container-b", sha256="C" * 64),
            ]
        )
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(
            report["duplicate_candidate_hashes"],
            [{"sha256": "c" * 64, "candidates": ["candidate-a", "candidate-b"]}],
        )

    def test_unknown_extra_keys_do_not_appear_in_report(self):
        row = full_row()
        row["component"] = "inferred-component"
        row["module_name"] = "inferred-module"
        report = summarize([row])
        rendered = str(report)
        self.assertNotIn("inferred-component", rendered)
        self.assertNotIn("inferred-module", rendered)
        self.assertNotIn("component", report)

    def test_architecture_and_elf_type_buckets_are_sorted_not_synthesised(self):
        report = summarize(
            [
                full_row(candidate="candidate-1", architecture="arm64", elf_type="elf-32"),
                full_row(
                    candidate="candidate-2",
                    sha256="b" * 64,
                    architecture="x86_64",
                    elf_type="elf-64",
                ),
            ]
        )
        group = report["by_source_container"]["container-a"]
        self.assertEqual(list(group["architectures"]), ["arm64", "x86_64"])
        self.assertEqual(list(group["elf_types"]), ["elf-32", "elf-64"])
        self.assertEqual(group["candidate_count"], 2)


if __name__ == "__main__":
    unittest.main()
