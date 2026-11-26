# Strata V2 operational checkpoint

Snapshot: 2026-11-26T08:47:42Z. Branch: `agent/strata-v2`. The eight-hour endurance run is in progress.

## Live operation

- Watchdog and daemon run as detached, hidden Windows processes. The local model API returned HTTP 200 and reported `qwen3.8-flash-next-q2_0` as loaded.
- Endurance start: 2026-11-26T08:29:21Z. Target: 28,800 seconds.
- Snapshot counters: 1,101 seconds uptime, 611.5 seconds worker time, 0 idle seconds, and 5 automatic daemon recoveries.
- The branch queue held 9 completed tasks, 12 pending tasks, 1 delayed retry, 1 running task, and 1 quarantined task. The quarantined task reached the repeated invalid-tool-call limit. Other work continued.
- The GitHub heartbeat is on `agent/strata-status`. At the snapshot it reported the last successful validation at 2026-11-26T08:46:56Z and commit `b35331cae284688de57a0e8cb385b76fe7fd53e4`.

## Recovery and validation

- A generated PS5 note failed doclint because it contained an em dash. The validation error was sent back to Strata. Strata corrected the note on retry and doclint passed.
- A task worker was terminated during a Nagi task. The daemon rescheduled it, then started independent work while the retry waited.
- A mocked model API timeout test confirmed that a running task moves to a retry state. Regression tests passed: 26 tests.
- Five PS5 summaries were reviewed against their declared sources and each passed doclint. Their task outputs remain separate from the proprietary firmware inputs.

The endurance run has not reached eight hours. The daemon uses a local model API, so that model service and the Windows host must remain available after Codex closes.
