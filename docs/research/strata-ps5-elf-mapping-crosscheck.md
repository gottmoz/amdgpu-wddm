# PS5 ELF inventory cross-check

Scope: compare the PS5 ELF inventory, Ghidra status, and rejection report. No firmware bytes were opened for this review.

## Verified counts

- The ELF inventory contains 40 entries. Thirty-four are PUP candidates. Six are kdata entries.
- The rejection report contains 34 entries. All 34 names also appear in the inventory.
- The six inventory entries absent from the rejection report are the kdata entries.
- Ghidra imported 40 candidates. Thirty-four have zero functions. Six have one function each.
- These counts are consistent. The 34-entry rejection report covers the PUP candidates. It does not list the six kdata entries.

## Entry point limits

The inventory records entry points and executable segment counts. It does not include program header mappings, segment virtual addresses, or file offsets.

Four readable PUP records have entry points 112 or 128. These values alone do not show whether the entry point lies in an executable segment. ELF entry points are virtual addresses. A file offset comparison would be invalid without the segment mapping.

The earlier claim that these entries fall inside the program header table is unsupported by the available reports. The parser reports valid file bounds. That does not establish entry point mapping.

## Bounded follow-up

Candidate: `1100_PS5UPDATE1.PUP_offset_28cac85d.elf`.

The inventory reports one executable segment, 2,493,134 executable bytes counted by the parser, and entry point zero. It does not provide the segment address needed to assess that entry point.

Run the existing deterministic parser against this candidate from the preserved local analysis workspace. Export each loadable segment's type, file offset, virtual address, file size, memory size, and permissions. Compare the entry point only against executable virtual address ranges reported by the parser. Do not repeat Ghidra import or infer a component identity.

## Review disposition

The initial Strata draft contained two unsupported statements. It counted 34 inventory records, although the inventory contains 40. It also treated entry point values as file offsets without a segment map. This corrected note removes both claims.
