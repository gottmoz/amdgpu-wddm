import unittest

from tools.firmware.compare_ps5_elf_segments import compare_executable_segments


def row(version, candidate, digest, *, source_offset=100, segment_index=0):
    return {
        "candidate": candidate,
        "source_container": f"{version.replace('.', '')}_PS5UPDATE1.PUP.dec",
        "source_offset": source_offset,
        "bounds_valid": True,
        "binary_audit_schema": "bc250.firmware-audit/v1",
        "binary_audit_parser_version": 2,
        "executable_segments": [{
            "index": segment_index,
            "file_offset": 4096,
            "virtual_address": 0,
            "file_size": 512,
            "flags": 1,
            "entropy_bits_per_byte": 7.5,
            "sha256": digest,
        }],
    }


class ComparePs5ElfSegmentsTests(unittest.TestCase):
    def test_reports_exact_matches_across_versions(self):
        digest = "a" * 64
        report = compare_executable_segments([
            row("11.00", "old.elf", digest),
            row("11.20", "middle.elf", digest, source_offset=200),
            row("11.40", "new.elf", "b" * 64),
        ])

        self.assertEqual(report["schema"], "bc250.ps5-segment-comparison/v1")
        self.assertEqual(report["summary"]["segment_count"], 3)
        self.assertEqual(report["summary"]["unique_hash_count"], 2)
        self.assertEqual(len(report["cross_version_matches"]), 1)
        match = report["cross_version_matches"][0]
        self.assertEqual(match["sha256"], digest)
        self.assertEqual(match["versions"], ["11.00", "11.20"])
        self.assertEqual(len(match["instances"]), 2)

    def test_does_not_report_same_version_duplicates_as_cross_version_matches(self):
        digest = "c" * 64
        report = compare_executable_segments([
            row("11.00", "one.elf", digest),
            row("11.00", "two.elf", digest, source_offset=200),
        ])

        self.assertEqual(report["summary"]["unique_hash_count"], 1)
        self.assertEqual(report["cross_version_matches"], [])

    def test_ignores_non_pup_inventory_rows(self):
        data = row("11.00", "pup.elf", "d" * 64)
        kdata = row("11.00", "kdata.elf", "e" * 64)
        kdata["source_container"] = "kdata1001.bin"

        report = compare_executable_segments([data, kdata])

        self.assertEqual(report["summary"]["candidate_count"], 1)
        self.assertEqual(report["summary"]["segment_count"], 1)

    def test_rejects_invalid_segment_hash(self):
        item = row("11.00", "bad.elf", "not-a-sha256")

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            compare_executable_segments([item])

    def test_rejects_unvalidated_candidate_boundaries(self):
        item = row("11.00", "truncated.elf", "f" * 64)
        item["bounds_valid"] = False

        with self.assertRaisesRegex(ValueError, "boundary validation"):
            compare_executable_segments([item])

    def test_rejects_unknown_pup_version(self):
        item = row("11.00", "bad.elf", "f" * 64)
        item["source_container"] = "1190_PS5UPDATE1.PUP.dec"

        with self.assertRaisesRegex(ValueError, "unsupported PUP version"):
            compare_executable_segments([item])


if __name__ == "__main__":
    unittest.main()
