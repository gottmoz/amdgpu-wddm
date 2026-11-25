# PSP loader boundaries (BC-250 shim)

Evidence: `driver/shim/bc250_psp.c`, `driver/shim/include/amdgpu_ucode.h`. No firmware bytes read.

## Verified: header checks in `bc250_fw_locate()`

- Minimum file size is `sizeof(struct gfx_firmware_header_v1_0)`. Out-of-range IDs and NULL pointers are rejected.
- `size_bytes` must equal the caller-supplied `file_size`. The shim checks this rather than trusting the caller.
- `header_size_bytes <= ucode_array_offset_bytes <= file_size`.
- `ucode_size_bytes != 0` and `<= file_size - array_offset`.
- RLC_G is gated to `header_version_major == 2`, `minor == 0`, and `header_size_bytes >= sizeof(struct rlc_firmware_header_v2_0)`. Later RLC minor versions are refused rather than partially loaded.
- Not checked: `crc32`, `ip_version_*`, `ucode_version`, `ucode_feature_version`.

## Verified: payload splits

- MEC1/MEC2 and their JT halves require gfx header `major == 1` (jt_offset/jt_size are v1.0 fields). Bounds: `jt_size != 0`, `jt_size <= ucode_size/4`, `jt_offset <= ucode_size/4 - jt_size`.
  - CP_MEC1/2: offset = `array_offset`, size = `ucode_size - jt_size*4`.
  - CP_MEC1_JT/2_JT: offset = `array_offset + jt_offset*4`, size = `jt_size*4`.
- SDMA0/1, CE, PFP, ME, RLC_G: whole `ucode_size` at `array_offset`.
- The header slice carries only common, gfx v1.0, rlc v2.0 and sdma v1.0. `le32_to_cpu` and `le16_to_cpu` are identity macros.

## Unanswered PS5 compatibility questions

1. Do PS5 microcode files use the same common-header framing, or a signed/encrypted PSP TA container?
2. Are PS5 RLC headers v2.0, or a later minor with restore-list/IRAM/DRAM images this loader rejects?
3. Is the PS5 PSP IP version compatible with the imported `psp_v11_0_8.c` ring/wait semantics?
4. Does PS5 firmware carry MEC jump tables with the same v1.0 semantics?
5. Is CRC32 expected to be checked before transfer?
6. Is little-endian guaranteed for PS5-sourced blobs?

All PS5 items are hypotheses. None are measured.
