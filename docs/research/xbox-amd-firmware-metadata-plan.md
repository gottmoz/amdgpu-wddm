# Xbox and AMD firmware metadata comparison plan

Scope: metadata only. No firmware bytes, headers, disassembly, or hardware access.

## Declared sources

- `XBOX_FIRMWARE_INVENTORY.json`
- `tools/firmware/cyan_skillfish2.json`

## Observations from the declared files

1. The inventory contains two entries:
   - `OSU1`: operating-system update package.
   - `CYAN_SKILLFISH2_PUBLIC_MICROCODE`: public AMD GPU microcode set.

2. `OSU1` metadata:
   - Official entry: `https://www.xbox.com/xboxone/osu1`
   - Resolved download: `https://download.microsoft.com/download/524a2f3b-271e-42a2-befe-913d3cc76c0e/OSU1.zip`
   - HTTP method observed: `HEAD`
   - Size: `6,286,062,048 bytes`
   - Last modified: `2026-11-06T21:38:03Z`
   - SHA-256: `null`
   - Version: `null`
   - Status: `SOURCE-DERIVED`. This task did not repeat the HTTP request.
   - Inventory note: update package, not a complete boot firmware image.

3. `CYAN_SKILLFISH2_PUBLIC_MICROCODE` metadata:
   - Manifest: `tools/firmware/cyan_skillfish2.json`
   - Source: `linux-firmware`, `amdgpu/cyan_skillfish2_*.bin`
   - Commit: `2b8daaf611fbade74f26a5b58ec1defe6a02f5e0`
   - File count: `8`
   - Status: `VERIFIED`
   - Local files are outside Git under `workspace scratch/firmware-static`.
   - Manifest lists per-file sizes and SHA-256 values.
   - `cyan_skillfish2_mec.bin` and `cyan_skillfish2_mec2.bin` have identical SHA-256 values.

## Comparison model

Use metadata fields only:

| Field | Public AMD microcode | Xbox OS update package |
|---|---|---|
| Identifier | `cyan_skillfish2_*` | `OSU1` package ID |
| Source | linux-firmware commit | Microsoft/Xbox URL |
| Provenance | LICENSE/WHENCE declared | URL and HTTP metadata only |
| Size | per-file bytes | package bytes |
| Hash | per-file SHA-256 | currently absent |
| Version | commit-derived | currently absent |
| Status | `VERIFIED` | `SOURCE-DERIVED` |
| Kind | GPU microcode | OS update package |

These are different artifact types. The current fields cannot establish that the update
contains any AMD microcode or that the platforms share a firmware component.

## Matching rules

1. **Exact identity match**
   - Same SHA-256, same filename, same declared source.
   - Apply only to two files of the same component type. A matching hash establishes byte
     identity, not platform compatibility.

2. **Provenance match**
   - Same upstream repository, commit, or license declaration.
   - This establishes source provenance, not byte identity.

3. **Structural match**
   - Same component name, size, or role, such as `ce`, `me`, `pfp`, `rlc`, `sdma`.
   - This is a search lead, not a match.

4. **Package containment hypothesis**
   - An Xbox update package may contain AMD microcode files.
   - Do not infer containment from size or naming alone.
   - Requires extracted manifest metadata, file listing, or published release notes.

## Xbox package identifier handling

For package identifiers such as `OSU1`:

- Record URL, HTTP status, size, last-modified date, and available version metadata.
- Do not assign AMD microcode identity unless a manifest or published metadata explicitly names it.
- Treat missing SHA-256 as unresolved, not as mismatch.
- Separate:
  - OS update package
  - embedded firmware component
  - public AMD microcode blob
  - Xbox boot firmware

## Recommended next metadata-only actions

1. Add a normalized schema for firmware entries:
   - `id`
   - `kind`
   - `source_url`
   - `component_name`
   - `version`
   - `sha256`
   - `size_bytes`
   - `provenance`
   - `status`
2. Populate `OSU1` only from public release notes, package manifests, or verified HTTP metadata.
3. Keep `cyan_skillfish2` entries as public AMD microcode references.
4. Mark any Xbox-to-AMD microcode relationship as hypothesis until a manifest or hash confirms it.

## Hypotheses, not verified facts

- The OSU1 archive may contain AMD GPU microcode or related firmware components.
- Xbox firmware identifiers may map to public AMD microcode names.
- Identical component sizes could indicate the same microcode family, but this is not sufficient evidence.

## Boundary

This plan does not inspect binary firmware, compare bytes, parse headers, or validate executable content.
