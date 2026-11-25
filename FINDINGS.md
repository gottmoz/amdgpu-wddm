# Findings and open questions

## Verified observations

- The repository builds its KMD through `driver/kmd/build.ps1`. `-CompileOnly` compiles and links without catalog creation, signing, or deployment.
- The installed Windows kit has the 10.0.26100.0 kernel headers and libraries. The build used local directory junctions under `D:\BC250-Development\toolchain\nuget` to point at that installed kit. CI will use pinned NuGet packages instead.
- Strata's local API exposes model `qwen3.8-flash-next-q2_0`, a 131072-token context and OpenAI-compatible tool calls. Its server is an owned background instance under profile `launch-q2_0-128k`.
- Ghidra 12.1.4 is installed at `D:\Tools\ghidra_12.1.4_PUBLIC`. `analyzeHeadless.bat` successfully analyzed our unsigned KMD and deleted the temporary project. No PS5 image has been analyzed.
- Visual Studio 2022 Community and Visual Studio 18 BuildTools are installed. `vswhere` selects BuildTools 18.3.2 for the local build. Python 3.14.3, PowerShell 7.6.9 and Git 2.53.0 are available. LLVM tools are absent from PATH.
- The workspace scan found SPI chip-register dumps and GPU ring dumps under `evidence/`. It did not identify a complete PS5 or BC-250 firmware image suitable for Ghidra analysis.
- `tools/firmware/inspect_headers.py` verified header bounds and CRC for all eight manifest-pinned public microcode files. The formats are gfx 1.0, RLC 2.0 and SDMA 1.0. See `docs/research/ps5-firmware-portability.md` for versions and limits.
- `driver/shim/bc250_psp.c` checks bounds and the supported RLC layout before splitting MEC and jump-table payloads. It does not establish compatibility with a PS5 firmware container. See `docs/research/psp-loader-boundaries.md`.

## Hypotheses and research leads

- `docs/research/gfx1013-isa-leads-ps5-decoders.md` contains source leads for PS5 decoder work. It is a lead, not evidence that PS5 firmware can run on the BC-250.
- The feasibility of porting PS5 system software has not been established. Check boot chain, trust/signature requirements, firmware interfaces, GPU microcode and memory topology with primary sources and permitted static artifacts.

No new hardware fact is asserted here. Use `docs/facts/data/*.yaml` for measured claims.
