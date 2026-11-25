# Current task

Branch: `research/ps5-firmware`.

1. Trace PS5 Linux memory reservation at pinned source revision and compare it with the BC-250 source map.
2. Identify a lawful complete firmware image before any PS5 and BC-250 binary comparison. Task S005 needs such an input.
3. Keep new Strata tasks small even though the supervisor now permits 100 tool rounds. Review and validate generated notes before GitHub publication.

The local and GitHub KMD `CompileOnly` runs passed. Ghidra headless was verified on our own KMD. See `PROGRESS.md` for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
