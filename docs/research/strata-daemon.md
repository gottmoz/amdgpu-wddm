# Continuous Strata coordinator

Run `tools/strata_daemon.py` from a dedicated `research/xbox-firmware` worktree. It extends `tools/strata_supervisor.py`. The current model remains `qwen3.8-flash-next-q2_0` at the local Strata API. Set `BC250_ROOT` to the shared toolchain workspace before starting. Keep the worktree separate from Codex builds.

The coordinator polls the GitHub task inbox every 60 seconds. It creates small source-review tasks when no task is ready. It continues polling when its seed tasks are done. A task may use at most 100 tool rounds. The worker retains six recent rounds and compacts earlier tool actions. Checkpoints and metrics are local files in the worktree. A stalled worker is stopped and retried at most three times with backoff.

The coordinator holds `.strata-daemon.lock` for its lifetime. A second process cannot use the same worktree. Create `STRATA_STOP` in the worktree for controlled shutdown. Remove that file before the next start.

## GitHub task inbox

The coordinator creates `agent/strata-inbox` with `TASK_INBOX.json` and `agent/strata-status` with `AGENT_STATUS.json` and `AGENT_STATUS.md`. These branches never merge automatically. Status changes are published while working and at least once every five minutes. A task submitted through the inbox must have this shape:

```json
{
  "schema_version": 1,
  "tasks": [
    {
      "id": "IN-XRE03-001",
      "area": "XRE03",
      "branch": "research/xbox-firmware",
      "objective": "Read a named public source and record a bounded format note.",
      "allowed_writes": ["docs/research/xbox-format-note.md"]
    }
  ]
}
```

Incoming tasks stay in `STRATA_INBOX_QUEUE.json`. Generated tasks stay in `STRATA_GENERATED_QUEUE.json`. The approved research plan stays in `XBOX_TASK_QUEUE.json`. The coordinator rejects duplicate IDs and objectives, writes outside `docs/research/`, branch mismatches and unsafe actions. A task that needs unavailable firmware or hardware stays blocked and does not loop.

Generated notes remain local until Codex reviews their evidence, runs doclint and commits them to the research branch. Only operational status is published automatically. No firmware bytes or credentials belong in any branch.
