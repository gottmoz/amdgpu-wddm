# XVD container: source-derived note (desk research, no binaries read)

Status: source note, not a measurement. Per `docs/01-evidence-rules.md`, nothing here is a
hardware fact for unit A. Hardware claims stay in `docs/facts/data/`.

Sources used (both read on this task):
- `XBOX_RESEARCH.md` - source inventory and limits for XRE03 (container metadata) and XRE04 (boot stages).
- [XanaduXVD README](https://raw.githubusercontent.com/xboxoneresearch/XanaduXVD/50aa0dc89350de580b77f26ade1018b16b0bc1f8/README.md),
  revision `50aa0dc89350de580b77f26ade1018b16b0bc1f8`.

## Verified from the pinned README (documented, as stated by the project)

- XVD = "Xbox Virtual Disk", described as used by Xbox One, Xbox Series, and Windows PC.
- The README states the format "lacks a public standard". The project's stated goal is to
  become a future source of technical documentation. So field names here are implementation
  descriptions, not a normative spec.
- Tool is explicitly "experimental" and "not yet production-ready". The README points to
  `xvdtool` and `XvdTool.Streaming` instead. `XBOX_RESEARCH.md` pins `xvdtool` at `6fc2886`
  and notes its own limit: "Format handling is not proof of Series boot behavior."
- Implemented (checked) user-facing features:
  - dumping the embedded XVD, "usually the game's `era.xvd` or `gameos.xvd`".
  - dumping UserData, "usually the VBI" (linked to the Xbox One Research VBI page).
- Not implemented (unchecked) at this revision: package decryption, drive extraction, XVC
  support, MSIXVC support, UWA/UWP/UW9 support, header editor, signature validation,
  signature manipulation, hash tree verification, hash tree rebuilding, trimming/removal of
  sections.
- Format definitions live in `XVDTypes.h` (with `XVDTypes.cpp` helpers). Parsing logic is in
  `XanaduXVD.cpp` / `XanaduXVD.h`. This note does not read those files or any binary.
- Portability caveat: README says it builds on Windows (Cygwin), Linux and macOS, but
  "little endian machines are not yet supported, need to finish deserialization code".

## What the README implies about container structure (documented intent, not verified fields)

The feature list names a header, signatures, a hash tree, drives, sections, an embedded
XVD, and UserData. The README does not establish their layout or applicability to each
Xbox Series image. It gives no field offsets, sizes, or encodings.

## Unknowns for Series X/S applicability

- The README's claim that XVD is used by Xbox Series is an assertion by the tool author. It
  carries no Series-specific field table, version list, or sample set. `XBOX_RESEARCH.md`
  records the same limit for the Xbox One Research wiki: "Xbox One details need Series X/S
  confirmation."
- Whether the header/signature and hash-tree semantics at `50aa0dc` match Series X/S XVD
  headers is unverified. The tool's own status (decryption, signature validation, hash-tree
  verification all unchecked) means no independent confirmation of those fields is available
  from this source.
- The role of `era.xvd` / `gameos.xvd` and of VBI in a Series X/S boot path is a lead, not an
  established fact. VBI is documented only via the Xbox One Research wiki link, which
  `XBOX_RESEARCH.md` already flags as needing separate Series evidence.
- Endianness handling is incomplete per the README, so any field values read from a Series
  image with this tool at this revision should be treated as provisional.

## Suggested next read-only steps (no hardware, no binaries)

1. Read `XVDTypes.h` as text at the pinned revision to list named fields and their declared
   types, and record which are documented vs inferred.
2. Compare the field list against `xvdtool` at `6fc2886` for agreement on header/hash-tree
   naming. Disagreement is a discrepancy to note, not a conclusion.
3. Keep XRE03 output as a field inventory with "documented / implied / unknown" labels, and
   defer any Series boot-stage claim to XRE04 with Series-specific evidence.


