# Project progress

Updated 2026-11-25. This is an operational handoff, not the hardware facts graph. Hardware claims belong in `docs/facts/data/*.yaml` with evidence links.

## Verified in this session

- Both local repositories are clean at start. GitHub access to `gottmoz/amdgpu-wddm` and `gottmoz/BC-250-Windows-graphics-driver` is authenticated with admin permission.
- `amdgpu-wddm` has remote branches `dev/build-ci` and `research/ps5-firmware`. Both initially point to `9e9702ea0`.
- Local KMD release `CompileOnly` built and linked on Windows with the installed 10.0.26100.0 WDK/SDK and VS tools. SHA-256 of `bc250kmd.unsigned.sys`: `11E6DAF5E2A1D733688557BC0D52E6FDCDCB09D32C9CD16F7869DF1820B624F4`. Output is outside the repository at `D:\BC250-Development\scratch\kmd-compile-only`.
- Build gates passed: stack budget, release flavour, and static KMD PE layout. Static layout does not establish runtime HVCI acceptance.
- Host tests passed: regcalc 10, diagusb 35, facts 17. `gen_facts.py --check` passed with 975 facts and 449 edges.
- Strata 0.2.9 (engine build 0.1.55) serves `qwen3.8-flash-next-q2_0` at local port 8080. `/v1/models` and a forced OpenAI chat tool call worked.
- GitHub Actions run [45675073663](https://github.com/gottmoz/amdgpu-wddm/actions/runs/45675073663) passed the pinned kit download, KMD `CompileOnly`, and host tests on `windows-2022` at commit `c61942caf`.
- The local Strata supervisor completed task S001 after the original task was split. Its source inventory was reviewed and adjusted for the repository writing gate.
- On `research/ps5-firmware`, task S002 produced a source-based PSP loader note. The note was reviewed against `bc250_psp.c` and adjusted for the writing gate.
- Eight public Cyan Skillfish files were fetched outside Git. They matched the manifest sizes and SHA-256 values and passed static header, bounds and CRC checks.
- Ghidra 12.1.4 headless imported and analyzed the locally built unsigned KMD. It exited zero and deleted its temporary project. This verifies the tool route, not PS5 firmware compatibility.
- Task S003 produced a scoped map of ACPI VFCT capture and Driver Store firmware loading. Its first validation failed on writing style. The reviewed note now passes doclint.

## In progress

- Continue bounded source review of the local SMU owner and PS5 Linux memory-map differences.
- Identify a lawful complete firmware image before attempting a PS5 and BC-250 binary comparison. No such image has been identified in this workspace.

## Constraints

- No firmware flash, driver installation, reboot, or voltage change without approval.
- No proprietary firmware or credentials in Git. Do not change `main` automatically.
