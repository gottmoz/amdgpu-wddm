# PS5 ELF counts - observed and unknown

Source: PS5_ELF_INVENTORY.json. The read was truncated at the 12k character limit.

Direct observations, 10 complete records, all from 1100_PS5UPDATE1.PUP.dec:
- All 10 are x86-64 with elf_type "other", 14 program headers, 0 section headers, and 1 executable segment.
- All 10 report bounds_valid true and empty error_codes.
- declared_executable_bytes equals validated_executable_bytes in all 10, totalling 46,213,492 bytes.
- All 10 report ghidra_functions 0 and confidence "medium".
- Entry points are 0 in 6 records, 112 in 3, and 128 in 1.
- File sizes range from 1,526,028 to 35,660,836 bytes.

Unknowns:
- Total record count. An 11th record naming 1120_PS5UPDATE1.PUP.dec is cut off mid-field.
- Whether any unseen record fails bounds checks or reports non-zero Ghidra functions.
- Ghidra version, loader options, and the cause of the zero function counts.
