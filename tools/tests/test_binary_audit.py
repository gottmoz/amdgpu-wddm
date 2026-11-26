import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).parents[1] / "firmware" / "binary_audit.py"
spec = importlib.util.spec_from_file_location("binary_audit", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def make_elf(path, *, phentsize=56, shentsize=0, phnum=1, shnum=0, phoff=64,
             shoff=0, ptype=1, pflags=5, poff=0, va=0x400000, filesz=128,
             memsz=160, entry=0x400080, extra=b""):
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 2, 62, 1, entry,
                         phoff, shoff, 0, 64, phentsize, phnum, shentsize,
                         shnum, 0)
    ph = struct.pack("<IIQQQQQQ", ptype, pflags, poff, va, va, filesz,
                     memsz, 0x1000) if phentsize == 56 else bytes(max(0, phentsize))
    path.write_bytes(header + ph * phnum + bytes(256) + extra)


class AuditTests(unittest.TestCase):
    def fixture(self, directory, **kwargs):
        p = Path(directory) / "fixture.elf"
        make_elf(p, **kwargs)
        return p

    def test_valid_elf_without_section_headers(self):
        with tempfile.TemporaryDirectory() as d:
            e = audit.detect(self.fixture(d))["elf"]
            self.assertEqual(e["architecture"], "x86-64")
            self.assertEqual(e["section_header_count"], 0)
            self.assertTrue(e["bounds_valid"])

    def test_zero_entry_is_not_mapped_when_load_begins_at_zero(self):
        with tempfile.TemporaryDirectory() as d:
            e = audit.detect(self.fixture(d, va=0, poff=64, entry=0))["elf"]
            self.assertFalse(e["entry_valid"])
            self.assertIn("entry point is outside file-backed executable PT_LOAD", e["warnings"])

    def test_invalid_header_entry_sizes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("ELF_PHENTSIZE_INVALID", audit.detect(self.fixture(d, phentsize=0))["elf"]["error_codes"])
            self.assertIn("ELF_SHENTSIZE_INVALID", audit.detect(self.fixture(d, shnum=1, shentsize=0, shoff=120))["elf"]["error_codes"])

    def test_truncated_program_and_section_tables(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.fixture(d, phoff=400)
            self.assertIn("ELF_PHDR_TABLE_TRUNCATED", audit.detect(p)["elf"]["error_codes"])
            p = self.fixture(d, shnum=2, shentsize=64, shoff=400)
            self.assertIn("ELF_SHDR_TABLE_TRUNCATED", audit.detect(p)["elf"]["error_codes"])

    def test_invalid_segment_range_and_non_loadable_type(self):
        with tempfile.TemporaryDirectory() as d:
            e = audit.detect(self.fixture(d, poff=1000))["elf"]
            self.assertIn("SEGMENT_FILE_RANGE_INVALID", e["error_codes"])
            e = audit.detect(self.fixture(d, ptype=4))["elf"]
            self.assertEqual(e["validated_executable_bytes"], 0)

    def test_overlapping_loads_and_entry_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.elf"
            ident=b"\x7fELF\x02\x01\x01"+bytes(9)
            h=struct.pack("<16sHHIQQQIHHHHHH",ident,2,62,1,0x500000,64,0,0,64,56,2,0,0,0)
            a=struct.pack("<IIQQQQQQ",1,5,0,0x400000,0,128,160,4096)
            b=struct.pack("<IIQQQQQQ",1,4,128,0x400080,0,128,128,4096)
            p.write_bytes(h+a+b+bytes(256)); e=audit.detect(p)["elf"]
            self.assertEqual(e["overlapping_segments"],[[0,1]])
            self.assertFalse(e["entry_valid"])
            self.assertEqual(e["program_headers"][0]["zero_initialized_bytes"],32)

    def test_extended_numbering_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d,shoff=120)
            self.assertIn("ELF_EXTENDED_NUMBERING_UNSUPPORTED",audit.detect(p)["elf"]["error_codes"])

    def test_entropy_cli_and_hash_range_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d); self.assertGreaterEqual(audit.entropy_range(p),0)
            with self.assertRaisesRegex(ValueError,"RANGE_OUT_OF_BOUNDS"): audit.hash_range(p,9999,3)

    def test_cache_parser_version_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d); c=Path(d)/"cache.json"; audit.cached_detect(p,c)
            data=json.loads(c.read_text()); data["parser_version"]=-1; c.write_text(json.dumps(data))
            audit.cached_detect(p,c); self.assertEqual(json.loads(c.read_text())["parser_version"],audit.PARSER_VERSION)


if __name__ == "__main__": unittest.main()
