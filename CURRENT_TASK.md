# Current task

Branch for current research checkout: `research/xbox-firmware`.

1. Extend the existing Strata supervisor with a GitHub inbox, heartbeat, locking and recovery. Run it in its separate worktree.
2. Inventory Nagi build dependencies with `build-release-set.ps1 -Plan` and preserve the output directory.
3. Continue PS5 tasks in `TASK_QUEUE.json` and Xbox tasks in `XBOX_TASK_QUEUE.json`. Review all generated findings before publication.
4. Identify a lawful complete firmware image before any PS5 and BC-250 binary comparison. Task S005 needs such an input.

The local and GitHub KMD `CompileOnly` runs passed. Ghidra headless was verified on our own KMD. See `PROGRESS.md` for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
