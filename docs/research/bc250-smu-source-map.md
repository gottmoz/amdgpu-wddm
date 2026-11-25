# SMU source map from a startup design note

Scope: `docs/design/startup-clock-ownership.md`. This is a historical M433 to M441 design note. Check `docs/hardware.md` and current facts before using any clock or voltage limit. No firmware or hardware was accessed for this source map.

## Source roles described by the note

- `driver/shim/bc250_smu.c` is the mailbox protocol layer. The note describes five imported AMD functions, generated MP1 offsets, caller-owner checks and bounded response polls. It says this shim performs no MMIO or locking itself.
- `driver/kmd/smu.c` is the intended native mailbox owner. The note describes a kernel push lock, MMIO and time bindings, paired reads and stop handling. At the note's recorded stage, hardware ownership transfer was still open.
- `driver/shim/bc250_clock.c` wraps the imported AMD DPM edit function with a local policy and readback. The note's numeric limits belong to that historical stage. They are not the current operating limits.
- The note selects a typed KMD escape for clients. It excludes raw SMU message forwarding and automatic fallback to the older instrument.

The note cites host tests for the protocol and owner. It says those tests do not establish hardware transport or production startup acceptance. The current implementation and hardware status require a fresh review of source, facts and evidence.

## Open PS5 questions

The note does not describe PS5 firmware. It cannot establish whether the PS5 SMU has the same mailbox offsets, command IDs, responses, DPM table or startup order. Compare pinned source and permitted static metadata before proposing a hardware experiment.
