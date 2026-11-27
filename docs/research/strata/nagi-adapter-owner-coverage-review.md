# Nagi adapter owner coverage review

Scope: Read the owner API, PnP call sites, and the full 9,891-byte host test. No hardware access occurred.

## API and coverage

- `AdapterOwnerClaim` atomically claims an empty slot. It rejects null identities, poison state, and an occupied slot.
- `AdapterOwnerIs` compares an identity with the stored owner.
- `AdapterOwnerRelease` clears the matching owner or stores a poison sentinel after an uncertain stop.
- Host cases cover competing claims, failed allocation, stop and restart, normal removal, concurrent claims, and remove serialization.
- The retained-stop case poisons admission. Later claims fail for both PDO identities.
- `run_adapter_owner.ps1` compiled the host harness and reported `94 checks, 0 failures`.

## Follow-up

- The host test never calls `AdapterOwnerRelease` directly. Add a wrong owner release case to prove that it preserves the current owner. This is a coverage gap, not an observed failure.

## Limit

This host test does not exercise hardware behavior.
