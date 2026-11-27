# Findings and open questions

## Verified observations

- The development-only D3D12 shell rows built for x64 and x86 at pinned source commit `747c1aa0`. Their SHA-256 values and host-test scope are in `docs/research/strata/d3d12-dev-build-2026-11-27.md`. The two vkd3d engine rows did not compile. BuildTree stopped during nested submodule setup.
- The existing RADV x64 DLL has PE machine x64 and the three Vulkan ICD exports. Its SHA-256 and the unsuccessful no-op incremental-build attempt are recorded in `docs/research/strata/radv-x64-artifact-verification-2026-11-27.md`. A fresh compile or link was not observed in this session.
- Initializing the recursive submodules at the exact commits recorded in the local vkd3d-proton source checkout resolved the BuildTree setup failure. The x64 `ddi-engine` and x86 `ddi-engine-lto` configurations built successfully. Cache-policy, compile-admission and ABI-only host tests passed for both architectures. The ABI-only test did not create a Vulkan device. See `docs/research/strata/vkd3d-x64-build-2026-11-27.md`.
- The repository builds its KMD through `driver/kmd/build.ps1`. `-CompileOnly` compiles and links without catalog creation, signing, or deployment.
- The installed Windows kit has the 10.0.26100.0 kernel headers and libraries. The build used local directory junctions under `D:\BC250-Development\toolchain\nuget` to point at that installed kit. CI will use pinned NuGet packages instead.
- Strata's local API exposes model `qwen3.8-flash-next-q2_0`, a 131072-token context and OpenAI-compatible tool calls. Its server is an owned background instance under profile `launch-q2_0-128k`.
- Ghidra 12.1.4 is installed at `D:\Tools\ghidra_12.1.4_PUBLIC`. `analyzeHeadless.bat` exists under `support`, but no headless analysis has run yet.
- Visual Studio 2022 Community and Visual Studio 18 BuildTools are installed. `vswhere` selects BuildTools 18.3.2 for the local build. Python 3.14.3, PowerShell 7.6.9 and Git 2.53.0 are available. LLVM tools are absent from PATH.
- The workspace scan found SPI chip-register dumps and GPU ring dumps under `evidence/`. It did not identify a complete PS5 or BC-250 firmware image suitable for Ghidra analysis.

## Hypotheses and research leads

- `docs/research/gfx1013-isa-leads-ps5-decoders.md` contains source leads for PS5 decoder work. It is a lead, not evidence that PS5 firmware can run on the BC-250.
- The feasibility of porting PS5 system software has not been established. Check boot chain, trust/signature requirements, firmware interfaces, GPU microcode and memory topology with primary sources and permitted static artifacts.

No new hardware fact is asserted here. Use `docs/facts/data/*.yaml` for measured claims.
