import io
import json
import hashlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tools.firmware.ps5_version_delta import SCHEMA, compare_containers, main

SUMMARY = {
    "schema_version": 1,
    "by_source_container": {
        "1100_PS5UPDATE1.PUP.dec": {
            "candidate_count": 3,
            "architectures": {"x86-64": 3},
            "bounds_valid_count": 3,
            "bounds_invalid_count": 0,
            "validated_executable_bytes": 1000,
            "distinct_candidate_hash_count": 3,
        },
        "1120_PS5UPDATE1.PUP.dec": {
            "candidate_count": 3,
            "architectures": {"x86-64": 3},
            "bounds_valid_count": 3,
            "bounds_invalid_count": 0,
            "validated_executable_bytes": 1200,
            "distinct_candidate_hash_count": 3,
        },
    },
    "records": [
        {"id": "a1", "container": "1100_PS5UPDATE1.PUP.dec", "sha256": "A" * 64},
        {"id": "a2", "container": "1100_PS5UPDATE1.PUP.dec", "sha256": "b" * 64},
        {"id": "a3", "container": "1100_PS5UPDATE1.PUP.dec", "sha256": "c" * 64},
        {"id": "b1", "container": "1120_PS5UPDATE1.PUP.dec", "sha256": f"  {'A' * 64} "},
        {"id": "b2", "container": "1120_PS5UPDATE1.PUP.dec", "sha256": "d" * 64},
        {"id": "b3", "container": "1120_PS5UPDATE1.PUP.dec", "sha256": None},
        {"id": "b4", "container": "1120_PS5UPDATE1.PUP.dec", "sha256": "   "},
        "not-an-object",
    ],
}

REAL_CONTAINERS = {
    "by_source_container": {
        "1100_PS5UPDATE1.PUP.dec": {"candidate_count": 10, "validated_executable_bytes": 46213492},
        "1120_PS5UPDATE1.PUP.dec": {"candidate_count": 10, "validated_executable_bytes": 44771508},
    }
}


class TestPs5VersionDelta(unittest.TestCase):
    def test_raw_candidate_inventory_groups_exact_hashes(self):
        rows = [
            {"source_container": "11.00", "candidate": "a", "sha256": "a" * 64,
             "bounds_valid": True, "ghidra_functions": 0, "validated_executable_bytes": 40},
            {"source_container": "11.20", "candidate": "b", "sha256": "a" * 64,
             "bounds_valid": True, "ghidra_functions": 1, "validated_executable_bytes": 50},
            {"source_container": "11.20", "candidate": "c", "sha256": "b" * 64,
             "bounds_valid": True, "ghidra_functions": 0, "validated_executable_bytes": 10},
        ]
        result = compare_containers(rows, "11.00", "11.20")
        self.assertEqual(result["hash_equality"]["identical_hashes"], ["a" * 64])
        self.assertEqual(result["hash_equality"]["only_in_target"], ["b" * 64])
        self.assertEqual(result["field_deltas"]["candidate_count"]["delta"], 1)
        self.assertIn("component identity", " ".join(result["limitations"]))

    def test_exact_overlap_and_deltas(self):
        result = compare_containers(SUMMARY, "1100_PS5UPDATE1.PUP.dec", "1120_PS5UPDATE1.PUP.dec")
        self.assertEqual(result["schema"], SCHEMA)
        eq = result["hash_equality"]
        self.assertTrue(eq["available"])
        self.assertEqual(eq["identical_count"], 1)
        self.assertEqual(eq["identical_hashes"], ["a" * 64])
        self.assertEqual(eq["only_in_base"], ["b" * 64, "c" * 64])
        self.assertEqual(eq["only_in_target"], ["d" * 64])
        self.assertFalse(eq["exact_match"])

    def test_numeric_field_delta(self):
        result = compare_containers(SUMMARY, "1100_PS5UPDATE1.PUP.dec", "1120_PS5UPDATE1.PUP.dec")
        self.assertEqual(result["field_deltas"]["validated_executable_bytes"],
                         {"base": 1000, "target": 1200, "delta": 200})
        self.assertNotIn("candidate_count", result["field_deltas"])
        self.assertIn("candidate_count", result["equal_fields"])

    def test_identical_containers_are_exact_match(self):
        result = compare_containers(SUMMARY, "1100_PS5UPDATE1.PUP.dec", "1100_PS5UPDATE1.PUP.dec")
        self.assertTrue(result["hash_equality"]["exact_match"])
        self.assertEqual(result["field_deltas"], {})

    def test_order_independence(self):
        shuffled = dict(SUMMARY)
        shuffled["records"] = list(reversed(SUMMARY["records"]))
        a = compare_containers(SUMMARY, "1100_PS5UPDATE1.PUP.dec", "1120_PS5UPDATE1.PUP.dec")
        b = compare_containers(shuffled, "1100_PS5UPDATE1.PUP.dec", "1120_PS5UPDATE1.PUP.dec")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_declared_hash_list_fallback(self):
        summary = {
            "containers": {
                "v1": {"candidate_count": 2, "hashes": ["F" * 64, "f" * 63 + "1", None, ""]},
                "v2": {"candidate_count": 2, "candidate_hashes": ["F" * 64, "F" * 63 + "2"]},
            }
        }
        eq = compare_containers(summary, "v1", "v2")["hash_equality"]
        self.assertEqual(eq["identical_hashes"], ["f" * 64])
        self.assertEqual(eq["only_in_base"], ["f" * 63 + "1"])
        self.assertEqual(eq["only_in_target"], ["f" * 63 + "2"])

    def test_no_hash_metadata_is_not_claimed_equal(self):
        summary = {"containers": {"v1": {"candidate_count": 1}, "v2": {"candidate_count": 1}}}
        eq = compare_containers(summary, "v1", "v2")["hash_equality"]
        self.assertFalse(eq["available"])
        self.assertFalse(eq["exact_match"])
        self.assertEqual(eq["identical_hashes"], [])

    def test_unknown_container_raises(self):
        with self.assertRaises(ValueError):
            compare_containers(SUMMARY, "1100_PS5UPDATE1.PUP.dec", "missing")

    def test_cli_emits_compact_sorted_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(REAL_CONTAINERS, fh)
            path = fh.name
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main([path, "1100_PS5UPDATE1.PUP.dec", "1120_PS5UPDATE1.PUP.dec"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["schema"], SCHEMA)
        with open(path, "rb") as source:
            expected_source_hash = hashlib.sha256(source.read()).hexdigest()
        self.assertEqual(payload["source_inventory_sha256"], expected_source_hash)
        self.assertFalse(payload["hash_equality"]["available"])
        self.assertEqual(payload["field_deltas"]["validated_executable_bytes"]["delta"], -1441984)
        self.assertEqual(out.getvalue().strip(), json.dumps(payload, sort_keys=True, separators=(",", ":")))

    def test_cli_bad_args_and_missing_container(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(main(["only-one-arg"]), 2)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(REAL_CONTAINERS, fh)
            path = fh.name
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(main([path, "1100_PS5UPDATE1.PUP.dec", "missing"]), 1)
        self.assertIn("unknown container", err.getvalue())


if __name__ == "__main__":
    unittest.main()
