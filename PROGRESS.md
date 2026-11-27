# Project progress

Updated 2026-11-27. This is an operational handoff, not the hardware facts graph. Hardware claims belong in `docs/facts/data/*.yaml` with evidence links.

## Verified in this session

- Both local repositories are clean at start. GitHub access to `gottmoz/amdgpu-wddm` and `gottmoz/BC-250-Windows-graphics-driver` is authenticated with admin permission.
- `amdgpu-wddm` has remote branches `dev/build-ci` and `research/ps5-firmware`. Both initially point to `9e9702ea0`.
- Local KMD release `CompileOnly` built and linked on Windows with the installed 10.0.26100.0 WDK/SDK and VS tools. SHA-256 of `bc250kmd.unsigned.sys`: `11E6DAF5E2A1D733688557BC0D52E6FDCDCB09D32C9CD16F7869DF1820B624F4`. Output is outside the repository at `D:\BC250-Development\scratch\kmd-compile-only`.
- Build gates passed: stack budget, release flavour, and static KMD PE layout. Static layout does not establish runtime HVCI acceptance.
- Host tests passed: regcalc 10, diagusb 35, facts 17. `gen_facts.py --check` passed with 975 facts and 449 edges.
- Strata 0.2.9 (engine build 0.1.55) serves `qwen3.8-flash-next-q2_0` at local port 8080. `/v1/models` and a forced OpenAI chat tool call worked.
- GitHub Actions run [45675073663](https://github.com/gottmoz/amdgpu-wddm/actions/runs/45675073663) passed the pinned kit download, KMD `CompileOnly`, and host tests on `windows-2022` at commit `c61942caf`.
- The local Strata supervisor completed task S001 after the original task was split. Its source inventory was reviewed and adjusted for the repository writing gate.

## In progress

- D3D12 development UMD x64 and x86 rows passed host builds on 2026-11-27. Their hashes, source pins, validation limits, and the vkd3d BuildTree blocker are recorded in `docs/research/strata/d3d12-dev-build-2026-11-27.md`. The engine rows are not built.
- An existing RADV x64 DLL was rechecked with `dumpbin`: PE machine x64, three Vulkan ICD exports, SHA-256 `DD084C00159F047E7126649C25DA07EE534167564047256F374517567777E09E`. The incremental Ninja command did not compile or link it in this session. See `docs/research/strata/radv-x64-artifact-verification-2026-11-27.md`.
- Survey PS5 Linux and BC5 source projects on `research/ps5-firmware`.
- Inventory any permitted local firmware images before attempting static analysis. No full PS5 or BC-250 firmware image has been identified in this workspace.

## Constraints

- No firmware flash, driver installation, reboot, or voltage change without approval.
- No proprietary firmware or credentials in Git. Do not change `main` automatically.
