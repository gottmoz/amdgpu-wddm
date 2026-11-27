# Ghidra analysis status

The original batch had 40 successful imports and was not repeated. Two samples were imported twice for targeted metadata reports on 2026-11-27. They were one PUP candidate and one kdata positive control. SHA-256 correlation reports six `EXEC` ELF files with one function each. The other 34 have zero reported functions despite executable load segments.

The saved batch script uses Ghidra 12.1.4 with `-analysisTimeoutPerFile 120` and `-max-cpu 4`. It sets no explicit processor, compiler specification or analyzer options. The batch deletes each temporary project. No saved Ghidra project exists for these imports.

`tools/firmware/GhidraEntryReport.java` reports the language, compiler, memory blocks, function count and Ghidra external entry points. It also checks a supplied ELF entry against memory and functions.

## Log audit

The saved Ghidra logs report the ELF loader and language `x86:LE:64:default:gcc` for both representatives. This confirms x86-64 language selection. It does not confirm that the language is the correct PS5 ABI.

| Sample | File SHA-256 | ELF type | Entry | Executable mapping | Ghidra functions | Saved log SHA-256 |
|---|---|---:|---:|---|---:|---|
| PUP 11.00 candidate at recorded offset `0x13b11295` | `84e76cb5415093eb61212d621f7144e376dc3539c4131fa7dc2987677210f5f3` | `0xfe10` | `0x70` | Mapped. Ghidra reports executable block at `0x0` | 0 | `9f667dad3ee458ae881b39ed1e924babefa82a50024c62595c9defc2e7955731` |
| `kdata1001.bin` candidate at recorded offset `0x11b47b8` | `9e612bbea569eb374428888e07efdf1c8f5b96fe7df6603798abd4a582be8629` | `ET_EXEC` (`2`) | `0x400200` | Mapped. Ghidra reports executable block at `0x400000` | 1 | `58f33874aebdea5c33316268f24f36c25c8f8febf1a03719ea859bd1421c7c9d` |

The PUP sample's executable segment entropy is 7.99763 bits per byte. Across the 34 PUP candidates, values range from 7.99762 to 7.99999. The median is 7.999845. Entropy does not identify compression, encryption or executable instruction content.

The original PUP log reports `Disassemble Entry Points` at 0.000 seconds. The original kdata log reports 0.060 seconds. The targeted imports report 0.001 and 0.050 seconds. Both targeted imports exited successfully. The PUP log also reports a failed ELF note parse. These facts do not establish a cause.
The PUP has two `PT_NOTE` ranges. Entry 9 uses file offset `0x173ed8` and length `0x24`. Entry 13 uses offset `0x1748c4` and length `0x48`. Both file ranges are bounded.

The first 12 bytes in each range do not describe a standard ELF note that fits its declared segment length. This matches Ghidra's note parse warning at `0x173ed8`. It does not explain the zero function count.

## Targeted entry report

The PUP candidate has `e_entry` `0x70`. Ghidra maps it in executable memory. No function starts at or contains this address. Ghidra reports zero external entry points and zero functions.

The kdata control has `e_entry` `0x400200`. Ghidra maps it in executable memory. No function starts at or contains this address. Ghidra reports one external entry point at `0x400080` and one function at that address.

Both imports use language `x86:LE:64:default` and compiler `gcc`. The control shows that this language can discover a function in kdata. It does not explain why the PUP candidate has none. Ghidra's external entry point list differs from the ELF `e_entry` values in these samples.

## Limits and next check

The targeted reports do not identify why Ghidra finds no function in the PUP candidate. They do not prove that its mapped bytes contain valid instructions. No additional imports are justified by this result alone. Do not force disassembly based on executable flags alone.