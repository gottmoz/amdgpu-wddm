# Current task

Branch: `dev/build-ci`.

1. Compare the fresh vkd3d x64 and x86 outputs against their pinned release recipes and package dependencies. Keep the historical tester.39 manifest unchanged.
2. Explain why the RADV incremental build reports five dry-run actions but runs only the generated-header step. Perform a fresh compile and link after understanding the cause.
3. Recheck exact TheRock and prior `kit8-qwen-split` provenance for the blocked tester.39 rows. Do not fabricate either input or alter its pins.
4. Continue source-based research on `research/ps5-firmware` when the build lane is checkpointed.

The local and GitHub KMD `CompileOnly` runs passed. The D3D12 shell and vkd3d engine x64/x86 development rows passed their documented builds. Host tests and the engine ABI-only checks passed. Historical tester.39 planning still stops on four missing TheRock and history inputs. See `PROGRESS.md` and the linked build report for exact results. The hardware is unavailable, so no device or hardware validation was run.
