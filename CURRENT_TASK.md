# Current task

Branch: `dev/build-ci`.

1. Diagnose the vkd3d BuildTree nested submodule failure and complete the two engine rows without changing the historical tester.39 manifest.
2. Fix branch-aware Strata backlog replenishment so the Nagi and PS5 workers can receive useful tasks on their approved branches.
3. Continue source-based research on `research/ps5-firmware` when the build lane is checkpointed.

The local and GitHub KMD `CompileOnly` runs passed. The D3D12 shell x64/x86 development rows also passed host builds. The vkd3d engine rows remain blocked before compilation. See `PROGRESS.md` and the linked build report for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
