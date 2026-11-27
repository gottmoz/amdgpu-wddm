# PS5 ELF candidate reassessment

## Result

The deterministic parser refreshed all 40 existing candidate extracts. Their file sizes and SHA-256 values match the previous inventory. No Ghidra import was repeated.

All 34 PUP candidates pass ELF header, program table and segment boundary checks. Each has one bounded executable `PT_LOAD` segment. The 34 executable segment hashes are unique.

The PUP candidates contain 12 raw `e_type` values of `0xfe10` and 22 of `0xfe18`. Twelve nonzero entry points map to executable segments. The other 22 entry fields are zero. These values do not establish component identity or Sony loader behavior.

All 34 candidates still have zero Ghidra functions. The metadata does not identify why Ghidra found no functions. Check the saved import settings and warnings before any individual reimport.

## Provenance

The audit used parser schema `bc250.firmware-audit/v1`, parser version 2, against the 40 extracted files under `scratch/ps5-ghidra/elf-inputs`. Firmware originals and extracts remain outside Git. The inventory preserves container names, offsets, full-file hashes, raw ELF types, executable segment boundaries and segment hashes.

See `PS5_ELF_REJECTION_REPORT.json` for per-candidate records and `PS5_ELF_INVENTORY.json` for all 40 candidates. See `PS5_VERSION_COMPARISON.md` for counts by update version.
