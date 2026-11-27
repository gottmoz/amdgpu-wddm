# Development-only Zink UMD build

## Result

The documented `zink-umd` option set did not configure on the pinned Mesa source. Its Gallium list selected only Zink. Meson requires softpipe or llvmpipe when `gallium-d3d10umd` is enabled.

The `zink-umd-dev` configuration adds Gallium softpipe. Its exact 19-option set passed the Nagi configure gate. The `build-mesa.ps1` build exited with code 0 and linked `src/gallium/targets/d3d10umd/bc250d3d_zink.dll`.

The DLL is an x64 PE file with 13,317,120 bytes. Its SHA-256 is `D89E7D31353DA30F949D89D088AA67704DCA0E842910C690ADAE5E8C0703EB3E`. `dumpbin /headers` reported machine `8664`. `dumpbin /dependents` listed `api-ms-win-core-synch-l1-2-0.dll`, `KERNEL32.dll`, `USER32.dll` and `GDI32.dll`. The export table has 49 named entries. It includes `OpenAdapter10` and `OpenAdapter10_2`.

The x86 build also exited with code 0. Its DLL is 12,041,728 bytes, with SHA-256 `39A58C149FDD9520A89D5652016E8D3650B117523E19F5FD223DC33539EACCF8`. `dumpbin /headers` reported machine `14C`. It has the same 49 named exports and the same four dependencies.

## Provenance

- Mesa commit `05e6c9622e135ac2aeaf56ec70222642627e2162` on the D-Ogi `amdgpu-wddm/radv-wddm2` branch.
- E33 WDDM2 patch SHA-256 `6e4e73ec2f27c6e19761675e06b7d5d279d0b76c3432e36e072adf276b9c71af`.
- `zink-umd-dev` derives from `zink-umd` and changes `gallium-drivers` to `zink,softpipe`.
- Build log: `D:\BC250-Development\scratch\mesa-zink-umd-dev-build.log`.
- Configure log: `D:\BC250-Development\scratch\mesa-zink-umd-dev-configure.log`.
- Build receipt: `D:\BC250-Development\scratch\mesa-zink-umd-dev-pinned-configure\recipe.json`.

The configuration is development-only. It is not part of tester.39 or a release manifest. Its source worktree contains local MSVC assertion fixes described in the [RADV build record](mesa-radv-msvc-build-2026-11-27.md).

## Limits

This is a host compile and link result. No driver installation, hardware load, D3D10 runtime test, GPU execution or BC-250 validation was performed. The DLL is not a release package.
