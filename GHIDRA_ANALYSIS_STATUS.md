# Ghidra analysis status

The existing batch has 40 successful imports and was not repeated. SHA-256 correlation reports six `EXEC` ELF files with one function each. The other 34 have zero reported functions despite executable load segments.

The saved batch script uses Ghidra 12.1.4 with `-analysisTimeoutPerFile 120` and `-max-cpu 4`. It sets no explicit processor, compiler specification or analyzer options. No saved Ghidra project exists for these imports.

## Log audit

The saved Ghidra 12.1.4 logs report the ELF loader and language `x86:LE:64:default:gcc` for both a representative PUP candidate and a kdata control. This confirms x86-64 language selection for these samples. It does not confirm that the language is the correct PS5 ABI.

| Sample | File SHA-256 | ELF type | Entry | Executable mapping | Ghidra functions | Saved log SHA-256 |
|---|---|---:|---:|---|---:|---|
| PUP 11.00 candidate at recorded offset `0x13b11295` | `84e76cb5415093eb61212d621f7144e376dc3539c4131fa7dc2987677210f5f3` | `0xfe10` | `0x70` | Mapped. Ghidra reports executable block at `0x0` | 0 | `9f667dad3ee458ae881b39ed1e924babefa82a50024c62595c9defc2e7955731` |
| `kdata1001.bin` candidate at recorded offset `0x11b47b8` | `9e612bbea569eb374428888e07efdf1c8f5b96fe7df6603798abd4a582be8629` | `ET_EXEC` (`2`) | `0x400200` | Mapped. Ghidra reports executable block at `0x400000` | 1 | `58f33874aebdea5c33316268f24f36c25c8f8febf1a03719ea859bd1421c7c9d` |

The PUP sample's executable segment entropy is 7.99763 bits per byte. Across the 34 PUP candidates, the values range from 7.99762 to 7.99999, with a median of 7.999845. This is a high-entropy observation. Entropy alone cannot identify compression, encryption or executable instruction content.

The PUP sample log says `Disassemble Entry Points` completed in 0.000 seconds and reports zero functions. It also records a failed ELF note parse. The kdata control reports one function and 0.060 seconds for that analyzer. These observations narrow the comparison. They do not prove the failed note parse or ELF type caused the PUP result.

The PUP sample's `e_entry` is `0x70`. Ghidra reports an executable block at `0x0` with size 985,772 bytes, so that address falls within the reported block. The kdata control uses the same x86-64 language and maps its entry at `0x400200` inside an executable block at `0x400000`.

The PUP and kdata logs record `Disassemble Entry Points` times of 0.000 and 0.060 seconds. The report script does not list Ghidra's defined entry points. The logs therefore do not show whether Ghidra accepted the PUP `e_entry` as an entry point.

## Limits and next check

The saved logs do not record Ghidra's defined entry points. The temporary project was deleted, so program metadata is unavailable. No candidate was re-imported. A future targeted import should export the ELF entry point and Ghidra-defined entry points before any disassembly comparison. Do not force disassembly based on executable flags alone.
