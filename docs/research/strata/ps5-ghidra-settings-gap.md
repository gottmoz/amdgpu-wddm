# Ghidra batch settings gap

Direct observations from `GHIDRA_ANALYSIS_STATUS.md`:

- Completed batch: 40 successful imports, and it was not repeated.
- Recorded setting: the ELF auto-loader was used for extracted candidates.
- Reported outcome: SHA-256 correlation shows six `EXEC` ELF files with one function each, while the other 34 report zero functions despite executable load segments.

Explicitly missing from the saved batch logs:

- Compiler spec.
- Analysis options.

Not stated anywhere in the source, so unknown:

- Ghidra version, entry-point selection, per-file analysis logs, total candidate count, and the cause of the zero-function results.

No setting beyond the ELF auto-loader can be confirmed from the declared source.
