import unittest

from tools.firmware.enrich_elf_inventory import enrich_inventory


class EnrichElfInventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [{
            "candidate": "sample.elf",
            "size": 100,
            "sha256": "a" * 64,
            "elf_type": "other",
        }]
        self.audit = {
            "schema": "bc250.firmware-audit/v1",
            "parser_version": 2,
            "files": [{
                "path": r"D:\scratch\sample.elf",
                "size": 100,
                "sha256": "A" * 64,
                "elf": {
                    "type": 0xFE10,
                    "entry_valid": True,
                    "program_headers": [
                        {"index": 0, "type": 1, "flags": 5, "offset": 64,
                         "vaddr": 0x1000, "filesz": 16, "memsz": 32,
                         "executable": True, "bounded": True,
                         "zero_initialized_bytes": 16, "sha256": "b" * 64,
                         "entropy_bits_per_byte": 6.5},
                        {"index": 1, "type": 1, "flags": 4, "offset": 80,
                         "vaddr": 0x2000, "filesz": 8, "memsz": 8,
                         "executable": False, "bounded": True,
                         "zero_initialized_bytes": 0, "sha256": "c" * 64,
                         "entropy_bits_per_byte": 3.0},
                        {"index": 2, "type": 1, "flags": 5, "offset": 96,
                         "vaddr": 0x3000, "filesz": 4, "memsz": 4,
                         "executable": True, "bounded": False,
                         "zero_initialized_bytes": 0, "sha256": None,
                         "entropy_bits_per_byte": None},
                    ],
                },
            }],
        }

    def test_joins_only_validated_executable_segments(self):
        result = enrich_inventory(self.inventory, self.audit)[0]
        self.assertEqual(result["e_type"], 0xFE10)
        self.assertEqual(result["e_type_hex"], "0xfe10")
        self.assertTrue(result["entry_point_mapped"])
        self.assertEqual([s["index"] for s in result["executable_segments"]], [0])
        self.assertEqual(result["executable_segments"][0]["zero_initialized_bytes"], 16)
        self.assertEqual(result["binary_audit_parser_version"], 2)

    def test_rejects_size_or_hash_mismatch(self):
        self.audit["files"][0]["sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            enrich_inventory(self.inventory, self.audit)
        self.audit["files"][0]["sha256"] = "a" * 64
        self.audit["files"][0]["size"] = 99
        with self.assertRaisesRegex(ValueError, "size"):
            enrich_inventory(self.inventory, self.audit)

    def test_rejects_candidate_set_mismatch(self):
        self.audit["files"] = []
        with self.assertRaisesRegex(ValueError, "candidate sets differ"):
            enrich_inventory(self.inventory, self.audit)

    def test_rejects_duplicate_audit_names(self):
        self.audit["files"].append(dict(self.audit["files"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate candidate name"):
            enrich_inventory(self.inventory, self.audit)


if __name__ == "__main__":
    unittest.main()
