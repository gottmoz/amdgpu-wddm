# PS5 segment comparison review

## Verified segment results

The deterministic comparison was rebuilt from `PS5_ELF_INVENTORY.json`. The rebuilt JSON matches `PS5_SEGMENT_COMPARISON.json` in full.

| Update | PUP candidates | Executable segments | Unique segment hashes |
|---|---:|---:|---:|
| 11.00 | 10 | 10 | 10 |
| 11.20 | 10 | 10 | 10 |
| 11.40 | 14 | 14 | 14 |
| Total | 34 | 34 | 34 |

The inventory has 40 candidates. Six are from `kdata1001.bin` and are outside this PUP comparison. This explains the 40 versus 34 scope difference in the Markdown report.

The 34 executable segment hashes are distinct. There are no exact segment hash matches across versions. The hashes establish byte identity only. They do not identify components or prove loader compatibility.

## PUP table-entry comparison

`PS5_PUP_ENTRY_COMPARISON.json` and its hash audit report 33 table entries per update. Seven positions are identical across all three updates. Twenty-six positions differ. This comparison uses each table entry's recorded size and SHA-256. It does not assign component identities.

The input files contain metadata and hashes. Firmware binaries and disassembly remain outside this report.
