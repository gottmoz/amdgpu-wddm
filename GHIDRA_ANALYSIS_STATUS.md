# Ghidra analysis status

The existing batch has 40 successful imports and was not repeated. SHA-256 correlation reports six `EXEC` ELF files with one function each. The other 34 have zero reported functions despite executable load segments.

## Log audit

The saved Ghidra 12.1.4 logs report the ELF loader and language `x86:LE:64:default:gcc` for both a representative PUP candidate and a kdata control. This confirms x86-64 language selection for these samples. It does not confirm that the language is the correct PS5 ABI.

| Sample | File SHA-256 | ELF type | Entry | Executable mapping | Ghidra functions | Saved log SHA-256 |
|---|---|---:|---:|---|---:|---|
| PUP 11.00 candidate at recorded offset `0x13b11295` | `84e76cb5415093eb61212d621f7144e376dc3539c4131fa7dc2987677210f5f3` | `0xfe10` | `0x70` | Mapped. Ghidra reports executable block at `0x0` | 0 | `9f667dad3ee458ae881b39ed1e924babefa82a50024c62595c9defc2e7955731` |
| `kdata1001.bin` candidate at recorded offset `0x11b47b8` | `9e612bbea569eb374428888e07efdf1c8f5b96fe7df6603798abd4a582be8629` | `ET_EXEC` (`2`) | `0x400200` | Mapped. Ghidra reports executable block at `0x400000` | 1 | `58f33874aebdea5c33316268f24f36c25c8f8febf1a03719ea859bd1421c7c9d` |

The PUP sample's executable segment entropy is 7.99763 bits per byte. Across the 34 PUP candidates, the values range from 7.99762 to 7.99999, with a median of 7.999845. This is a high-entropy observation. Entropy alone cannot identify compression, encryption or executable instruction content.

The PUP sample log says `Disassemble Entry Points` completed in 0.000 seconds and reports zero functions. It also records a failed ELF note parse. The kdata control reports one function and 0.060 seconds for that analyzer. These observations narrow the comparison. They do not prove the failed note parse or ELF type caused the PUP result.

## Limits and next check

The saved logs do not record a full analysis-option set or an explicit imported entry-point list. No candidate was re-imported. A bounded next check is to inspect the saved Ghidra program metadata for entry-point creation and analyzer options for the two hashed samples. Do not force disassembly of the high-entropy PUP segments based on executable flags alone.
