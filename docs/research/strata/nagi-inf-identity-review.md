# BC-250 KMD INF identity review

Scope: Read-only comparison of `driver/kmd/bc250kmd.inf`, `docs/hardware.md`, and the packagecheck README. This review uses metadata only.

## Findings

- The INF model section names `PCI\VEN_1002&DEV_13FE` in `[Models.NTamd64.10.0...22631]`.
- `docs/hardware.md` lists BC-250 as PCI `1002:13FE`. The packagecheck README requires that ID and warns about extra matches.
- The INF declares one model hardware ID. This matches the single-device rule in the README.
- The INF version section sets `Signature`, `Class`, `ClassGuid`, `CatalogFile`, `DriverVer`, and `PnpLockdown`.
- The README lists those fields among packagecheck rules. It does not give a literal expected `ClassGuid` in the reviewed section.
- The service section points to `%13%\bc250kmd.sys`. `DefaultDestDir` is 13, and the INF copies that driver through `Bc250_Files`.
- The plain INF comments out `UserModeDriverName`. The README says a full-model package requires this value. The plain package should fail that gate.

## Limits

This review covers no package contents, catalog presence, hashes, or test results. It makes no claim about hardware behavior.
