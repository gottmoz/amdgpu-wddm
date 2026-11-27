# Nagi compiled artifact audit

Scope: Static PE metadata, exports, direct dependencies, and SHA-256 for local scratch outputs. Hashes identify files only.

## RADV Vulkan ICD

- x64 `vulkan_radeon.dll`: AMD64, 22,586,368 bytes. SHA-256: `dd084c00159f047e7126649c25da07ee534167564047256f374517567777e09e`.
- x86 `vulkan_radeon.dll`: x86, 20,383,744 bytes. SHA-256: `effe253804edd8ab099a16636bd586068b50319df272941e4fbd0e7e992277e5`.
- Both export `vk_icdGetInstanceProcAddr`, `vk_icdGetPhysicalDeviceProcAddr`, and `vk_icdNegotiateLoaderICDInterfaceVersion`.
- Direct dependencies are `api-ms-win-core-synch-l1-2-0.dll`, `dwmapi.dll`, `KERNEL32.dll`, `USER32.dll`, and `GDI32.dll`.

## Development Zink D3D10 UMD

- x64 `bc250d3d_zink.dll`: AMD64, 13,317,120 bytes. SHA-256: `d89e7d31353da30f949d89d088aa67704dca0e842910c690adae5e8c0703eb3e`.
- x86 `bc250d3d_zink.dll`: x86, 12,041,728 bytes. SHA-256: `39a58c149fdd9520a89d5652016e8d3650b117523e19f5fd223dc33539eaccf8`.
- Both export `OpenAdapter10` and `OpenAdapter10_2`. Neither exports the legacy `OpenAdapter` name.
- Direct dependencies are `api-ms-win-core-synch-l1-2-0.dll`, `KERNEL32.dll`, `USER32.dll`, and `GDI32.dll`.

## Kernel driver

- `bc250kmd.unsigned.sys`: AMD64 native image, 1,278,976 bytes. SHA-256: `11e6daf5e2a1d733688557bc0d52e6fdcdcb09d32c9cd16f7869df1820b624f4`.
- It has no export directory. Direct dependencies are `ntoskrnl.exe`, `HAL.dll`, and `cng.sys`.
- Its PE receipt marks section layout as passing. HVCI acceptance is explicitly false.

## Provenance and limits

- Mesa recipes name source commit `05e6c9622e135ac2aeaf56ec70222642627e2162`. The source tree had 63 modified and 15 untracked entries.
- Its recorded diff hash covers tracked files only. The KMD PE receipt records no source commit.
- All five files are unsigned scratch outputs. No complete package was assembled, and no runtime or hardware test was run.
