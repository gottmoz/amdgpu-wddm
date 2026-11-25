# Current task

Branch: `dev/build-ci`.

1. Commit and push the reviewed Strata task S001, its supervisor, and the handoff files to `dev/build-ci`.
2. Use `research/ps5-firmware` for source-based research on PSP, SMU, AGESA, VCN, microcode, and memory init.
3. Identify permitted local firmware images. Run Ghidra headless only after identifying an appropriate input and analysis question.

The local and GitHub KMD `CompileOnly` runs passed. See `PROGRESS.md` for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
