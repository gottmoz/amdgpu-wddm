# PS5 kdata candidate triage

Source read: PS5_KDATA_METADATA.json only. No firmware bytes were read.

## Scope

The file reports six rows from container kdata1001.bin. Schema version is 1.
Source SHA-256 is 9ce50d49887107d1e5e92e9fffb9dd2a012abd1e7e20341062f3cd82603c674e.

## Row table

| Candidate | ELF type | Architecture | Entry point | Validated bytes | Full-file SHA-256 | Ghidra functions |
|---|---|---|---|---|---|---|
| kdata1001_offset_e0d7b8.elf | EXEC | x86-64 | 4194432 | 186412 | e8d86372736ef190fc0290e643c1cc631f1c32791682b28d9998430f52c471fc | 1 |
| kdata1001_offset_e337b8.elf | EXEC | x86-64 | 4194432 | 479612 | fdc688c1a1c2737b5201789f7172964789638037e63a06230acd38b6c285b751 | 1 |
| kdata1001_offset_e897b8.elf | EXEC | x86-64 | 4194432 | 571452 | 4de1f2b41781c0acd5a2fc3eab5809bab58b79584cc7642e2f771e1345d1e506 | 1 |
| kdata1001_offset_efb7b8.elf | EXEC | x86-64 | 4194432 | 2470524 | 916e53b9380f97f2b1b6e351a3274413b93adb0e2c8cee99a891d2be8c020709 | 1 |
| kdata1001_offset_11b47b8.elf | EXEC | x86-64 | 4194432 | 685564 | 9e612bbea569eb374428888e07efdf1c8f5b96fe7df6603798abd4a582be8629 | 1 |
| kdata1001_offset_12267b8.elf | EXEC | x86-64 | 4194432 | 142700 | 9aef15e9b2dcbc325f40616228c7a6478b37b72fe9317e63541a989052427e10 | 1 |

## Observations

All six rows share the same ELF type, architecture and entry point.
Each row reports six program headers and zero section headers.
Each row reports one executable segment and bounds_valid true.
Error codes are empty for every row.
Declared executable bytes equal validated executable bytes in all six rows.
Ghidra reports one function for every row.
Confidence is medium for every row.

## Hash uniqueness

The six full-file SHA-256 values are all distinct.
No duplicate hash appears in the six rows.
Distinct hashes show only that the six files differ as byte streams.
They do not establish component identity, subsystem role or function ownership.
Hypothesis: repeated entry points may reflect a shared load convention.
It does not prove a shared component or a shared origin.

## Recommended follow-up

Compare each row program header segment sizes against its validated executable byte count.
That comparison stays inside the declared metadata and needs no firmware access.

## Limitations

The metadata has no component names, roles or symbol tables.
Section header counts are zero, so section level attribution is unavailable.
Ghidra function counts of one limit any behavioural claim.

