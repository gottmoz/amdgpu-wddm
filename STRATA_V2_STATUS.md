# Strata V2 operational checkpoint

Snapshot: 2026-11-26T09:04:03Z. Branch: `agent/strata-v2`. The eight-hour endurance run is in progress.

## Live operation

- A hidden watchdog and daemon run as detached Windows processes. The local model API returned HTTP 200 and reported `qwen3.8-flash-next-q2_0` as loaded.
- Endurance start: 2026-11-26T08:29:21Z. Target: 28,800 seconds.
- Snapshot counters: 2,082 seconds uptime, 1,454.5 seconds worker time, 0 recorded idle seconds, and 6 automatic recoveries.
- The persistent branch queue held 18 completed tasks, 17 pending tasks, 2 delayed retries, 1 running task, and 2 quarantined tasks. The two quarantined tasks reached retry or invalid-tool-call limits. Other work continued.
- When ready work fell below five, the daemon generated 16 source-to-result review tasks and refilled the useful queue.
- The GitHub heartbeat is on `agent/strata-status`. At this snapshot it recorded the last validation at 2026-11-26T09:04:01Z and `NAGI-DEP-05` as the upcoming task.

## Recovery and validation

- A generated PS5 note failed doclint because it contained an em dash. Strata received the error, corrected the note on retry, and passed doclint.
- A task worker was terminated during Nagi work. The daemon rescheduled it and continued with independent work while the retry waited.
- A mocked model API timeout test confirmed that a running task moves to a retry state. Regression tests passed: 27 tests.
- Five PS5 summaries were reviewed against their declared sources and passed doclint. They are listed in `STRATA_REVIEWED.json`.

The endurance run has not reached eight hours. The daemon uses a local model API, so that service and the Windows host must remain available after Codex closes.

## Latest intervention

Snapshot: 2026-11-26T10:18:05Z. The original endurance start and counters were preserved. At the last read, the run recorded 4,259.9 seconds of work, 1,350 seconds idle, 74 worker runs, and 7 automatic recoveries. The detached watchdog restarted the daemon after its code update.

The 33 outstanding task results now have explicit accepted/corrected/rejected dispositions. Review generation is disabled to prevent review recursion. Twelve implementation tasks are queued across PS5, Nagi and Strata. Scheduler selection rotates across available areas. The verified PS5 inventory summary reports 40 metadata candidates, all parser-bounds valid, with 34 zero-function and six positive-function Ghidra records; this does not identify components.

The five pinned Nagi Python dependencies are verified in the isolated scratch target. Focused regressions pass: 34 tests. Automatic publication is gated to explicitly opted-in Python/JSON tools artifacts with declared unittest validation; the test suite mocks Git and performs no push.

The eight-hour endurance run is still in progress. Nagi's LLVM, MinGW, glslang, NuGet, SDK and full-build dependencies remain outstanding.


## Recovery checkpoint – 2026-11-26 10:26 UTC

The original eight-hour endurance start and counters remain intact. The daemon/watchdog were briefly stopped to recover the original full regression file and load the corrected task-scoped prompts; the watchdog is being resumed. The latest run counters before this checkpoint were 4,599.3 work seconds, 1,350 idle seconds, 97 worker runs and 9 automatic recoveries.

The generated Nagi dependency verifier was incorrect on first pass (unrelated package pins and global environment lookup). Codex corrected it against `docs/build.md`; five pinned distributions in isolated `scratch\\py` all match, and tests pass. Publication now rejects large deletions from existing files. A Strata task had replaced the daemon tests with an inspection probe; it was restored from the reviewed revision and the actual regression suite passes 43 tests.

Seven bounded implementation tasks remain in the queue. The task context now explicitly forbids profile/Strata local paths and records invalid-call details. Some tasks previously retried after source-scope errors have been corrected and rescheduled.


## Validated operational checkpoint – 2026-11-26T10:53:46Z

The queue has 20 concrete pending/retry code and test tasks across PS5, Nagi and Strata; source existence checks passed. Review-loop generation is off, and duplicate probes are rejected before publication.

Nagi's `build_context_summary.py` was automatically published at `35e509c4fbc345f64ffa546afe3023ebffa99474` after its declared tests passed; Codex reviewed the code and tests. The five Python build dependencies were verified in scratch/py. Other toolchain dependencies remain unresolved.

The full focused suite passed 51 tests at this checkpoint. The eight-hour endurance start remains `2026-11-26T08:29:21Z`; latest stored counters before daemon restart were 5,293.2 work seconds, 1,410 idle seconds, 112 worker runs and 11 automatic recoveries.


## PS5 tool review – 2026-11-26T11:02:10Z

Reviewed the automatically published segment-hash utility. Corrected SHA-256 syntax validation and the requirement for explicit validation; the 9-test module and 60-test focused suite pass. Current PS5 summary input lacks per-segment digests, so no real cross-version segment match has been established.
