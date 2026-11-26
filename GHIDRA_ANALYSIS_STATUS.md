# Ghidra analysis status

The existing batch has 40 successful imports and was not repeated. SHA-256 correlation reports six `EXEC` ELF files with one function each. The other 34 have zero reported functions despite executable load segments. The Ghidra invocation used ELF auto-loader for extracted candidates. Compiler spec and analysis options were not recorded in the saved batch logs, so function-discovery differences remain unresolved.
