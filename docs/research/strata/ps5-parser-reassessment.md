# PS5 parser-v2 reassessment

Source: PS5_ELF_REJECTION_REPORT.json (read truncated at 8 records).

Direct observations:
- Each visible record came from 1100_PS5UPDATE1.PUP.dec and carried "ELF bounds rejected by parser v1".
- Parser v2 gives reason "No ELF bounds violations", bounds_valid true, and empty error_codes.
- All are x86-64, elf_type "other", 14 program headers, 0 section headers, 1 executable segment.
- declared_executable_bytes equals validated_executable_bytes in every visible record.
- ghidra_functions is 0 and confidence is medium. Entry points are 0, 112, or 128.

Unknowns:
- Total record count and the fields of the truncated eighth record.
- Whether any candidate was still rejected by v2.
- Why Ghidra recovers no functions despite valid bounds.
