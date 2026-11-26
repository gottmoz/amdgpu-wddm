# Nagi build dependency status

This note records the latest release-set dependency check performed on 2026-11-26.
It describes environment state only. It does not claim a complete release build.

## Verified progress

- `build-release-set.ps1 -Plan` ran with `tools/release/release-tester.39.json` and wrote its context to `D:\BC250-Development\scratch\release-plan-after-sdk-x86-v2`.
- The Microsoft Windows SDK CPP x86 NuGet package `10.0.26100.6584` was downloaded to scratch, verified with NuGet signature verification, and extracted outside Git to `D:\BC250-Development\toolchain\nuget\microsoft.windows.sdk.cpp.x86`.
- Package file: `Microsoft.Windows.SDK.CPP.x86.10.0.26100.6584.nupkg`. Size: 49,788,719 bytes. SHA-256: `47BFC24AE5D594B62154ACC062E04F7A0E54FF1534A50659F71CB40E878EE9CF`.
- `c\um\x86\kernel32.lib` exists in the extracted package and is 329,914 bytes.
- The NuGet CLI used for verification was the official `nuget.exe`, Authenticode-valid and signed by Microsoft Corporation. Its SHA-256 was `D4DDB222CB8FCA8200B59E82286C0CBA9C29B4FCE6F9835FDFA54E67C9483D07`.
- The same dependency-context capture now recognizes the x86 SDK path. The release-set planner still stops before planning/build because required identity inputs are incomplete.

## Remaining blockers from the captured context

The generated `build-context.json` reports `complete: false`, with 19 required inputs absent and two paths as unsupported links:

- Reference sources: `ref/AGS_SDK-v6.3.0`, `ref/ddi-display`, and `ref/display-library__WARN-EULA-in-docs-only-headers-MIT/include`.
- Public AMD firmware inputs outside Git: `cyan_skillfish2_ce.bin`, `me.bin`, `mec.bin`, `mec2.bin`, `pfp.bin`, `rlc.bin`, `sdma.bin`, and `sdma1.bin` under the declared `ref/linux-firmware.../amdgpu` root.
- Linux source inputs: `amdgpu_device.c` and `amdgpu_drv.c` under `ref/linux-src/drivers/gpu/drm/amd/amdgpu`.
- Toolchains: `toolchain/llvm-23.1.4-win64`, `toolchain/llvm-amdgpu-22.1.8/mingw64` and its `bin` directory, and `toolchain/mingw-w64-tools-14.0.0.r532/ucrt64/bin`.
- NuGet/WDK inputs: `microsoft.direct3d.d3d12.1.619.6/build/native/include` and `wdk-28000.2526-um/c/Include/10.0.28000.0/um`.
- The context additionally flags `toolchain/nuget/microsoft.windows.sdk.cpp/c` and `toolchain/nuget/microsoft.windows.wdk.x64/c` as unsupported links. These are not the extracted x86 SDK directory above.

The context capture contains a host snapshot and declared input inventory. Its own `limits` state that it is not a hermetic dependency proof. Re-run the documented plan after resolving inputs, using the same output directory when retrying, and inspect the plan before compilation.

## Safety and scope

No driver was installed, signed, deployed, or loaded. No hardware writes were performed. Downloaded package and toolchain files remain outside Git. AMD firmware blobs are not included in this repository.
