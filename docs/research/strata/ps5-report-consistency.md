# PS5 report consistency note (corrected)

Source: `docs/research/ps5-dump-static-analysis.md` only.

Counts that check out:
- 33 PUP entries each. 7 identical plus 26 differing equals 33.
- ELF markers 11 + 11 + 15 + 7 = 44. Bounded candidates 10 + 10 + 14 + 6 = 40. The source does not establish that the four unbounded markers are the same four records as the failed extent checks.
- 99 complete entries equals 33 x 3, matching the eight Skillfish hash comparison.

Discrepancy: the source names `PS5_DUMP_INVENTORY.json`, not `PS5_ELF_INVENTORY.json`. This note's declared source did not include the ELF inventory, so its own cross-check was limited to the source text.

Wording gap: the "Forty candidates ... within ... their containing PUP entry" claim cannot cover the six `kdata1001.bin` candidates, which have no PUP entry.

Unknowns at the time of the source note: nested PUP payloads, per-file Ghidra logs, final function counts. Later inventory metadata records zero reported Ghidra functions for 34 PUP candidates and one for each of six bounded `kdata1001.bin` candidates; those counts do not establish analysis completeness or component identity.

The source reports zero full-entry SHA-256 matches against eight public Cyan Skillfish microcode files among 99 complete PUP entries. This does not exclude a nested component match. The 40 candidate hashes and function metadata are summarized reproducibly in `PS5_ELF_INVENTORY_SUMMARY.json`; the script reads JSON metadata only, not firmware bytes.
