# PS5 and BC-250 component comparison

This matrix separates binary observations from source leads. No row establishes firmware
or boot compatibility.

| Component | Local PS5 input observation | BC-250 reference | Assessment |
|---|---|---|---|
| x86-64 executables | 40 bounded ELF64 candidates across the three PUP files and `kdata1001.bin`. Ghidra analysis is in progress. | Nagi KMD source and BC-250 Linux reports describe host-side paths. | Architecture family alone does not establish interface compatibility. |
| PSP or secure loader | PUP entries with IDs `0x103`, `0x104`, `0x106` and `0x107` begin with `e4db7c02`. The [public unpacker](https://raw.githubusercontent.com/zecoxao/ps5-pup-unpacker/master/PUP.cpp) labels some IDs as Oberon secure loaders. | `driver/shim/bc250_psp.c` and public Cyan Skillfish microcode manifest. | Component name is a source lead. Processor type and PSP contract are unverified. |
| SMU and power | No SMU component was identified from a verified header or symbol. | `driver/shim/bc250_smu.c` and `docs/research/bc250-smu-source-map.md`. | Unknown. |
| GPU microcode | No complete PUP entry hash matches the eight public Cyan Skillfish files. | `tools/firmware/cyan_skillfish2.json` at pinned linux-firmware commit. | No byte-identical complete entry. Nested components remain unknown. |
| Memory initialization | No component was identified from a verified header or symbol. | `docs/research/bc250-memory-init-source-map.md`. | Unknown. |
| Platform initialization | PUP tables, a nested PUP and SLB2 markers are present. Their boot roles are not established by this static scan. | BC-250 UEFI and Nagi host-side initialization documentation. | Interface comparison awaits component identification. |
