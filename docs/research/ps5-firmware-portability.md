# PS5 and BC-250 firmware portability survey

Desk research, 2026-11-25. This page records source observations and open questions. It makes no new hardware fact. The unit is unavailable. No firmware image was flashed, installed, extracted, modified, or published.

## Inputs and limits

- The local `tools/firmware/cyan_skillfish2.json` pins eight public GPU microcode files to linux-firmware commit `2b8daaf611fbade74f26a5b58ec1defe6a02f5e0`. The names are CE, ME, MEC, MEC2, PFP, RLC, SDMA and SDMA1. This manifest does not contain PSP or SMU firmware, AGESA, VCN firmware or a PS5 system image.
- `driver/kmd/psp.c` and `driver/shim/bc250_psp.c` implement the KMD's PSP loading path. `driver/kmd/smu.c` and `driver/shim/bc250_smu.c` implement its SMU path. These files show this driver's interfaces. They do not establish that Sony firmware accepts the same interface.
- The local Linux reading `evidence/linux/2026-11-01-L1031-init-trace/out/boot-b/l3-firmware-info.txt` reports ME, PFP, CE, RLC, MEC and SDMA versions. It reports SMC version `0x00580600` and VCN firmware version zero for that boot. A zero in this report does not establish the state of a PS5.
- The workspace contains SPI chip-register snapshots and GPU ring dumps under `evidence/`. The file inventory did not identify a full PS5 or BC-250 firmware image for a Ghidra comparison. The SPI evidence stays immutable.

## Static public microcode header check

`python tools/firmware/inspect_headers.py D:\BC250-Development\scratch\firmware-static` verified each file against the pinned manifest. It parsed `common_firmware_header` from `driver/shim/include/amdgpu_ucode.h` and checked header and payload bounds. The stored CRC matched the bytes after the 32-byte common header. All eight passed on 2026-11-25. The files remain outside Git.

| File suffix | Header | IP | Microcode version |
|---|---|---|---|
| CE | 1.0 | 10.1 | `0x25` |
| ME | 1.0 | 10.1 | `0x63` |
| MEC and MEC2 | 1.0 | 10.1 | `0x90` |
| PFP | 1.0 | 10.1 | `0x94` |
| RLC | 2.0 | 10.1 | `0x0d` |
| SDMA and SDMA1 | 1.0 | 5.0 | `0x34` |

## Primary project sources

| Project and revision | What its own source shows | Limit for this project |
|---|---|---|
| [PS5 Linux loader](https://github.com/ps5-linux/ps5-linux-loader/tree/badfe48a56629d2e512e3f4e4a177cace333e4b9) `badfe48` | A PS5 payload that prepares a custom Linux bootloader through the console's loader path. | It is a PS5 boot method. It does not show that the BC-250 can boot Sony system software. |
| [PS5 Linux patches](https://github.com/ps5-linux/ps5-linux-patches/tree/c8fe83a4db9d87b1d95cde83223069bae8256988) `c8fe83a` | A patch and configuration applied to a Linux kernel for PS5. Its README lists PS5-specific GPU, clock and screen options. | A Linux driver patch is not a PS5 firmware image or a proof of compatibility with the BC-250. |
| [BC5](https://github.com/RedMadKnight/BC5/tree/0792861113c69679df83209f3123d2310a322a1c) `0792861` | The project runs a PS5 game host on the BC-250 under Linux. Its [ADR 0012](https://github.com/RedMadKnight/BC5/blob/0792861113c69679df83209f3123d2310a322a1c/docs/decisions/0012-no-firmware-hle-host.md) chooses host-written system libraries and no PS5 firmware dependency. | BC5's statement that the PS5 boot chain cannot run on the board is a project position, not a measurement in this repository. Its emulator route does not require a firmware port. |
| [BC-250 VCN research](https://github.com/Shalasere/bc250-vcn-research/tree/4a91ceb86275fbceeaf1fb3062f2f086e7f780c5) `4a91ceb` | The maintainers report a direct VCN firmware load path and an SMU power-up reply that rejects a prerequisite. | These are third-party observations on a different setup. Our `docs/hardware.md` forbids VCN MMIO reads and writes because prior access wedged a unit. No runtime VCN probe is in scope. |

## Static comparison plan

| Area | Current evidence | Next permitted step |
|---|---|---|
| PSP and trust chain | The KMD loads public GPU microcode through its PSP path. PS5 Linux uses a console-specific loader. | Compare documented call and image formats at pinned source revisions. If lawful images become available, record hashes and headers locally before Ghidra analysis. |
| SMU | The local Linux firmware report records SMC `0x00580600`. BC5 and VCN research use their own firmware paths. | Compare documented mailbox contracts and known firmware identifiers. Do not infer message compatibility from a shared IP name. |
| AGESA and memory init | No AGESA or complete BIOS image was identified in this workspace. The older companion repository discusses a PS5 Linux loader VRAM reservation, but its notes are prior art. | Trace the loader's memory map code and compare it with BC-250 firmware documentation. Keep address and capacity claims tied to evidence. |
| VCN | The local Linux report lists VCN firmware version zero for one boot. Third-party work reports a gated VCN path. | Review static source and permitted firmware metadata only. Do not access the VCN MMIO window. |
| GPU microcode | Eight public Cyan Skillfish files are pinned by size and SHA-256 in the local manifest. | Parse their documented headers and compare hashes and version fields with permitted PS5 references. Do not copy binary contents into Git. |

## Feasibility assessment

There is no verified route in these inputs to boot PS5 system software on the BC-250. Shared CPU and GPU lineage supports an investigation of interfaces. It does not establish compatible boot security, board initialization, memory layout, firmware services or peripherals. BC5 demonstrates a different route: run a host implementation of required system behavior and submit native GPU work under Linux. That result is a lead for software compatibility, not proof of firmware portability.
