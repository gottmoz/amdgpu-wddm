import json
import tempfile
import unittest
from pathlib import Path

from tools.release.verify_python_build_deps import EXPECTED, PINNAMES, installed_versions, main, verify


class VerifyPythonBuildDepsTest(unittest.TestCase):
    def test_pins_match_the_build_playbook(self):
        self.assertEqual(PINNAMES, ("meson", "mako", "markupsafe", "pyyaml", "packaging"))
        self.assertEqual(EXPECTED, {
            "meson": "1.12.0", "mako": "1.4.1", "markupsafe": "3.0.3",
            "pyyaml": "6.0.3", "packaging": "25.0"})

    def test_verifier_accepts_all_matching_versions(self):
        self.assertTrue(all(item.ok for item in verify(EXPECTED, EXPECTED.copy())))

    def test_missing_or_mismatched_versions_fail(self):
        actual = EXPECTED.copy()
        actual["meson"] = "0.1"
        del actual["mako"]
        self.assertFalse(all(item.ok for item in verify(EXPECTED, actual)))

    def test_reads_only_distribution_metadata_from_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dist = root / "meson-1.12.0.dist-info"
            dist.mkdir()
            (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: meson\nVersion: 1.12.0\n", encoding="utf-8")
            self.assertEqual(installed_versions(root), {"meson": "1.12.0"})

    def test_cli_verifies_the_actual_isolated_install(self):
        self.assertEqual(main(["--target", r"D:\BC250-Development\scratch\py"]), 0)


if __name__ == "__main__":
    unittest.main()
