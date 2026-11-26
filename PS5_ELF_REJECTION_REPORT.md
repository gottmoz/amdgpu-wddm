# PS5 ELF candidate reassessment

The previous parser reported 34 candidates as rejected. Parser v2 rechecked all 40 extracts against their source files. All 40 extracted file extents fit their recorded PUP entry or kdata source boundary. All 40 ELF headers, program tables and segment byte ranges pass v2 bounds checks. The 34 candidates with zero Ghidra functions are therefore not file truncation findings. Their ELF type field is nonstandard (`other`), despite valid x86-64 headers and executable PT_LOAD regions. Ghidra logs recorded zero functions. This is unresolved function discovery, not proof of protected payload or complete executables.

See `PS5_ELF_REJECTION_REPORT.json` for candidate offsets, hashes, segment metadata and prior Ghidra counts. No import was repeated.
