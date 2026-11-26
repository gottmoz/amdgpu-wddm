# PS5 update comparison

Each local update file has 33 PUP table entries. Seven entry positions have identical packed-entry SHA-256 values across all versions. The other 26 positions differ. Entry IDs come from table metadata. They do not confirm component identity. See `PS5_SEGMENT_COMPARISON.json` for entry hashes and sizes.

## Bounded ELF candidate comparison

This section summarizes existing validated metadata. No Ghidra batch ran for this report. We compared complete candidate SHA-256 values. This is not a segment-level comparison.

| Version | Bounded candidates | Validated executable bytes | Ghidra candidates with functions |
|---|---:|---:|---:|
| 1100_PS5UPDATE1.PUP.dec | 10 | 46,213,492 | 0 |
| 1120_PS5UPDATE1.PUP.dec | 10 | 44,771,508 | 0 |
| 1140_PS5UPDATE1.PUP.dec | 14 | 118,197,596 | 0 |

| Base to target | Identical hashes | Only base | Only target | Candidate count delta | Executable byte delta |
|---|---:|---:|---:|---:|---:|
| 1100 to 1120 | 0 | 10 | 10 | 0 | -1,441,984 |
| 1100 to 1140 | 0 | 10 | 14 | 4 | +71,984,104 |
| 1120 to 1140 | 0 | 10 | 14 | 4 | +73,426,088 |

All 34 PUP candidates pass recorded boundary validation. All 34 Ghidra records report zero functions. The six `kdata1001.bin` candidates are separate. Each has one recorded function. Bounds validation and successful Ghidra import do not prove executable semantics.

The candidate count grows from 10 in 11.20 to 14 in 11.40. The inventory does not establish that these are four new components. Hash differences do not identify changed content or component identities.

Source inventory SHA-256: `4f812aefe17ad7cd5b66400841605013c42c57905fc307e28e96bee85e1360a4`.

## Executable segment hashes and ELF type metadata

The existing extracts contain 34 PUP ELF candidates. There are 10 from 11.00, 10 from 11.20 and 14 from 11.40. The read-only audit found one bounded file-backed executable `PT_LOAD` segment in each candidate. SHA-256 was calculated over each segment range. All 34 hashes are distinct. No executable segment hashes match across versions.

Full metadata for these segments is in `PS5_EXECUTABLE_SEGMENTS.json`. It includes file offsets, virtual addresses, sizes, permissions, entropy and hashes. Extracted binaries remain outside Git.

All candidates report `EI_OSABI=9`. Twelve report `e_type=0xfe10`. The other 22 report `e_type=0xfe18`. The ELF ABI specification reserves `0xfe00` to `0xfeff` for operating-system-specific semantics ([GABI ELF header](https://gabi.xinuos.com/v42/elf/02-eheader.html)).

A public reverse-engineered PS5 tool names `0xfe10` as `ET_SCE_EXEC_ASLR`. It names `0xfe18` as `ET_SCE_DYNAMIC` ([kstuff definitions](https://github.com/EchoStretch/kstuff/blob/elfldr-compatability/ps5-kstuff/porting_tool/make_fself.py)). These are source-derived names. They are not an official Sony loader contract. Tool support does not prove BC-250 or Nagi loader compatibility.

Twenty-two candidates have `e_entry=0`. The corrected parser treats zero as “no associated entry point.” It does not accept zero as mapped when a load segment starts at virtual address zero. The other 12 entry values map into bounded executable segments. This mapping does not prove loader acceptance.

The unusual `e_type` values alone do not explain Ghidra's zero-function results. Existing Ghidra records show executable program-header ranges. Loader semantics and Ghidra import settings still need investigation. The six `kdata1001.bin` extracts are not part of the version comparison.
