# PS5 decoder source inventory

Desk research only. Nothing here is a measurement on unit A. Per `docs/01-evidence-rules.md`, a hardware claim
needs an `evidence/` file and a positive control before it leaves `HYPOTHESIS`.

Source page: `docs/research/gfx1013-isa-leads-ps5-decoders.md`.

## Source inventory recorded in that page

| project | commit read | licence | decoder size |
|---|---|---|---|
| AnyPS5 | `9206c3e62167900ea0dabcbf4764b741b114dca2` | GPL-2.0 | 1098 opcode entries, 16 encodings, 1114 names |
| KytyPS5 | `1cfb9522` | GPL-2.0 | 740 names |
| sharpemu | `a2983692` | GPL-2.0 | 747 names |

- All three were cross-checked against LLVM 22.1.8 `llvm-mc -arch=amdgcn -mcpu=gfx1013` and against AMD's
  machine-readable ISA package of 2026-08-06 (RDNA1-RDNA4, CDNA1-CDNA5).
- No code from the projects enters this repository. They are read only as facts about their decoders.
- Some assembler refusals were word-layout artefacts, not opcode gaps: `ds_gws_*` (six), `ds_ordered_count`, and
  both `image_bvh*_intersect_ray` are known for gfx1013 and are explicitly not leads.
- Lead group A: 18 MIMG load/store/gather forms named in AMD's RDNA1/RDNA2 ISA XML at opcodes LLVM rejects for
  every target. The RDNA3 file reassigns six of those slots (0x42, 0x43, 0x4a, 0x4b, 0x62, 0x63). Detail:
  `docs/gfx10-image-ops-amd-xml.md`.
- First lead: MIMG opcode 0xE5 in Ghost of Yōtei (PPSA26344), 38 words, `f1949f05` at 34 sites, `f1962969` at 4.
  AnyPS5 closed the issue by naming the opcode in an error message and deferring the shader. 0xE5 stays
  unidentified. The GFX11 `image_gather4_c_b_cl` reading was withdrawn by its author. gfx1013 encodes that gather
  as 0x4E, already in the decoder.
- Referenced measured facts: the nine GFX10.1 dot products decode in AnyPS5 but write zero or a legacy minimum on
  our silicon (`docs/facts/hardware.md#M865`, `#M866`).

## Unanswered questions about shader ISA portability

1. Do the decoder tables describe gfx1013, or only RDNA2 parts? AnyPS5's notes say most of its measurements are
   on gfx1031/gfx1035/gfx1036.
2. Is 0xE5 a real ray-tracing instruction beside the two BVH ops AMD gives gfx1013, or padding/data in the shader
   store? The bit reading is a hypothesis until the MIMG sweep runs the game's words on unit A.
3. Are the 18 AMD-XML-only MIMG slots executable on gfx1013, or merely reserved? LLVM silence is not silicon
   silence.
4. Can PS5-emitted encodings be reused in our toolchain? Unknown: GPL-2.0 sources, no imported code, so any
   portability claim needs a separately written assembler test with a positive control.
5. Do the three decoders agree on any opcode absent from AMD's ISA map? Not yet tabulated.
