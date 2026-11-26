# Strata V2 operational checkpoint

Date: 2026-11-26. Branch: `agent/strata-v2`.

## Verified execution

- Local model API responds with `qwen3.8-flash-next-q2_0`.
- Three live tasks ran through the supervisor. Task A read approved source files and produced `docs/research/strata-v2-live-a.md`, validated by doclint. Task B generated `tools/v2_smoke.py` and `tools/tests/test_v2_smoke.py`; two unapproved tool attempts were returned as recoverable errors, then the task completed and its two tests passed. Task C read the structured PS5 JSON reports and wrote `docs/research/strata-v2-ps5-followup.md`. Codex corrected two doclint findings and reran validation successfully.
- Watchdog recovery test: terminate owned daemon PID, wait one watchdog interval, confirm new daemon PID and watchdog still alive.
- GitHub heartbeat on `agent/strata-status` reports idle, validation timestamp, and commit `4bf73967882ece48c36d39035f49469e6b06a865`.
- Combined regression suite: 19 tests passed. Python syntax and report doclint pass.

## Limits

- API failure and unexpected worker termination have not yet been exercised as automated supervisor integration tests.
- Daemon currently idles when its existing branch queues have no matching tasks. A durable cross-project planner is not yet connected to SQLite.
- Task Scheduler registration remains disabled. The watchdog and daemon are running as hidden user processes, not as a boot-start service independent of login.
- SQLite checkpoints are written by the worker. Lease ownership and abandoned-task recovery still need stronger integration tests.
