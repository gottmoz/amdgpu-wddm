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
- Task S004 produced a historical SMU source map. Its first validation failed on writing style. The reviewed note now passes doclint and directs current limits to `docs/hardware.md`.
- The Strata supervisor now permits 100 tool rounds per task and compacts older tool actions. A mocked 18-round run completed with at most 15 context messages.
- GitHub Actions run [45678032319](https://github.com/gottmoz/amdgpu-wddm/actions/runs/45678032319) passed on `dev/build-ci` after the 100-round change. It completed the KMD build and host-test steps on Windows.

## In progress

- Compare PS5 Linux memory-map source with the BC-250 source map at pinned revisions.
- Identify a lawful complete firmware image before attempting a PS5 and BC-250 binary comparison. No such image has been identified in this workspace.

## Constraints

- No firmware flash, driver installation, reboot, or voltage change without approval.
- No proprietary firmware or credentials in Git. Do not change `main` automatically.
- 2026-11-26: User-provided PS5 files found in `D:\BC250-Development\ps5 pups`. SHA-256 and byte counts are in `PS5_DUMP_INVENTORY.json`. Source acquisition provenance was not supplied. Originals remain unchanged.
- Read-only PUP table scan found 33 bounded entries in each of 11.00, 11.20 and 11.40 named files. Seven entry positions have identical packed hashes across the three files. Forty bounded ELF64 x86-64 candidates were copied to `D:\BC250-Development\scratch\ps5-ghidra` and analyzed with Ghidra 12.1.4. All 40 imports exited successfully. Ghidra reported six functions across six `kdata1001.bin` ELF candidates and zero functions across 34 PUP ELF candidates. Detailed reports and logs stay outside Git.
- No complete PUP entry hash matches the eight public Cyan Skillfish microcode hashes. This does not exclude nested components. No PSP, SMU, GPU microcode, memory-init or platform-init component identity is verified.

## Productivity intervention – 2026-11-26 10:18 UTC

- Reviewed and dispositioned all 33 outstanding result/review artifacts. Corrected the PS5 consistency note, rejected repetitive review tasks, and recorded each decision in `STRATA_REVIEW_DIGEST.md` and `TASK_QUEUE.json`. S001–S005 remain recorded as previously source-reviewed.
- Deterministic PS5 inventory summary: 40 candidates, all 40 bounds-valid; Ghidra metadata reports 34 zero-function and six positive-function candidates; 40 distinct candidate hashes. This is inventory metadata only, not component identification or new disassembly.
- Added `tools/firmware/elf_inventory_summary.py` and synthetic tests. A focused suite passed 34 tests, including binary parser, Strata daemon, V2 smoke, inventory summary and auto-publication gate tests.
- Fixed review-loop starvation by disabling automatic review generation; scheduler rotates between available areas and continues a running task before taking new work.
- Added a restricted automatic-publication policy: Python/JSON artifacts in tools directories only, explicit unittest verification, declared outputs, safe branch, empty index and credential scan. Git operations were mocked in regression tests.
- Added 12 concrete PS5, Nagi and Strata implementation templates; 12 ready tasks are queued. The running queue is being handled by the detached daemon.
- Installed and verified in `D:\BC250-Development\scratch\py`: Meson 1.12.0, Mako 1.4.1, MarkupSafe 3.0.3, PyYAML 6.0.3, packaging 25.0. This does not complete Nagi's other toolchain dependencies or a full build.
- Restarted only the daemon through its existing watchdog. Endurance state was preserved: start `2026-11-26T08:29:21Z`, target 28,800 seconds; latest local counters before new worker execution: 4,259.9 work seconds, 1,350 idle seconds, 74 worker runs. Recovery count: 7.
