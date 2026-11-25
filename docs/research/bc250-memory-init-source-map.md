# BC-250 memory-init source map (scoped to two files)

Scope: `driver/kmd/atom_firmware.c` and `docs/design/firmware-driver-store.md` only. No firmware binaries were read, copied, or hashed.

## What the code actually establishes (`driver/kmd/atom_firmware.c`)

- `AtomFirmwareCapture()` captures an ACPI table. It calls `AuxKlibInitialize()`, `AuxKlibEnumerateSystemFirmwareTables('ACPI', ...)` and `AuxKlibGetSystemFirmwareTable('ACPI', BC250_ATOM_VFCT_ID, ...)`. It runs at `PASSIVE_LEVEL` and checks `KeGetCurrentIrql()`.
- Device identity comes from the PCI common header read through `DxgkCbReadDeviceSpace(DXGK_WHICHSPACE_CONFIG ...)`. The code checks bus, device and function against `DevicePropertyBusNumber` and `DevicePropertyAddress`. It requires `PCI_CLASS_DISPLAY_CTLR` and a device header type. Vendor and device IDs come from that header.
- Buffers come from `ExAllocatePool2(POOL_FLAG_NON_PAGED, ..., 'AfAB')` and use the same tag on free. `AtomFirmwareRelease()` releases them.
- Failure is mapped to `STATUS_INSUFFICIENT_RESOURCES`, `context.Status`, or `STATUS_DEVICE_CONFIGURATION_ERROR`.

Verified: nothing in this file writes to, trains, or initializes GPU/DRAM memory. It only captures a table and hands it to `Bc250AtomFirmwareCapture()`.

## What the design note establishes

- Eight firmware binaries ship inside the signed driver package (`SourceDisksFiles` and `CopyFiles`, DIRID 13). Names and hashes are pinned in `tools/firmware/cyan_skillfish2.json`. The public ZIP omits the binaries.
- `IoGetDriverDirectory(DriverDirectoryImage)` gives a handle held until unload. Each firmware file opens relative to that handle from the compiled firmware table. No path, registry override or fallback directory is accepted.
- Reparse, empty, oversized and short reads fail before firmware reaches the PSP. The read limit is 1 MiB per file.
- Host tests (`tools/release/test-firmware-package.ps1`, `driver/kmd/test/run_firmware_io.ps1`) do not establish driver-load or deferred-install acceptance. BD-152 still needs lab install, repair and rollback checks.

## Unanswered

- AGESA: the VFCT table's origin is not stated in either file. The value of `BC250_ATOM_VFCT_ID` is not shown here.
- Memory initialization: no MCLK/DRAM training, no memory controller bring-up is described.
- PS5 comparison: no evidence in these two files.
