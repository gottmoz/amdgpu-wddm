"""Synthetic assertions for the deterministic Markdown renderer.

No firmware bytes are read; every payload is constructed in-test.
"""

import io
import json
import unittest
from contextlib import redirect_stdout

from tools.firmware.elf_inventory_summary import (
    main,
    render_markdown,
    summarize,
)


def _row(candidate, digest, container, elf_type="other", functions=0, bounds=True, size=100):
    return {
        "candidate": candidate,
        "sha256": digest,
        "source_container": container,
        "architecture": "x86-64",
        "elf_type": elf_type,
        "bounds_valid": bounds,
        "ghidra_functions": functions,
        "validated_executable_bytes": size,
    }


def _synthetic_rows():
    return [
        _row("a", "a" * 64, "PUP.dec", functions=0, size=10),
        _row("b", "b" * 64, "PUP.dec", functions=3, size=20),
        _row("c", "c" * 64, "PUP.dec2", elf_type="EXEC", functions=1, bounds=False, size=30),
        _row("d", "b" * 64, "PUP.dec2", functions=0, size=40),
    ]


class MarkdownRendererTest(unittest.TestCase):
    def test_counts_are_rendered(self):
        report = summarize(_synthetic_rows())
        text = render_markdown(report)
        self.assertIn("# PS5 ELF Inventory Summary", text)
        self.assertIn("| Candidates | 4 |", text)
        self.assertIn("| Bounds valid | 3 |", text)
        self.assertIn("| Bounds invalid | 1 |", text)
        self.assertIn("| Ghidra zero-function candidates | 2 |", text)
        self.assertIn("| Ghidra positive-function candidates | 2 |", text)
        self.assertIn("| Ghidra function total | 4 |", text)
        self.assertIn("| Distinct candidate hashes | 3 |", text)
        self.assertIn("| Duplicate candidate hash entries | 1 |", text)
        self.assertIn("| Source containers | 2 |", text)

    def test_container_table_rows(self):
        report = summarize(_synthetic_rows())
        text = render_markdown(report)
        self.assertIn(
            "| PUP.dec | 2 | 2 | 2 | 0 | 1 | 1 | 3 | 30 |", text
        )
        self.assertIn(
            "| PUP.dec2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 70 |", text
        )

    def test_container_order_is_sorted_and_stable(self):
        rows = [
            _row("z", "d" * 64, "PUP.dec2"),
            _row("y", "e" * 64, "1100_PS5UPDATE1.PUP.dec"),
            _row("x", "f" * 64, "kdata1001.bin"),
        ]
        first = render_markdown(summarize(rows))
        second = render_markdown(summarize(list(reversed(rows))))
        self.assertEqual(first, second)
        order = [line for line in first.splitlines() if line.startswith("### ")]
        self.assertEqual(
            order,
            ["### 1100_PS5UPDATE1.PUP.dec", "### PUP.dec2", "### kdata1001.bin"],
        )

    def test_deterministic_byte_identical_output(self):
        report = summarize(_synthetic_rows(), b"seed")
        self.assertEqual(render_markdown(report), render_markdown(report))

    def test_hex_case_normalization_in_duplicates(self):
        rows = [
            _row("u", "A" * 64, "PUP.dec"),
            _row("v", "a" * 64, "PUP.dec"),
        ]
        report = summarize(rows)
        self.assertEqual(report["distinct_candidate_hash_count"], 1)
        text = render_markdown(report)
        self.assertIn(f"- `{'a' * 64}`: u, v", text)

    def test_no_duplicates_section(self):
        report = summarize([_row("only", "e" * 64, "kdata1.bin")])
        text = render_markdown(report)
        self.assertIn("None detected.", text)

    def test_empty_inventory(self):
        report = summarize([])
        text = render_markdown(report)
        self.assertIn("| Candidates | 0 |", text)
        self.assertIn("No containers in the inventory.", text)
        self.assertIn("None detected.", text)

    def test_limitations_documented_and_no_identity_claim(self):
        report = summarize(_synthetic_rows())
        text = render_markdown(report)
        joined = " ".join(text.split())
        self.assertIn("## Limitations (metadata only)", text)
        self.assertIn("do not establish component identity", joined)
        self.assertIn("does not open firmware bytes", joined)
        self.assertIn("no component identity is inferred", joined)
        for forbidden in ("component is", "identified as", "matches the", "belongs to"):
            self.assertNotIn(forbidden, joined.lower())

    def test_markdown_escapes_pipes(self):
        rows = [_row("pipe|name", "f" * 64, "A|B.dec")]
        text = render_markdown(summarize(rows))
        self.assertIn("| A\\|B.dec | 1 |", text)

    def test_source_sha_rendered(self):
        raw = json.dumps(_synthetic_rows()).encode("utf-8")
        report = summarize(_synthetic_rows(), raw)
        text = render_markdown(report)
        self.assertIn(f"- Source inventory SHA-256: {report['source_inventory_sha256']}", text)
        self.assertIn("- Source inventory SHA-256: not recorded", render_markdown(summarize(_synthetic_rows())))

    def test_invalid_report_rejected(self):
        report = summarize(_synthetic_rows())
        report["candidate_count"] = 99
        with self.assertRaises(ValueError):
            render_markdown(report)

    def test_missing_limitations_rejected(self):
        report = summarize(_synthetic_rows())
        report["limitations"] = []
        with self.assertRaises(ValueError):
            render_markdown(report)

    def test_cli_markdown_flag_writes_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            out = Path(tmp) / "summary.md"
            inventory.write_text(json.dumps(_synthetic_rows()), encoding="utf-8")
            code = main([str(inventory), "--markdown", "--out", str(out)])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("# PS5 ELF Inventory Summary", text)
            self.assertIn("| Candidates | 4 |", text)
            self.assertNotIn("{", text.split("\n")[0])

    def test_cli_json_default_still_json(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            out = Path(tmp) / "summary.json"
            inventory.write_text(json.dumps(_synthetic_rows()), encoding="utf-8")
            main([str(inventory), "--out", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidate_count"], 4)
            self.assertIn("limitations", payload)

    def test_cli_markdown_to_stdout(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            inventory.write_text(json.dumps(_synthetic_rows()), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                main([str(inventory), "--markdown"])
            self.assertIn("# PS5 ELF Inventory Summary", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
