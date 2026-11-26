# PSP, SMU, microcode and memory-init evidence

Source: PS5_COMPONENT_MATRIX.md only.

## Direct observations
- 40 bounded ELF64 candidates across three PUP files and `kdata1001.bin`. Ghidra analysis is in progress.
- PUP entries with IDs `0x103`, `0x104`, `0x106` and `0x107` start with `e4db7c02`. A public unpacker labels some IDs as Oberon secure loaders.
- No complete PUP entry hash matches the eight public Cyan Skillfish files.
- PUP tables, one nested PUP and SLB2 markers are present.

## Unknowns
- PSP processor type and PSP contract are unverified. The component name is only a source lead.
- SMU identity is unknown. No verified header or symbol exists.
- Memory initialization identity is unknown.
- Nested GPU microcode components remain unknown.
- Boot roles of platform initialization markers are not established.

## Cross-document review
- This matrix says Ghidra analysis is in progress. `GHIDRA_ANALYSIS_STATUS.md` records 40 successful imports, so the status wording is stale. The zero-function results still need interpretation.

Note: `STRATA_SKILLS.md` was rejected as a non-declared source, so it was not read.
