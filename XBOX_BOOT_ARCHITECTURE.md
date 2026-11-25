# Xbox boot architecture: evidence map

This map starts from public sources. It does not assert a complete Series X/S boot sequence.

| Stage or dependency | Series X/S evidence | BC-250 comparison | Status |
|---|---|---|---|
| Silicon initialization | Microsoft publishes Zen 2, RDNA 2 and GDDR6 specifications. Low-level initialization order is not in those pages. | `docs/hardware.md` identifies the local IP blocks. Exact reset and firmware sequence differs or remains unmeasured. | SOURCE-DERIVED and UNKNOWN |
| Secure boot and security processor | No Series X/S PSP call contract verified in the reviewed sources. | The BC-250 KMD uses an AMD PSP path for public GPU microcode. This is not an Xbox boot path. | BLOCKED on source evidence |
| System storage | Microsoft documents a custom NVMe SSD and Velocity Architecture. | BC-250 board storage and boot media need their own map. | SOURCE-DERIVED |
| Offline update | Microsoft provides OSU1 through its support route. | An update ZIP cannot stand in for a complete boot firmware image. | SOURCE-DERIVED |
| Hypervisor and OS layers | Xbox One research exists. Series X/S applicability has not been established here. | Windows desktop WDDM contracts in Nagi do not establish Xbox graphics-driver contracts. | HYPOTHESIS pending source review |

Next steps: inspect public Series X/S documentation and read-only package metadata. Keep Xbox One findings labeled by generation. Do not bypass signatures or inspect private keys.
