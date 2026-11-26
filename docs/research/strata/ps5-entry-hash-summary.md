# PS5 entry hash comparison - visible records

Direct observations from PS5_SEGMENT_COMPARISON.json:
- 33 entries are visible for 1100_PS5UPDATE1.PUP.dec, index 0 through 32. Every sha256 in that set is distinct.
- Same size with different hash: index 11 and 13 (477396 B), index 24 and 25 (443328 B).
- Index 0 matches across versions: id 3842, 4096 B, sha256 ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7 in both 1100 and 1120.
- The 1120 block is cut off at index 1, so no other position pair is readable.

Unknowns: total record count, hashes for 1120 index 1 onward, and which positions differ. No component inference was made.