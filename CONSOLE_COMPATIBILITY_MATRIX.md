# Console and kit compatibility questions

This matrix records investigation routes, not boot support.

| Pair | Shared published basis | Main missing proof | Current assessment |
|---|---|---|---|
| BC-250 and PS5 | Zen 2, RDNA-family GPU and GDDR6 | Boot trust, board initialization, PSP/SMU contracts, peripherals | HYPOTHESIS only |
| BC-250 and Series X | Zen 2, RDNA-family GPU and GDDR6 | GPU IP identity, firmware services, memory layout, boot chain | HYPOTHESIS only |
| BC-250 and Series S | Zen 2, RDNA-family GPU and GDDR6 | Same barriers plus a different published memory capacity | HYPOTHESIS only |
| BC-250 and 4700S kit | Zen 2 and GDDR6 | Exact silicon identity, GPU state, board firmware and PCI topology | UNKNOWN |
| BC-250 and 4800S kit | No verified primary 4800S specification yet | Source provenance and hardware inventory | UNKNOWN |
| PS5 and Series X/S | Zen 2, RDNA 2-based graphics and GDDR6 | Platform firmware, security and OS interfaces | No compatibility claim |

The feasible near-term target is reusable knowledge: public format parsers, memory-map comparisons, GPU command and shader documentation, and documented Windows interfaces that can guide Nagi. Running a console operating system or firmware on another board requires separate evidence.
