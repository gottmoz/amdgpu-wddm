# RADV x64 artifact verification, 2026-11-27

## Configuration and artifact

The pinned Meson build directory is `scratch/mesa-radv-pinned-configure`. Its source checkout is
Mesa commit `05e6c9622e135ac2aeaf56ec70222642627e2162`. Meson records `vulkan-drivers=amd`,
`platforms=windows`, `llvm=disabled`, and `amd-use-llvm=false`.

The existing `vulkan_radeon.dll` is 22,586,368 bytes, dated 2026-11-27 07:40 UTC. Its SHA-256 is
`DD084C00159F047E7126649C25DA07EE534167564047256F374517567777E09E`. `dumpbin /headers` reports
x64. `dumpbin /exports` reports the three Vulkan ICD exports: `vk_icdGetInstanceProcAddr`,
`vk_icdGetPhysicalDeviceProcAddr`, and `vk_icdNegotiateLoaderICDInterfaceVersion`.

## Build attempt and limits

The first incremental Ninja invocation from a plain PowerShell session failed because `cl` was not
on `PATH`. Under Visual Studio 18.3.2's x64 developer environment, Ninja exited successfully after
running only the `src/git_sha1.h` generator. The dry run still listed five RADV actions, but no C
compile or link ran in that invocation. The DLL above predates it, so this session verified its PE
metadata and hash. It did not produce a fresh RADV build. Ninja's explain output showed the generated
header's phony dependency as dirty. Why the real build skips the dependent actions remains open.

No ICD runtime test or hardware test was performed. The DLL and logs remain in local scratch.
