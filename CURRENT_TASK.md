# Current task

Branch: `dev/build-ci`.

1. Build the vkd3d x86 engine row from its documented x86 source revision. The x64 `ddi-engine` row now builds and passes both host tests. Leave the historical tester.39 manifest unchanged.
2. Explain why the RADV incremental build reports five dry-run actions but runs only the generated-header step. Perform a fresh compile and link after understanding the cause.
3. Fix branch-aware Strata backlog replenishment so the Nagi and PS5 workers can receive useful tasks on their approved branches.
4. Continue source-based research on `research/ps5-firmware` when the build lane is checkpointed.

The local and GitHub KMD `CompileOnly` runs passed. The D3D12 shell x64/x86 development rows also passed host builds. The vkd3d engine rows remain blocked before compilation. See `PROGRESS.md` and the linked build report for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
