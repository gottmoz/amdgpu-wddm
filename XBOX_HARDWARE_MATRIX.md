# Hardware comparison matrix

Status: SOURCE-DERIVED unless a cell says UNKNOWN. `B` is local `docs/hardware.md` and its linked evidence. `P` is the [Sony PS5 specification](https://blog.playstation.com/2020/03/18/unveiling-new-details-of-playstation-5-hardware-technical-specs/). `X` and `S` are [Microsoft Series X](https://www.xbox.com/en-us/consoles/xbox-series-x/) and [Series S](https://www.xbox.com/en-US/consoles/xbox-series-s) specifications. `A47` is the [AMD-authored 4700S manual at a third-party mirror](https://device.report/m/9c96424b88d60d548112cad0e33e256e006f06fcf542559368bfc60fb490b084_optim.pdf). No verified primary 4800S specification is available yet.

| Area | BC-250 | PS5 | Series X | Series S | 4700S kit | 4800S kit |
|---|---|---|---|---|---|---|
| CPU architecture | Zen 2, six cores usable on baseline board `B` | Zen 2, 8 cores and 16 threads `P` | Custom Zen 2, 8 cores `X` | Custom Zen 2, 8 cores `S` | Zen 2, 8 cores `A47` | UNKNOWN |
| CPUID and microcode | Exact CPUID comparison pending | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| GPU family | GFX 10.1.3, Cyan Skillfish `B` | RDNA 2-based `P` | Custom RDNA 2, 52 CUs `X` | Custom RDNA 2, 20 CUs `S` | Integrated GPU path not established by reviewed source | UNKNOWN |
| GPU IP version | GC 10.1.3, DCN 2.0.1 and SDMA 5.0.1 `B` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| PCI identity | GPU `1002:13FE` `B` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| PSP and SMU | MP0 and MP1 11.0.8 in Linux discovery `B` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Memory | 16 GB shared GDDR6 `B` | 16 GB GDDR6 `P` | 16 GB GDDR6, 320-bit bus `X` | 10 GB GDDR6, 128-bit bus `S` | 8 or 16 GB GDDR6 `A47` | UNKNOWN |
| Memory controller and training | Exact init path open | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Interrupt controller | Local driver and Linux evidence need a scoped comparison | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| DMA and IOMMU | GART and SDMA paths in local driver `B` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Storage | Board-specific controller inventory pending | Custom SSD `P` | Custom NVMe SSD `X` | Custom NVMe SSD `S` | Kit storage interface needs source review | UNKNOWN |
| Display | DCN 2.0.1 class discovery `B` | HDMI output `P` | HDMI 2.1 `X` | HDMI 2.1 `S` | Discrete display path needs source review | UNKNOWN |
| VCN | 2.0.3 hardware ID reported, runtime path gated `B` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

Shared Zen 2 or RDNA branding is an architectural family label. It does not prove matching registers, firmware images, memory maps or security policy. Missing cells are research tasks, not negative findings.
