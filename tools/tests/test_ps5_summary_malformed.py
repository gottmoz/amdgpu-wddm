"""Synthetic malformed-row tests for tools/firmware/elf_inventory_summary.py.

All fixtures are hand-built dicts/JSON strings. No firmware bytes, ELF files,
or host paths are read by these tests.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tools.firmware.elf_inventory_summary import main, summarize


def row(**overrides):
    """Build one synthetic, schema-valid inventory row."""
    base = {
        "candidate": "synthetic-candidate-00",
        "sha256": "0" * 64,
        "source_container": "container-a",
        "architecture": "x86_64",
        "elf_type": "ELF64",
        "bounds_valid": True,
        "ghidra_functions": 12,
        "validated_executable_bytes": 4096,
    }
    base.update(overrides)
    return base


class MalformedInventoryTest(unittest.TestCase):
    def test_inventory_must_be_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            summarize({"rows": [row()]})
        self.assertIn("inventory must be a JSON list", str(ctx.exception))
        self.assertIn("dict", str(ctx.exception))

    def test_empty_inventory_is_valid(self):
        report = summarize([])
        self.assertEqual(report["candidate_count"], 0)
        self.assertEqual(report["ghidra_function_total"], 0)
        self.assertEqual(report["by_source_container"], {})

    def test_non_object_row_is_rejected(self):
        for bad in ("not-a-row", 7, None, [row()], True):
            with self.assertRaises(ValueError) as ctx:
                summarize([bad])
            message = str(ctx.exception)
            self.assertIn("inventory row 0 must be an object", message)
            self.assertIn("got", message)

    def test_missing_fields_are_named(self):
        bad = row()
        del bad["sha256"]
        del bad["bounds_valid"]
        with self.assertRaises(ValueError) as ctx:
            summarize([row(), bad])
        message = str(ctx.exception)
        self.assertIn("inventory row 1 is missing required field(s)", message)
        self.assertIn("sha256", message)
        self.assertIn("bounds_valid", message)
        self.assertNotIn("candidate", message)

    def test_empty_candidate_is_rejected(self):
        for value in ("", "   ", None, 0):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(candidate=value)])
            self.assertIn("'candidate'", str(ctx.exception))
            self.assertIn("non-empty string", str(ctx.exception))

    def test_blank_container_architecture_and_elf_type_are_rejected(self):
        for field in ("source_container", "architecture", "elf_type"):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(**{field: ""})])
            message = str(ctx.exception)
            self.assertIn(field, message)
            self.assertIn("non-empty string", message)


class MalformedSha256Test(unittest.TestCase):
    def test_none_sha256(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row(sha256=None)])
        self.assertIn("sha256", str(ctx.exception))
        self.assertIn("got None", str(ctx.exception))

    def test_short_and_long_and_non_hex_sha256(self):
        for value in ("abc", "0" * 63, "0" * 65, "z" * 64, "0" * 64 + " ", "0" * 64 + "\n"):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(sha256=value)])
            self.assertIn("64-character hex string", str(ctx.exception))

    def test_non_string_sha256(self):
        for value in (0, 12345678901234567890, [0] * 64, True):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(sha256=value)])
            self.assertIn("sha256", str(ctx.exception))

    def test_uppercase_hex_sha256_is_accepted(self):
        report = summarize([row(sha256="A" * 64)])
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        self.assertEqual(report["duplicate_candidate_hashes"], [])


class MalformedCounterTest(unittest.TestCase):
    def test_bounds_valid_must_be_real_bool(self):
        for value in (None, 1, 0, "true", "True", 1.0, [True]):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(bounds_valid=value)])
            message = str(ctx.exception)
            self.assertIn("bounds_valid", message)
            self.assertIn("must be a boolean", message)

    def test_bool_bounds_valid_is_accepted(self):
        report = summarize([row(bounds_valid=True), row(candidate="b", bounds_valid=False)])
        self.assertEqual(report["bounds_valid_count"], 1)
        self.assertEqual(report["bounds_invalid_count"], 1)

    def test_function_counter_must_be_int(self):
        for value in (None, 1.5, "12", True, False, [12]):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(ghidra_functions=value)])
            message = str(ctx.exception)
            self.assertIn("ghidra_functions", message)
            self.assertIn("must be an integer", message)

    def test_negative_function_counter_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row(ghidra_functions=-1)])
        self.assertIn("ghidra_functions", str(ctx.exception))
        self.assertIn(">= 0", str(ctx.exception))

    def test_byte_counter_must_be_int(self):
        for value in (None, 4096.0, "4096", True):
            with self.assertRaises(ValueError) as ctx:
                summarize([row(validated_executable_bytes=value)])
            message = str(ctx.exception)
            self.assertIn("validated_executable_bytes", message)
            self.assertIn("must be an integer", message)

    def test_negative_byte_counter_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row(validated_executable_bytes=-4096)])
        self.assertIn("validated_executable_bytes", str(ctx.exception))
        self.assertIn(">= 0", str(ctx.exception))

    def test_source_bytes_must_be_bytes(self):
        with self.assertRaises(ValueError) as ctx:
            summarize([row()], source_bytes="0" * 64)
        self.assertIn("source_inventory bytes must be bytes", str(ctx.exception))
        self.assertIn("str", str(ctx.exception))

    def test_row_index_is_reported_for_later_rows(self):
        rows = [row(), row(sha256="bad")]
        with self.assertRaises(ValueError) as ctx:
            summarize(rows)
        self.assertIn("inventory row 1", str(ctx.exception))


class ValidAggregationTest(unittest.TestCase):
    def test_counters_and_grouping(self):
        rows = [
            row(candidate="a", sha256="a" * 64, ghidra_functions=3,
                validated_executable_bytes=100),
            row(candidate="b", sha256="a" * 64, ghidra_functions=0, bounds_valid=False,
                validated_executable_bytes=200),
            row(candidate="c", sha256="b" * 64, source_container="container-b",
                architecture="aarch64", elf_type="ELF32", ghidra_functions=5,
                validated_executable_bytes=50),
        ]
        report = summarize(rows, source_bytes=b'{"synthetic": true}')
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["ghidra_function_total"], 8)
        self.assertEqual(report["ghidra_zero_function_count"], 1)
        self.assertEqual(report["ghidra_positive_function_count"], 2)
        self.assertEqual(report["distinct_candidate_hash_count"], 2)
        self.assertEqual(
            report["duplicate_candidate_hashes"],
            [{"sha256": "a" * 64, "candidates": ["a", "b"]}],
        )
        self.assertEqual(report["by_source_container"]["container-a"]["candidate_count"], 2)
        self.assertEqual(report["by_source_container"]["container-b"]["candidate_count"], 1)
        self.assertEqual(report["by_source_container"]["container-a"]["validated_executable_bytes"], 300)
        self.assertEqual(len(report["source_inventory_sha256"]), 64)
        self.assertTrue(report["limitations"])

    def test_no_firmware_bytes_are_read(self):
        # The module exposes no file-reading helper other than the CLI entry point;
        # summarize() only consumes the in-memory rows and the supplied bytes.
        report = summarize([row()])
        self.assertIsNone(report["source_inventory_sha256"])


class CliMalformedJsonTest(unittest.TestCase):
    def test_cli_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_inventory.json"
            path.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                main([str(path)])
            message = str(ctx.exception)
            self.assertIn("is not valid JSON", message)
            self.assertIn("synthetic_inventory.json", message)

    def test_cli_rejects_non_list_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_inventory.json"
            path.write_text(json.dumps({"rows": []}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                main([str(path)])
            self.assertIn("inventory must be a JSON list", str(ctx.exception))

    def test_cli_accepts_synthetic_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_inventory.json"
            out = Path(tmp) / "report.json"
            path.write_text(json.dumps([row()]), encoding="utf-8")
            self.assertEqual(main([str(path), "--out", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["ghidra_function_total"], 12)


if __name__ == "__main__":
    unittest.main()
