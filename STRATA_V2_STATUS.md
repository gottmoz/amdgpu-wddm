# Strata V2 operational checkpoint

Snapshot: 2026-11-26T09:02:38Z. Branch: `agent/strata-v2`. The eight-hour endurance run is in progress.

## Live operation

- A hidden watchdog and daemon run as detached Windows processes. The local model API returned HTTP 200 and reported `qwen3.8-flash-next-q2_0` as loaded.
- Endurance start: 2026-11-26T08:29:21Z. Target: 28,800 seconds.
- Snapshot counters: 1,997 seconds uptime, 1,379.5 seconds worker time, 0 idle seconds, and 6 automatic recoveries.
- The persistent branch queue held 16 completed tasks, 3 pending tasks, 2 delayed retries, 1 running task, and 2 quarantined tasks. The quarantined tasks exceeded retry or invalid-tool-call limits. Other work continued.
- The GitHub heartbeat is on `agent/strata-status`. It records current and next task IDs, validation time, recovery count, review count and published commits.

## Recovery and validation

- A generated PS5 note failed doclint because it contained an em dash. Strata received the error, corrected the note on retry, and passed doclint.
- A task worker was terminated during Nagi work. The daemon rescheduled it and continued with independent Nagi work while the retry waited.
- A mocked model API timeout test confirmed that a running task moves to a retry state. Regression tests passed: 27 tests.
- Five PS5 summaries were reviewed against their declared sources and each passed doclint. They are listed in `STRATA_REVIEWED.json`.

The endurance run has not reached eight hours. The daemon uses a local model API, so that service and the Windows host must remain available after Codex closes.
