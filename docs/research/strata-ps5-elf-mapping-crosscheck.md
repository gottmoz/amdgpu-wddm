# PS5 ELF inventory cross-check

Scope: compare the deterministic ELF inventory, Ghidra status, and rejection report. This review used structured metadata. It did not read firmware bytes.

## Verified counts

- The inventory contains 40 candidates. Thirty-four come from PUP files. Six come from `kdata1001.bin`.
- The rejection report contains the same 34 PUP candidate names. It excludes the six kdata candidates.
- Ghidra imported all 40 candidates. The existing batch reports zero functions for 34 PUP candidates and one function for each of six kdata candidates.
- Parser schema `bc250.firmware-audit/v1`, version 2, records bounded executable `PT_LOAD` segments for all 34 PUP candidates.
- Each PUP candidate has one bounded executable segment. Their 34 SHA-256 values are distinct.

## Entry point mapping

The enriched inventory records ELF entry values and the bounded executable segment's file offset, virtual address, file size, memory size, permissions, entropy, and hash.

- Twelve PUP candidates have nonzero entry values. The parser maps each one into its bounded executable segment.
- The other 22 candidates have a zero entry value. The parser maps zero into their executable segment ranges because all 34 segments begin at virtual address zero. This structural mapping does not prove that zero is a usable runtime entry point.
- The PUP ELF types are 12 values of `0xfe10` and 22 values of `0xfe18`. The values do not establish component identity or Sony loader behavior.

The earlier report lacked program-header mappings and could not assess entry mapping. The deterministic parser has now supplied those fields. No Ghidra import was repeated for this refresh.

## Ghidra comparison

The saved logs select `x86:LE:64:default:gcc` for both a PUP sample and a kdata control. The PUP sample has a mapped entry and an executable memory block, but zero functions. The kdata control has standard ELF type `ET_EXEC`, a mapped entry, and one function. The comparison does not establish why Ghidra found no PUP functions.

The PUP executable segments have entropy from 7.99762 to 7.99999 bits per byte. Entropy alone cannot determine whether bytes are compressed, encrypted, or instructions. Do not force disassembly from executable flags alone.

## Review disposition

This update supersedes the earlier follow-up that requested program-header mappings. The enriched records are in `PS5_ELF_INVENTORY.json` and `PS5_ELF_REJECTION_REPORT.json`. The log comparison is in `GHIDRA_ANALYSIS_STATUS.md`. These reports contain metadata and hashes, not firmware binaries or disassembly.
