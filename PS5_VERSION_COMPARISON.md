# PS5 update comparison

The three local update files each contain 33 PUP table entries. Packed-entry SHA-256 comparison shows 7 entry positions byte-identical across all three and 26 positions differing. Entry IDs are table metadata, not confirmed component identities. See `PS5_SEGMENT_COMPARISON.json` for per-entry hashes and sizes.

## Bounded ELF candidate comparison

This section summarizes existing validated metadata; no Ghidra batch was rerun. Complete candidate SHA-256 values were compared across the three PUP versions. This is whole-candidate equality, not a segment-level comparison.

| Version | Bounded candidates | Validated executable bytes | Ghidra candidates with functions |
|---|---:|---:|---:|
| 1100_PS5UPDATE1.PUP.dec | 10 | 46,213,492 | 0 |
| 1120_PS5UPDATE1.PUP.dec | 10 | 44,771,508 | 0 |
| 1140_PS5UPDATE1.PUP.dec | 14 | 118,197,596 | 0 |

| Base → target | Identical hashes | Only base | Only target | Candidate-count delta | Executable-byte delta |
|---|---:|---:|---:|---:|---:|
| 1100_PS5UPDATE1.PUP.dec → 1120_PS5UPDATE1.PUP.dec | 0 | 10 | 10 | +0 | -1,441,984 |
| 1100_PS5UPDATE1.PUP.dec → 1140_PS5UPDATE1.PUP.dec | 0 | 10 | 14 | +4 | +71,984,104 |
| 1120_PS5UPDATE1.PUP.dec → 1140_PS5UPDATE1.PUP.dec | 0 | 10 | 14 | +4 | +73,426,088 |

All 34 PUP candidates are marked bounds-valid in the existing inventory; all 34 corresponding Ghidra records report zero functions. The six `kdata1001.bin` candidates are separate and are not included above; each has one recorded function. Bounds validation and successful Ghidra import do not prove complete executable semantics. The inventory schema does not record per-segment hashes, so this report does not claim identical executable segments.

No exact whole-candidate hashes match across the compared versions. Hash differences do not identify what changed or establish component identities. The candidate count increases from 10 in 11.20 to 14 in 11.40; this reflects the inventory and is not interpreted as four newly introduced components.

Source inventory SHA-256: `4f812aefe17ad7cd5b66400841605013c42c57905fc307e28e96bee85e1360a4`.
