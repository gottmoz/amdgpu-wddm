# PS5 update comparison

## ELF candidates

The parser rechecked 40 existing candidate extracts. The file sizes and SHA-256 values match the previous inventory. No Ghidra imports were repeated.

| Update | PUP candidates | `e_type` 0xfe10 | `e_type` 0xfe18 | Nonzero mapped entries | Unique executable segments |
|---|---:|---:|---:|---:|---:|
| 11.00 | 10 | 4 | 6 | 4 | 10 |
| 11.20 | 10 | 4 | 6 | 4 | 10 |
| 11.40 | 14 | 4 | 10 | 4 | 14 |
| Total | 34 | 12 | 22 | 12 | 34 |

Every PUP candidate has one bounded executable `PT_LOAD` segment. The 34 segment SHA-256 values are distinct within the analyzed set. The candidate hashes do not establish component identity across versions.

All 34 candidates retain zero Ghidra functions. This refresh did not repeat imports. See `PS5_ELF_INVENTORY.json` for raw types, mapped entry points, segment ranges and hashes. See `PS5_SEGMENT_COMPARISON.json` for the separate PUP table-entry comparison.

## PUP table entries

Each update file has 33 recorded table entries. Seven entry positions have identical size and SHA-256 values across all three versions. The other 26 positions differ. The hash scope is each recorded table entry. Entry IDs and hashes do not establish component identity.
