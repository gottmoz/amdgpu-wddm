import importlib.util,struct,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('audit',Path(__file__).parents[1]/'firmware'/'binary_audit.py'); audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
def elf(path,sections=False):
    code=b'\x90\xc3'; phoff=64; shoff=120 if sections else 0; eh=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+bytes(9),2,62,1,0x400078,phoff,shoff,0,64,56,1,64,0,0)
    ph=struct.pack('<IIQQQQQQ',1,5,0,0x400000,0,122,122,0x1000)
    path.write_bytes(eh+ph+code)
class AuditTests(unittest.TestCase):
    def test_elf_without_section_headers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x'; elf(p); x=audit.detect(p)['elf']; self.assertEqual(x['architecture'],'x86-64'); self.assertTrue(x['entry_valid']); self.assertEqual(x['section_header_count'],0); self.assertEqual(x['executable_bytes'],122)
    def test_truncated_program_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x'; elf(p); p.write_bytes(p.read_bytes()[:80]); x=audit.detect(p)['elf']; self.assertFalse(x['bounds_valid']); self.assertTrue(x['warnings'])
    def test_cache_invalidates_on_size_change(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x'; c=Path(d)/'cache.json'; p.write_bytes(b'abc'); a=audit.cached_detect(p,c); p.write_bytes(b'abcd'); b=audit.cached_detect(p,c); self.assertNotEqual(a['size'],b['size'])
if __name__=='__main__': unittest.main()
