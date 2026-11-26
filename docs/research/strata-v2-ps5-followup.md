# Strata v2 - PS5 follow-up (metadata only)

Sources: `PS5_ELF_INVENTORY.json`, `PS5_SEGMENT_COMPARISON.json`.

**Numerical observation.** Every ELF candidate visible in the inventory reports
`declared_executable_bytes == validated_executable_bytes` with `bounds_valid: true`,
`section_header_count: 0`, and `program_header_count: 14`. The largest such gap is
candidate `1100_PS5UPDATE1.PUP_offset_14ba9895.elf`: 33,921,044 bytes total vs.
25,593,244 declared executable bytes (75.4%). In the segment comparison, the largest
segment of `1100_PS5UPDATE1.PUP.dec` is index 32 (id 516) at 919,186,432 bytes, about
2.66x the next largest (index 30, id 515, 345,955,840 bytes).

**Bounded follow-up question.** Does segment id 516 in the 1120 container have the same
size and sha256 as the 1100 entry, or is the difference confined to that single segment?

No firmware component identity is inferred. only container/segment metadata is used.

