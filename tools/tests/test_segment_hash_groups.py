"""Synthetic regression tests for tools.firmware.segment_hash_groups."""

import io
import json
import contextlib
import os
import tempfile
import unittest

from tools.firmware.segment_hash_groups import (
    SCHEMA,
    dumps,
    from_inventory_summary,
    group_segment_hashes,
    main,
)


class GroupingTests(unittest.TestCase):
    def test_requires_sha256_format_and_explicit_validation(self):
        result = group_segment_hashes([
            {"hash": "a" * 64, "version": "11.00", "validated": True},
            {"hash": "z" * 64, "version": "11.20", "validated": True},
            {"hash": "b" * 64, "version": "11.40"},
        ])
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["hash"], "a" * 64)
        self.assertEqual(result["missing_hash_records"], [{"index": 1, "reason": "invalid-hash"}])
        self.assertEqual(result["unvalidated_records"], [{"index": 2, "hash": "b" * 64}])

    def test_identical_hash_shared_across_versions(self):
        records = [
            {"hash": "A" * 64, "firmware_version": "11.40", "container": "1140_PS5UPDATE1.PUP.dec", "validated": True},
            {"hash": "a" * 64, "firmware_version": "11.20", "container": "1120_PS5UPDATE1.PUP.dec", "validated": True},
            {"hash": "b" * 64, "firmware_version": "11.40", "container": "1140_PS5UPDATE1.PUP.dec", "validated": True},
        ]
        result = group_segment_hashes(records)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["record_count"], 3)
        self.assertEqual(result["group_count"], 2)
        self.assertEqual(result["shared_group_count"], 1)
        self.assertEqual(result["groups"][0], {
            "hash": "a" * 64,
            "occurrences": 2,
            "firmware_version_count": 2,
            "firmware_versions": ["11.20", "11.40"],
            "containers": ["1120_PS5UPDATE1.PUP.dec", "1140_PS5UPDATE1.PUP.dec"],
            "shared_across_versions": True,
        })
        self.assertEqual(result["groups"][1]["firmware_version_count"], 1)
        self.assertFalse(result["groups"][1]["shared_across_versions"])

    def test_deterministic_sorted_output(self):
        records = [
            {"segment_hash": "f" * 64, "version": "11.40", "validated": True},
            {"segment_hash": "0" * 64, "version": "11.00", "validated": True},
            {"segment_hash": "0" * 64, "version": "11.20", "validated": True},
        ]
        first = dumps(group_segment_hashes(records))
        second = dumps(group_segment_hashes(list(reversed(records))))
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual([g["hash"] for g in payload["groups"]], ["0" * 64, "f" * 64])
        self.assertEqual(payload["shared_group_count"], 1)

    def test_missing_and_invalid_hash_handling(self):
        records = [
            {"firmware_version": "11.40"},
            {"hash": None, "firmware_version": "11.40"},
            {"hash": "   ", "firmware_version": "11.40"},
            {"hash": 12345, "firmware_version": "11.40"},
            {"hash": "cc33", "firmware_version": "11.40", "validated": True},
        ]
        result = group_segment_hashes(records)
        self.assertEqual(result["missing_hash_count"], 5)
        self.assertEqual(result["group_count"], 0)
        reasons = [item["reason"] for item in result["missing_hash_records"]]
        self.assertEqual(reasons, ["invalid-hash", "missing-hash-field", "non-string-hash", "null-hash", "whitespace-only-hash"])
        self.assertEqual(result["unvalidated_count"], 0)

    def test_unvalidated_records_excluded_from_groups(self):
        records = [
            {"hash": "d" * 64, "firmware_version": "11.40", "validated": False},
            {"hash": "d" * 64, "firmware_version": "11.20", "validated": True},
        ]
        result = group_segment_hashes(records)
        self.assertEqual(result["group_count"], 1)
        self.assertEqual(result["groups"][0]["occurrences"], 1)
        self.assertEqual(result["unvalidated_count"], 1)
        self.assertEqual(result["unvalidated_records"][0], {"index": 0, "hash": "d" * 64})

    def test_non_object_record_is_missing_hash(self):
        result = group_segment_hashes(["not-a-record"])
        self.assertEqual(result["missing_hash_count"], 1)
        self.assertEqual(result["missing_hash_records"][0]["reason"], "non-object-record")

    def test_inventory_summary_has_no_per_hash_records(self):
        summary = {
            "schema_version": 1,
            "source_inventory_sha256": "4f812aefe17ad7cd5b66400841605013c42c57905fc307e28e96bee85e1360a4",
            "candidate_count": 40,
            "distinct_candidate_hash_count": 40,
            "duplicate_candidate_hashes": [],
            "by_source_container": {
                "1140_PS5UPDATE1.PUP.dec": {"distinct_candidate_hash_count": 14},
                "1100_PS5UPDATE1.PUP.dec": {"distinct_candidate_hash_count": 10},
            },
        }
        result = from_inventory_summary(summary)
        self.assertEqual(result["group_count"], 0)
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["record_count"], 0)
        self.assertEqual(result["aggregate"]["candidate_count"], 40)
        self.assertEqual(result["aggregate"]["by_source_container"], {
            "1100_PS5UPDATE1.PUP.dec": 10,
            "1140_PS5UPDATE1.PUP.dec": 14,
        })
        self.assertTrue(result["limitations"])

    def test_cli_emits_json(self):
        payload = {"segments": [{"hash": "A" * 64, "firmware_version": "11.40", "validated": True}]}
        path = self._write_tmp(payload)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([path])
        emitted = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(emitted["group_count"], 1)
        self.assertEqual(emitted["groups"][0]["hash"], "a" * 64)

    def test_cli_missing_argument_returns_error(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["error"], "usage: segment_hash_groups.py <inventory.json>")

    def _write_tmp(self, payload):
        path = os.path.join(tempfile.mkdtemp(), "inventory.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        return path


if __name__ == "__main__":
    unittest.main()
