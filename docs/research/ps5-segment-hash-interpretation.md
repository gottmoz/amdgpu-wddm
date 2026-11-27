# PS5 segment hash audit interpretation

## Scope

This note uses only PS5_SEGMENT_HASH_AUDIT.json. No other source was read. No firmware bytes were inspected.

## Verified version counts

- 1100_PS5UPDATE1.PUP.dec reports an entry count of 33.
- 1120_PS5UPDATE1.PUP.dec reports an entry count of 33.
- 1140_PS5UPDATE1.PUP.dec reports an entry count of 33.
- The recorded compared index count is 33.
- Each version lists indices 0 through 32.

## Verified unchanged and changed indices

- Seven indices are identical across all three versions.
- The changed block reports a count of 26.
- The changed list contains 26 indices.
- 7 plus 26 equals 33, which matches the compared index count.
- The unchanged set and the changed set do not overlap.

## Unchanged indices

| Index | Entry IDs | Size | SHA-256 |
|---:|---|---:|---|
| 0 | 3842, 3842, 3842 | 4096 | ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7 |
| 2 | 1, 1, 1 | 624448 | 018eef055292061918cabb112171df855b1461e9960b76b626bf1500801b51d9 |
| 9 | 15, 15, 15 | 131 | 45de60c371172469a2587c80ec0baf14857017df3ec042bda0a33544a0d927f7 |
| 10 | 17, 17, 17 | 240128 | 65c51aa8990f1cac3ce1fa6aab4350f44c1c099f3b47336f2bc105f06ac5eff0 |
| 12 | 18, 18, 18 | 47616 | cdb7d84b0fdceb57f168b53858d31127d3d80a9d6c43bf855b90ba6003d891da |
| 22 | 11, 11, 11 | 21132448 | 17fbdec1f1d634ba7988dbbbcff97076f2abdb92bba40daeae787a09df415b64 |
| 28 | 513, 513, 513 | 1194496 | 7186384ff44a663e6b4c6bf4ce478146abfed1b6c1dd6f473e2b73ede4f0fff2 |

The unchanged indices are 0, 2, 9, 10, 12, 22 and 28.

## What the equality proves

The audit method treats an index as equal only when size and SHA-256 match. That match proves byte identity inside the recorded hash scope. The scope is the entry bytes that the audit hashed. A matching hash is a statement about those bytes. It is not a statement about the rest of the file.

## What the equality does not prove

- It does not name a firmware component.
- It does not map an index to a subsystem or module.
- It does not show that two entries serve the same function.
- Entry IDs are table labels. They are not component identifiers.
- A changed index only means the recorded bytes differ. It does not say what changed.

## Limits of the source

The JSON contains no component names, roles or segment descriptions. Any claim about firmware components needs a separate source. This note stops at the recorded hash scope.
