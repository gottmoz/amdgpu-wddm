# Current task

Branch for current research checkout: `research/xbox-firmware`.

1. Continue the Strata coordinator in its separate worktree. Review generated files before publication and verify the next live heartbeat.
2. Restore the missing Mesa reference source at the recorded revision, then rerun the Nagi release build plan.
3. Continue PS5 tasks in `TASK_QUEUE.json` and Xbox tasks in `XBOX_TASK_QUEUE.json`. Review all generated findings before publication.
4. Identify a lawful complete firmware image before any PS5 and BC-250 binary comparison. Task S005 needs such an input.

The local and GitHub KMD `CompileOnly` runs passed. Ghidra headless was verified on our own KMD. See `PROGRESS.md` for exact results. The hardware is unavailable, so only build, host tests, and static analysis are in scope.
