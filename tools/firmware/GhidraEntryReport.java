// Metadata-only Ghidra report for entry-point validation.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.SymbolTable;

public class GhidraEntryReport extends GhidraScript {
    @Override
    protected void run() throws Exception {
        println("GHIDRA_REPORT name=" + currentProgram.getName()
            + " format=" + currentProgram.getExecutableFormat()
            + " language=" + currentProgram.getLanguageID()
            + " compiler=" + currentProgram.getCompilerSpec().getCompilerSpecID()
            + " image_base=" + currentProgram.getImageBase()
            + " functions=" + currentProgram.getFunctionManager().getFunctionCount());

        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            println("GHIDRA_BLOCK name=" + block.getName()
                + " start=" + block.getStart()
                + " end=" + block.getEnd()
                + " execute=" + block.isExecute());
        }

        SymbolTable symbols = currentProgram.getSymbolTable();
        AddressIterator entries = symbols.getExternalEntryPointIterator();
        int entryCount = 0;
        while (entries.hasNext()) {
            Address entry = entries.next();
            println("GHIDRA_ENTRY_POINT address=" + entry);
            entryCount++;
        }
        println("GHIDRA_ENTRY_POINT_COUNT count=" + entryCount);

        String[] args = getScriptArgs();
        if (args.length > 0) {
            long entryValue = Long.decode(args[0]);
            Address elfEntry = toAddr(entryValue);
            Function exact = currentProgram.getFunctionManager().getFunctionAt(elfEntry);
            Function containing = currentProgram.getFunctionManager().getFunctionContaining(elfEntry);
            println("GHIDRA_ELF_ENTRY address=" + elfEntry
                + " mapped=" + currentProgram.getMemory().contains(elfEntry)
                + " function_at=" + (exact != null)
                + " function_containing=" + (containing != null));
        }

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            Function function = functions.next();
            println("GHIDRA_FUNCTION address=" + function.getEntryPoint()
                + " external=" + function.isExternal());
        }
    }
}