# tester.39 workspace input recovery

The manifest at 47debf029 pins these consumers and prerequisite producers.

| Workspace input | Producer and identity | Consumers |
|---|---|---|
| `scratch/llvm2312-build` | `tools/build/build-llvm.ps1 -Arch x64`, LLVM tag `llvmorg-23.1.2` at `85ac560262434c9ccfc0c183ec22d4138ed647fb`; MSVC Release /MT and Ninja; retain build-tree llvm-config and libraries. | cpu-x64-rel, cpu-x64-lab |
| `scratch/wow64/llvm2312-x86-build` | Same recipe with `-Arch x86`, separate build and install paths; expect i686-pc-windows-msvc. | cpu-x86-rel, cpu-x86-lab |
| `scratch/t36/f11-rocm/release/hip-layer1-6115ab35` | `compute/hip/build.ps1` from `6115ab3527d2e79ae0287dd91d003e9def8dc375`; requires MSVC and SDK x64 headers and libraries. Produces `bc250hsa.lib`. | extra-hip-release, extra-hip-lab, extra-rocm-release, extra-rocm-lab |
| `scratch/t36/f11-rocm/rocm-input` | Stage one upstream AMD TheRock build as documented by `compute/hip/build-rocm-payload.ps1` at `c434348f41daa358e896483116b486b5bbf9e271`. Obtain the original `therock.json` or verified package record, matching DLLs, SDK headers and HIP import census. The recipe checks both DLL hashes against that record. | extra-rocm-release, extra-rocm-lab |
| `scratch/t36/f11-rocm/tmp/kit8-qwen-split` | Recover the preceding payload manifest. The recipe requires `payload.json` with SHA-256 `1d212df471d25b1e41c92f0d123a81abf8524ac8778e3c59fc2f837a37605bc2`. | extra-rocm-release, extra-rocm-lab |

The official LLVM tag dereferences to the documented commit. Complete both LLVM builds with the documented recipe and verify each llvm-config before relying on its tree. Recover the exact TheRock and history inputs from the prior build records.

## Strata handoff

The coordinator reads the checkout branch with `git branch --show-current`. Its GitHub intake requires the task branch to match the worker checkout and allows `research/ps5-firmware` and `research/xbox-firmware`. The current `agent/strata-v2` checkout cannot accept those tasks. Two offline fixture tests passed for intake scope and deduplication, and for delayed retry eligibility.

For a separate authorized run, provision a checkout of the approved research branch with the reviewed V2 daemon present. Confirm the checkout branch, use a separate runtime directory and launch under the approved research configuration before submitting a matching task. The existing run was left in place. The saved endurance snapshot reported 13,539.5 work seconds and 22,500.1 idle seconds against a 28,800-second target.
## Host validation

The LLVM checkout completed at the pinned commit. Both ConfigureOnly runs exited 0, with 28 x64 and 29 x86 cache values matching the recipe. These trees still need compilation and llvm-config validation.

The pinned HIP layer 1 recipe exited 0 with its host validation enabled. The local bc250hsa.lib SHA-256 is 4D07C234A3EDA71CCE55D6DE01DA6D262BD935EE16F95B2B8FBA3E874D948EDD.

tester.39 -Plan exited 1 with complete context 7F6244B9B413FCDC60CA2EC3BF390476F7701F0B4AF1F495DD9F27DDF296FE90. The four remaining diagnostics are absent TheRock and history inputs for each of extra-rocm-release and extra-rocm-lab. The plan checks these paths and does not establish that the configured LLVM trees contain compiled libraries.
