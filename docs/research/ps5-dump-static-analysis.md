# Local PS5 update file analysis

Status: static observations on user-provided files, 2026-11-25. The acquisition source is
unknown. Original files remain unchanged. Binary copies, Ghidra projects and detailed logs
stay in `D:\BC250-Development\scratch\ps5-ghidra`, outside Git.

## Inputs and method

`PS5_DUMP_INVENTORY.json` records the four analyzed files, byte counts and SHA-256 hashes.
The folder also contains key-related files and archives. Those files were not opened for
binary analysis. Archive listing showed no executable extension in `mgs4.zip`.

The PUP table layout was checked against the [open-source unpacker header](https://raw.githubusercontent.com/zecoxao/ps5-pup-unpacker/master/PUP.h)
and [entry reader](https://raw.githubusercontent.com/zecoxao/ps5-pup-unpacker/master/PUP.cpp).
The local parser read the 32-byte header and bounded each 32-byte table entry against the
actual file size. It did not decompress, decrypt or change a package. The names in that
unpacker are research leads, not verified identities for these files.

## Observed boundaries

| Input | PUP table entries | Out-of-bounds entries | Valid ELF64 markers | Bounded ELF files |
|---|---:|---:|---:|---:|
| `1100_PS5UPDATE1.PUP.dec` | 33 | 0 | 11 | 10 |
| `1120_PS5UPDATE1.PUP.dec` | 33 | 0 | 11 | 10 |
| `1140_PS5UPDATE1.PUP.dec` | 33 | 0 | 15 | 14 |
| `kdata1001.bin` | not a PUP | not applicable | 7 | 6 |

The three PUP header size fields equal their actual file sizes. Their entry tables have the
same count. Of the 33 entry positions, seven have identical packed SHA-256 values in all
three files and 26 differ. Each PUP has a bounded 11,780,212-byte nested PUP with six
table entries. The nested payloads were not decrypted or interpreted.

ELF candidates were checked for ELF64 little-endian headers, x86-64 machine type, and
program and section header bounds. Forty candidates have file extents within the source
file and their containing PUP entry. Four candidates failed the stricter extent check.
The 40 bounded files were copied to scratch for Ghidra. They are not in Git.

## Ghidra results and limits

Ghidra 12.1.4 headless imported the first raw PUP entry as x86-64 and reported zero
functions. Raw import has no trusted load address or entry point. Ghidra recognized a
bounded ELF from `kdata1001.bin` as x86-64 ELF and reported one function. A bounded
ELF batch is in progress. Its per-file logs and function inventories remain in scratch.
Function counts describe Ghidra's output for each import, not a complete firmware map.

The eight public Cyan Skillfish microcode SHA-256 values in
`tools/firmware/cyan_skillfish2.json` match none of the 99 complete PUP entries. This
does not rule out a nested component match. No PSP, SMU, GPU microcode, memory init or
platform init image has been identified by a verified component label in these inputs.
