# RADV MSVC build result

## Result

The pinned RADV target built on 27 November 2026 with MSVC 19.50.35725 and the Windows 10.0.26100.0 SDK. The Nagi `build-mesa.ps1` command exited with code 0. The target was `src/amd/vulkan/vulkan_radeon.dll`.

The x64 output is a PE DLL with 22,586,368 bytes. Its SHA-256 is `DD084C00159F047E7126649C25DA07EE534167564047256F374517567777E09E`. `dumpbin /headers` reported machine `8664`. The x86 output is a PE DLL with 20,383,744 bytes. Its SHA-256 is `EFFE253804EDD8AB099A16636BD586068B50319DF272941E4FBD0E7E992277E5`. `dumpbin /headers` reported machine `14C`.

Both outputs export three names, including `vk_icdGetInstanceProcAddr`. Both import `api-ms-win-core-synch-l1-2-0.dll`, `dwmapi.dll`, `KERNEL32.dll`, `USER32.dll` and `GDI32.dll`. These checks confirm file metadata only. They do not confirm Vulkan runtime operation.

## Inputs

- Mesa commit `05e6c9622e135ac2aeaf56ec70222642627e2162` on the D-Ogi `amdgpu-wddm/radv-wddm2` branch.
- Nagi patch `experiments/E33-m12-applications/mesa05-wddm2.patch`, SHA-256 `71f4ff87ac000b2e7adc615a915b394d0446e2bc73cf897c32eb19545821ed56`. The patch adds the x86 dispatch calling-convention fix. The generator file SHA-256 is `4E8906C60B243B8FEF837A867444F4FDCF1387BF43693BAD16B61D75E2337EEB`.
- RADV configuration from `tools/build/mesa-configs.json`: Windows, AMD Vulkan only, ACO, LLVM disabled, static CRT.
- The default glslang directory was missing its executable files. The staged glslang 16.6.0 binaries were copied there from the versioned directory. Their source and destination hashes match.
- A fresh x86 ConfigureOnly run passed with the default glslang path and the 18-option RADV gate.
- Build log: `D:\BC250-Development\scratch\mesa-radv-msvc-build.log`. The build `recipe.json` is in `D:\BC250-Development\scratch\mesa-radv-pinned-configure`.

## Local build fixes

The source worktree needed two MSVC fixes outside the E33 patch. `ASSERTED` marks locals used only by assertions when release assertions are disabled. The MSVC-only `/NODEFAULTLIB:libcmt.lib` option was removed from `src/amd/vulkan/meson.build`. With that option, linking failed with 149 unresolved CRT and runtime symbols.

The first x86 RADV build failed in generated WDDM2 dispatch fallbacks. MSVC reported incompatible function-pointer assignments. The Windows SDK defines these D3DKMT pointer types with `APIENTRY`. The fallback functions used the default C calling convention. The E33 patch now adds `WDDM2_APIENTRY` to those generated functions. It maps to `APIENTRY` on Windows and is empty elsewhere.

A clean worktree at the pinned Mesa commit passed `git apply --check` with the updated patch. The x86 build then passed. The x64 build was rebuilt from the same source and also passed. The recipe's worktree hash covers tracked changes only. It excludes untracked source files. The generator hash above identifies that file.

## Limits

This is a host compile and link result. No driver installation, hardware load, GPU execution, Vulkan runtime test or BC-250 validation was performed. The DLL is not a release package.
