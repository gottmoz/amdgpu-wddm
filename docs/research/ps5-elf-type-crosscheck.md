# PS5 ELF e_type cross-check

## Scope
This note compares three declared sources. It reports only what those sources state.
It does not inspect firmware binaries. It does not identify components. It does not describe Sony loader behavior.

## Sources and revisions
- `awake-devel/pkg-to-anyps5` at `2e9b12267840f9777f8d825335c4b4938160d9c4`, file [`src/selfelf.rs`](https://github.com/awake-devel/pkg-to-anyps5/blob/2e9b12267840f9777f8d825335c4b4938160d9c4/src/selfelf.rs).
- `OpenOrbis/create-fself` at `f2da6229684ce320f673c06fceac9c218f621788`, file [`pkg/oelf/PS4Constants.go`](https://github.com/OpenOrbis/create-fself/blob/f2da6229684ce320f673c06fceac9c218f621788/pkg/oelf/PS4Constants.go).
- `shadps4-emu/shadPS4` at `78a8a54dd5a25b05275d4918bd52d30f1511bbed`, file [`src/core/loader/elf.cpp`](https://github.com/shadps4-emu/shadPS4/blob/78a8a54dd5a25b05275d4918bd52d30f1511bbed/src/core/loader/elf.cpp).
- The same shadPS4 revision defines the SCE ELF values in [`src/core/loader/elf.h`](https://github.com/shadps4-emu/shadPS4/blob/78a8a54dd5a25b05275d4918bd52d30f1511bbed/src/core/loader/elf.h).
- Limitation: the source projects are PS4 or PS5 tools, not Sony loader specifications.

## Direct source statements

### pkg-to-anyps5 `src/selfelf.rs`
- Doc comment on `elf_type`: "The ELF type field: 0xfe10 for the main executable, 0xfe18 for a module."
- Code: `pub fn elf_type(elf: &[u8]) -> Option<u16> { le16(elf, 0x10).ok() }`. It returns the raw little-endian u16 at offset 0x10.
- No branch on `0xfe10` or `0xfe18` appears in the fetched file. The values are documentation, not enforced logic.
- `SELF_MAGIC_PS4 = [0x4f, 0x15, 0x3d, 0x1d]` and `SELF_MAGIC_PS5 = [0x54, 0x14, 0xf5, 0xee]`.
- `PT_SCE_VERSION = 0x6fff_ff01`.
- `unwrap` rejects encrypted or compressed SELF segments.
- `unwrap` zeroes `e_shoff`, `e_shentsize`, `e_shnum` and `e_shstrndx` in the output ELF.

### OpenOrbis `pkg/oelf/PS4Constants.go`
- File header: "This file contains constants that are specific to SCE types. This includes ELF types, program header types, and dynamic table tags."
- `const ET_SCE_EXEC_ASLR = 0xFE10`
- `const ET_SCE_DYNAMIC = 0xFE18`
- The file names 0xFE10 as an ASLR exec type. It does not call it a main executable.
- The file names 0xFE18 as a dynamic type. It does not call it a module.

### shadPS4 `src/core/loader/elf.cpp`
- `GetType` switches over `ET_NONE`, `ET_REL`, `ET_EXEC`, `ET_DYN`, `ET_CORE`, `ET_SCE_EXEC`, `ET_SCE_STUBLIB`, `ET_SCE_DYNEXEC` and `ET_SCE_DYNAMIC`.
- `IsElfFile` accepts `ET_SCE_EXEC`, `ET_SCE_DYNEXEC` and `ET_SCE_DYNAMIC`. It also requires x86-64 and specific OS ABI fields.
- `IsSharedLib` returns true for `ET_SCE_DYNAMIC`.
- `src/core/loader/elf.h` maps `ET_SCE_EXEC` to `0xfe00`, `ET_SCE_DYNEXEC` to `0xfe10`, and `ET_SCE_DYNAMIC` to `0xfe18`.
- These are shadPS4 implementation details. They do not establish Sony loader behavior or PS5 compatibility.
- `GetMachine` accepts only `EM_X86_64`.

## What the labels do establish
- Both the PS5-specific file and the PS4-oriented file use the same numeric pair 0xFE10 and 0xFE18 for SCE ELF types. Confidence: high, because both files state it directly.
- pkg-to-anyps5 maps 0xFE10 to a main executable and 0xFE18 to a module. Confidence: medium, because it is a comment and not code that branches on the value.
- OpenOrbis maps 0xFE10 to `ET_SCE_EXEC_ASLR` and 0xFE18 to `ET_SCE_DYNAMIC`. Confidence: high for the names, low for the implied semantics.
- shadPS4 accepts `0xfe10` and `0xfe18` under its DYNEXEC and DYNAMIC names. Confidence: high for this source mapping, low for applying it to PS5.
- OpenOrbis calls `0xfe10` `ET_SCE_EXEC_ASLR`, while shadPS4 calls it `ET_SCE_DYNEXEC`. This naming difference limits semantic conclusions.

## Cross-platform inference, not source statements
- Applying OpenOrbis names to PS5 files is inference. The file is named `PS4Constants.go` and states no PS5 scope. Confidence: low.
- Applying shadPS4 names to PS5 files is also inference. Its code is a PS4 emulator implementation. Confidence: low.
- Treating the pkg-to-anyps5 comment as a PS5 ABI rule is inference. The file gives no PS5 specification reference. Confidence: low.
- The shared numeric pair suggests a common SCE ELF convention across PS4 and PS5 tooling. Confidence: medium as a convention, none as a verified platform fact.

## What the labels do not establish
- They do not prove that PS5 uses the same e_type values as PS4.
- They do not identify any firmware component, subsystem or function.
- They do not describe how a Sony loader interprets the value.
- They do not say whether a file is signed, self-verified or loadable.
- They do not separate a main executable from a module beyond the naming in one comment.

## The 34 local PS5 ELF candidates
- `PS5_ELF_INVENTORY.json` has 40 rows: 34 PUP candidates and six `kdata1001.bin` candidates.
- The refreshed inventory records raw e_type, mapped executable segments and their hashes for every row.
- The 34 PUP rows contain 12 values of 0xFE10 and 22 values of 0xFE18. Every candidate hash matches the earlier inventory.
- Each PUP candidate has one bounded executable PT_LOAD segment. All 34 segment hashes are unique.
- Twelve entry points are nonzero and map into executable segments. The other 22 entry fields are zero.
- The 0xFE10 and 0xFE18 values match the pkg-to-anyps5 comment labels. This is a value match, not a component identity claim.
- The labels cannot establish Sony loader behavior or candidate roles. No official loader specification was found in these sources.

## Bounded next step
- Investigate why Ghidra reported zero functions for the 34 candidates despite bounded executable segments.
- Compare the existing import settings and warnings before any candidate-specific reimport.
- Do not assign roles from e_type alone.
- Do not repeat the full Ghidra batch.
