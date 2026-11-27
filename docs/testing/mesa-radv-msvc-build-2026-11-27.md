# RADV MSVC build result

## Result

The pinned RADV target built on 27 November 2026 with MSVC 19.50.35725 and the Windows 10.0.26100.0 SDK. The Nagi `build-mesa.ps1` command exited with code 0. The configured target was `src/amd/vulkan/vulkan_radeon.dll`.

The output is an x64 PE DLL with 22,586,368 bytes. Its SHA-256 is `D4175A7CC72DDAB639A323E6778B8DB666C9965DE0DF93627E0DE7C1091C1566`. `dumpbin /headers` reported machine `8664`. `dumpbin /dependents` listed `api-ms-win-core-synch-l1-2-0.dll`, `dwmapi.dll`, `KERNEL32.dll`, `USER32.dll` and `GDI32.dll`.

## Inputs

- Mesa commit `05e6c9622e135ac2aeaf56ec70222642627e2162` on the D-Ogi `amdgpu-wddm/radv-wddm2` branch.
- Nagi patch `experiments/E33-m12-applications/mesa05-wddm2.patch`, SHA-256 `6e4e73ec2f27c6e19761675e06b7d5d279d0b76c3432e36e072adf276b9c71af`.
- RADV configuration from `tools/build/mesa-configs.json`: Windows, AMD Vulkan only, ACO, LLVM disabled, static CRT.
- Build log: `D:\BC250-Development\scratch\mesa-radv-msvc-build.log`. The build `recipe.json` is in `D:\BC250-Development\scratch\mesa-radv-pinned-configure`.

## Local build fixes

The pinned source was changed only in the scratch worktree. `ASSERTED` was added to locals that MSVC C4189 found unused because release assertions were disabled. The MSVC-only `/NODEFAULTLIB:libcmt.lib` option was removed from `src/amd/vulkan/meson.build`. With that option present, the link failed with 149 unresolved CRT and runtime symbols. After its removal, the link completed and the DLL imports only the listed system libraries.

These scratch changes are not part of the Nagi repository or the pinned Mesa patch. Review and upstream the source fixes before treating this as a reproducible supported build.

## Limits

This is a host compile and link result. No driver installation, hardware load, GPU execution, Vulkan runtime test or BC-250 validation was performed. The DLL is not a release package.


