# Xbox Series X and S interoperability research

Started 2026-11-25 on `research/xbox-firmware`. This is source-based research. A console specification does not establish that its firmware or operating system runs on the BC-250. Hardware facts about our unit remain in `docs/facts/data/` with evidence.

## Source inventory

| Source | Revision or access | Supports | Limit |
|---|---|---|---|
| [Xbox Series X specifications](https://www.xbox.com/en-us/consoles/xbox-series-x/) | Microsoft page, read 2026-11-25 | Zen 2 CPU, RDNA 2 GPU, GDDR6, SSD and display specifications | No PCI IDs, PSP, SMU or boot-stage map |
| [Xbox Series S specifications](https://www.xbox.com/en-US/consoles/xbox-series-s) | Microsoft page, read 2026-11-25 | Zen 2 CPU, RDNA 2 GPU, GDDR6 and SSD specifications | No low-level firmware interface map |
| [Xbox Velocity Architecture](https://news.xbox.com/en-us/2020/07/14/a-closer-look-at-xbox-velocity-architecture/) | Microsoft, 2020-07-14 | Public description of storage and decompression path | Does not specify SSD boot partitions |
| [Xbox offline system update](https://support.xbox.com/help/hardware-network/console/offline-system-update) | Microsoft support, read 2026-11-25 | Official update route | An update package is not a complete boot firmware image |
| [Xbox One Research wiki](https://github.com/xboxoneresearch/wiki/tree/c3219b210d8e98ad50d4c3a851369f96f2655834) | `c3219b2` | Community format and operating-system leads | Xbox One details need Series X/S confirmation |
| [XanaduXVD](https://github.com/xboxoneresearch/XanaduXVD/tree/50aa0dc89350de580b77f26ade1018b16b0bc1f8) | `50aa0dc` | Open XVD parser implementation | Its own README calls it work in progress |
| [xvdtool](https://github.com/emoose/xvdtool/tree/6fc28862cc5fb711843c0e717101ce4034acf805) | `6fc2886` | Open XVD/XVC parser implementation | Format handling is not proof of Series boot behavior |
| [PS5 hardware specification](https://blog.playstation.com/2020/03/18/unveiling-new-details-of-playstation-5-hardware-technical-specs/) | Sony, 2020-03-18 | Zen 2, RDNA 2-based GPU, GDDR6 and SSD baseline | No BC-250 firmware equivalence |
| [AMD 4700S manual mirror](https://device.report/m/9c96424b88d60d548112cad0e33e256e006f06fcf542559368bfc60fb490b084_optim.pdf) | AMD-authored manual at third-party mirror | Kit memory and board configuration | Verify origin and revision before treating as a primary source |
| IEEE document 9354509 | Link supplied for review | Pending access and bibliographic verification | No claim taken from the unavailable abstract |

The local BC-250 baseline is `docs/hardware.md`, backed by the facts graph. PS5 source notes are in `docs/research/ps5-firmware-portability.md`.

## Pinned XVD tool review

The README at XanaduXVD commit `50aa0dc89350de580b77f26ade1018b16b0bc1f8` describes the project as an experimental parser and manipulator. It claims XVD use on Xbox One, Xbox Series and Windows PC. It also says the project is not production-ready and that little-endian deserialization is incomplete. Its listed features include metadata-relevant parsing as well as decryption, extraction, header editing, signature manipulation and hash-tree changes. It is not a read-only tool by default. [Pinned XanaduXVD README](https://github.com/xboxoneresearch/XanaduXVD/blob/50aa0dc89350de580b77f26ade1018b16b0bc1f8/README.md)

The README at xvdtool commit `6fc28862cc5fb711843c0e717101ce4034acf805` documents an `-i` information mode for package metadata. It describes the tool as targeting Xbox One XVD/XVC packages and says testing used developer-crypted packages. It does not establish Series X/S system-image or boot support. Other documented modes include decryption, extraction, rehashing, resigning and package writes. [Pinned xvdtool README](https://github.com/emoose/xvdtool/blob/6fc28862cc5fb711843c0e717101ce4034acf805/README.md)

These sources support a bounded follow-up: inspect parser code and synthetic fixtures for read-only header fields. Do not provide keys, invoke cryptographic operations, write package inputs or infer Series X/S boot behavior from Xbox One support.

## Work packages

XRE01 covers hardware identity. XRE02 inventories official packages. XRE03 studies container metadata. XRE04 maps boot stages. XRE05 studies documented Windows and Xbox interfaces. XRE06 compares AMD firmware metadata. XRE07 covers storage layout. XRE08 evaluates compatibility barriers. The small tasks are in `XBOX_TASK_QUEUE.json`.

## Initial assessment

The published specifications support shared CPU and GPU architectural families across these systems. They do not identify equal PSP firmware, SMU messages, PCI topology, boot trust chain or operating-system driver contracts. Xbox One research is a lead that requires separate Series X/S evidence. The first useful work is read-only format and interface mapping.
