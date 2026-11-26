"""Provenance regression tests for tools/firmware/elf_inventory_summary.py.

Goal: prove that ``source_inventory_sha256`` is the SHA-256 of the *exact*
source JSON bytes handed to the summarizer (not a re-serialized, re-parsed, or
normalized rendering of them), and that any change to those bytes -- even one
that leaves every aggregate counter identical -- produces a different
provenance digest.

Only synthetic JSON inventory bytes are used. No firmware bytes are read.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.firmware.elf_inventory_summary import main, summarize


def digest_of(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_row(candidate, container="sysconf.bin", architecture="aarch64",
             elf_type="ET_EXEC", bounds_valid=True, functions=1, size=1024):
    return {
        "candidate": candidate,
        "sha256": digest_of(candidate),
        "source_container": container,
        "architecture": architecture,
        "elf_type": elf_type,
        "bounds_valid": bounds_valid,
        "ghidra_functions": functions,
        "validated_executable_bytes": size,
    }


def rows():
    return [
        make_row("elf-a", functions=3, size=4096),
        make_row("elf-b", functions=0, size=2048, bounds_valid=False),
        make_row("elf-c", container="boot.bin", functions=7, size=8192),
    ]


def pretty(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def sha256_hex(data):
    return hashlib.sha256(bytes(data)).hexdigest()


class ExactSourceHashTest(unittest.TestCase):
    """The provenance field is the SHA-256 of the exact bytes passed in."""

    def test_report_hash_equals_sha256_of_exact_source_bytes(self):
        raw = pretty(rows())
        report = summarize(json.loads(raw.decode("utf-8")), raw)
        self.assertEqual(report["source_inventory_sha256"], sha256_hex(raw))

    def test_hash_is_lowercase_64_char_hex(self):
        report = summarize(rows(), pretty(rows()))
        digest = report["source_inventory_sha256"]
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        self.assertTrue(all(ch in "0123456789abcdef" for ch in digest))

    def test_hash_is_not_of_a_renormalized_rendering(self):
        # Same parsed inventory, different byte-level rendering: the digest must
        # follow the bytes actually supplied, not a canonical dump.
        compact = json.dumps(rows(), separators=(",", ":")).encode("utf-8")
        indented = json.dumps(rows(), indent=4).encode("utf-8")
        self.assertNotEqual(sha256_hex(compact), sha256_hex(indented))

        report_compact = summarize(json.loads(compact), compact)
        report_indented = summarize(json.loads(indented), indented)
        self.assertEqual(report_compact["source_inventory_sha256"], sha256_hex(compact))
        self.assertEqual(report_indented["source_inventory_sha256"], sha256_hex(indented))
        self.assertNotEqual(report_compact["source_inventory_sha256"],
                           report_indented["source_inventory_sha256"])

    def test_hash_is_not_of_the_parsed_python_object(self):
        raw = pretty(rows())
        parsed = json.loads(raw)
        # Re-dumping the parsed object is byte-different from the source; the
        # report must still reflect the original source bytes.
        redumped = json.dumps(parsed, sort_keys=True).encode("utf-8")
        report = summarize(parsed, raw)
        self.assertEqual(report["source_inventory_sha256"], sha256_hex(raw))
        self.assertNotEqual(report["source_inventory_sha256"], sha256_hex(redumped))

    def test_key_order_is_part_of_the_hashed_bytes(self):
        reordered = json.dumps(
            [{k: v for k, v in reversed(list(row.items()))} for row in rows()]
        ).encode("utf-8")
        canonical = json.dumps(rows()).encode("utf-8")
        report_reordered = summarize(json.loads(reordered), reordered)
        report_canonical = summarize(json.loads(canonical), canonical)
        self.assertEqual(report_reordered["candidate_count"], report_canonical["candidate_count"])
        self.assertNotEqual(report_reordered["source_inventory_sha256"],
                           report_canonical["source_inventory_sha256"])

    def test_bytearray_source_bytes_are_hashed_identically(self):
        raw = pretty(rows())
        report_bytes = summarize(json.loads(raw), raw)
        report_array = summarize(json.loads(raw), bytearray(raw))
        self.assertEqual(report_bytes["source_inventory_sha256"], report_array["source_inventory_sha256"])
        self.assertEqual(report_array["source_inventory_sha256"], sha256_hex(bytearray(raw)))

    def test_no_source_bytes_yields_none_provenance(self):
        self.assertIsNone(summarize(rows())["source_inventory_sha256"])
        self.assertIsNone(summarize(rows(), b"")["source_inventory_sha256"])

    def test_non_bytes_source_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            summarize(rows(), pretty(rows()).decode("utf-8"))
        self.assertIn("source_inventory bytes must be bytes", str(ctx.exception))

    def test_provenance_is_source_bytes_not_report_bytes(self):
        raw = pretty(rows())
        report = summarize(json.loads(raw), raw)
        rendered = json.dumps(report, indent=2).encode("utf-8")
        self.assertNotEqual(report["source_inventory_sha256"], sha256_hex(rendered))

    def test_digest_is_stable_across_repeated_calls(self):
        raw = pretty(rows())
        first = summarize(json.loads(raw), raw)["source_inventory_sha256"]
        second = summarize(json.loads(raw), raw)["source_inventory_sha256"]
        self.assertEqual(first, second)
        self.assertEqual(first, sha256_hex(raw))


class ChangedInventoryDistinguishedTest(unittest.TestCase):
    """Any byte change to the inventory is visible in the provenance digest."""

    def test_row_reorder_changes_hash_even_when_aggregates_match(self):
        original = json.dumps(rows()).encode("utf-8")
        reordered = json.dumps(list(reversed(rows()))).encode("utf-8")

        report_a = summarize(json.loads(original), original)
        report_b = summarize(json.loads(reordered), reordered)

        # Every aggregate counter is identical; only provenance differs.
        for key in ("candidate_count", "bounds_valid_count", "bounds_invalid_count",
                    "ghidra_zero_function_count", "ghidra_positive_function_count",
                    "ghidra_function_total", "distinct_candidate_hash_count",
                    "duplicate_candidate_hashes", "by_source_container"):
            self.assertEqual(report_a[key], report_b[key], f"aggregate {key!r} changed")

        self.assertNotEqual(report_a["source_inventory_sha256"], report_b["source_inventory_sha256"])

    def test_changed_counter_changes_hash(self):
        original = json.dumps(rows()).encode("utf-8")
        mutated = [dict(row) for row in rows()]
        mutated[0]["ghidra_functions"] = mutated[0]["ghidra_functions"] + 1
        changed = json.dumps(mutated).encode("utf-8")

        report_original = summarize(json.loads(original), original)
        report_changed = summarize(json.loads(changed), changed)
        self.assertNotEqual(report_original["source_inventory_sha256"],
                           report_changed["source_inventory_sha256"])
        self.assertEqual(report_changed["ghidra_function_total"],
                         report_original["ghidra_function_total"] + 1)

    def test_changed_candidate_name_changes_hash_only_in_provenance(self):
        original = json.dumps(rows()).encode("utf-8")
        mutated = [dict(row) for row in rows()]
        mutated[1]["candidate"] = "elf-b-renamed"
        changed = json.dumps(mutated).encode("utf-8")

        report_original = summarize(json.loads(original), original)
        report_changed = summarize(json.loads(changed), changed)
        self.assertNotEqual(report_original["source_inventory_sha256"],
                           report_changed["source_inventory_sha256"])
        self.assertEqual(report_original["candidate_count"], report_changed["candidate_count"])
        self.assertEqual(report_original["ghidra_function_total"],
                         report_changed["ghidra_function_total"])

    def test_whitespace_only_change_changes_hash(self):
        original = json.dumps(rows(), separators=(",", ":")).encode("utf-8")
        spaced = json.dumps(rows(), separators=(", ", ": ")).encode("utf-8")
        self.assertEqual(json.loads(original), json.loads(spaced))
        report_a = summarize(json.loads(original), original)
        report_b = summarize(json.loads(spaced), spaced)
        self.assertNotEqual(report_a["source_inventory_sha256"], report_b["source_inventory_sha256"])

    def test_trailing_newline_changes_hash(self):
        without = json.dumps(rows()).encode("utf-8")
        with_newline = without + b"\n"
        report_a = summarize(json.loads(without), without)
        report_b = summarize(json.loads(with_newline), with_newline)
        self.assertEqual(report_a["candidate_count"], report_b["candidate_count"])
        self.assertNotEqual(report_a["source_inventory_sha256"], report_b["source_inventory_sha256"])

    def test_unicode_escape_vs_literal_changes_hash(self):
        literal = json.dumps([make_row("elf-\u00e9")], ensure_ascii=False).encode("utf-8")
        escaped = json.dumps([make_row("elf-\u00e9")], ensure_ascii=True).encode("utf-8")
        self.assertEqual(json.loads(literal), json.loads(escaped))
        report_literal = summarize(json.loads(literal), literal)
        report_escaped = summarize(json.loads(escaped), escaped)
        self.assertNotEqual(report_literal["source_inventory_sha256"],
                           report_escaped["source_inventory_sha256"])

    def test_duplicate_json_key_changes_hash_without_changing_parsed_rows(self):
        base = rows()[0]
        dup = (
            b'{"candidate": "elf-a", "candidate": "elf-a-dup", "sha256": "'
            + digest_of("elf-a").encode("ascii")
            + b'", "source_container": "sysconf.bin", "architecture": "aarch64",'
            b' "elf_type": "ET_EXEC", "bounds_valid": true, "ghidra_functions": 3,'
            b' "validated_executable_bytes": 4096}'
        )
        parsed = json.loads(dup)
        self.assertEqual(parsed["candidate"], "elf-a-dup")  # last key wins
        report = summarize([parsed], dup)
        self.assertEqual(report["source_inventory_sha256"], sha256_hex(dup))
        self.assertNotEqual(report["source_inventory_sha256"],
                           sha256_hex(json.dumps([base]).encode("utf-8")))

    def test_two_distinct_inventories_never_share_a_provenance_digest(self):
        payloads = [
            json.dumps(rows()).encode("utf-8"),
            json.dumps(rows()[:2]).encode("utf-8"),
            json.dumps([make_row("elf-a", bounds_valid=False)]).encode("utf-8"),
        ]
        digests = {summarize(json.loads(p), p)["source_inventory_sha256"] for p in payloads}
        self.assertEqual(len(digests), len(payloads))
        self.assertTrue(all(d is not None for d in digests))

    def test_provenance_distinguishes_inventory_with_identical_row_hashes(self):
        # Same candidate digests, different container assignment: aggregates
        # differ per container but the global counters match.
        a = [make_row("elf-a", container="sysconf.bin"), make_row("elf-b", container="boot.bin")]
        b = [make_row("elf-a", container="boot.bin"), make_row("elf-b", container="sysconf.bin")]
        raw_a, raw_b = json.dumps(a).encode("utf-8"), json.dumps(b).encode("utf-8")
        report_a, report_b = summarize(a, raw_a), summarize(b, raw_b)
        self.assertEqual(report_a["candidate_count"], report_b["candidate_count"])
        self.assertEqual(report_a["distinct_candidate_hash_count"],
                         report_b["distinct_candidate_hash_count"])
        self.assertNotEqual(report_a["source_inventory_sha256"], report_b["source_inventory_sha256"])


class CliProvenanceTest(unittest.TestCase):
    """The CLI hashes the file bytes it read, exactly as read."""

    def _run_cli(self, raw, out_path=None):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            inventory.write_bytes(raw)
            argv = ["inventory.json"]
            if out_path is not None:
                argv += ["--out", str(out_path)]
            self.assertEqual(main(argv), 0)
            return inventory

    def test_cli_hashes_exact_file_bytes(self):
        raw = pretty(rows())
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            inventory.write_bytes(raw)
            out = Path(tmp) / "report.json"
            self.assertEqual(main([str(inventory), "--out", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["source_inventory_sha256"], sha256_hex(inventory.read_bytes()))

    def test_cli_includes_bom_in_hashed_bytes(self):
        raw = b"\xef\xbb\xbf" + pretty(rows())
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            inventory.write_bytes(raw)
            out = Path(tmp) / "report.json"
            self.assertEqual(main([str(inventory), "--out", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["source_inventory_sha256"], sha256_hex(raw))
            self.assertNotEqual(report["source_inventory_sha256"], sha256_hex(raw[3:]))

    def test_cli_distinguishes_a_changed_inventory_file(self):
        original = pretty(rows())
        changed = pretty([dict(row) for row in rows()][:2])
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "inventory_a.json"
            second = Path(tmp) / "inventory_b.json"
            first.write_bytes(original)
            second.write_bytes(changed)
            out_a = Path(tmp) / "report_a.json"
            out_b = Path(tmp) / "report_b.json"
            main([str(first), "--out", str(out_a)])
            main([str(second), "--out", str(out_b)])
            report_a = json.loads(out_a.read_text(encoding="utf-8"))
            report_b = json.loads(out_b.read_text(encoding="utf-8"))
            self.assertEqual(report_a["source_inventory_sha256"], sha256_hex(original))
            self.assertEqual(report_b["source_inventory_sha256"], sha256_hex(changed))
            self.assertNotEqual(report_a["source_inventory_sha256"], report_b["source_inventory_sha256"])
            self.assertNotEqual(report_a["candidate_count"], report_b["candidate_count"])

    def test_cli_rejects_invalid_json_before_hashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "inventory.json"
            inventory.write_bytes(b"{\"rows\": [")
            with self.assertRaises(ValueError) as ctx:
                main([str(inventory)])
            self.assertIn("is not valid JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
