"""Streaming, read-only firmware inventory and comparison helpers."""

from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

CHUNK = 8 * 1024 * 1024
PARSER_VERSION = 2
SCHEMA = "bc250.firmware-audit/v1"
MAGICS = ((b"\x7fELF", "ELF"), (b"MZ", "PE/DOS"), (b"SLB2", "SLB2"), (b"\x54\x14\xf5\xee", "PUP"), (b"PK\x03\x04", "ZIP"))


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entropy_range(path, offset=0, size=None):
    counts = [0] * 256
    p=Path(path); file_size=p.stat().st_size
    size=file_size-offset if size is None else size
    if offset < 0 or size < 0 or offset > file_size or size > file_size-offset: raise ValueError("RANGE_OUT_OF_BOUNDS")
    left=size; total=0
    with Path(path).open("rb") as stream:
        stream.seek(offset)
        while left:
            chunk=stream.read(min(CHUNK,left))
            if not chunk: raise ValueError("UNEXPECTED_EOF")
            for value in chunk: counts[value] += 1
            total += len(chunk)
            left -= len(chunk)
    return round(-sum((n/total)*math.log2(n/total) for n in counts if n), 5) if total else 0.0


def detect(path):
    p = Path(path)
    result = {"path": str(p), "name": p.name, "size": p.stat().st_size, "sha256": hash_file(p), "format": "unknown"}
    with p.open("rb") as f:
        head = f.read(4096)
    for magic, name in MAGICS:
        if head.startswith(magic):
            result["format"] = name
            break
    if result["format"] == "ELF" and len(head) >= 64 and head[4:6] == b"\x02\x01":
        e_type, machine = struct.unpack_from("<HH", head, 16)
        entry, phoff, shoff = struct.unpack_from("<QQQ", head, 24)
        ehsize, phentsize, phnum, shentsize, shnum = struct.unpack_from("<HHHHH", head, 52)
        segments, sections, warnings = [], [], []
        valid = True
        errors=[]
        if ehsize != 64: valid=False; errors.append("ELF_EHSIZE_INVALID")
        if phnum and phentsize != 56: valid=False; errors.append("ELF_PHENTSIZE_INVALID")
        if shnum and shentsize != 64: valid=False; errors.append("ELF_SHENTSIZE_INVALID")
        if shnum == 0 and shoff != 0: valid=False; errors.append("ELF_EXTENDED_NUMBERING_UNSUPPORTED")
        if phnum and (phoff > p.stat().st_size or phnum*phentsize > p.stat().st_size-phoff): valid=False; errors.append("ELF_PHDR_TABLE_TRUNCATED")
        if shnum and (shoff > p.stat().st_size or shnum*shentsize > p.stat().st_size-shoff): valid=False; errors.append("ELF_SHDR_TABLE_TRUNCATED")
        if valid:
            with p.open("rb") as f:
                for i in range(phnum):
                    f.seek(phoff+i*phentsize); raw=f.read(phentsize)
                    if len(raw)!=phentsize: valid=False; errors.append("ELF_PHDR_TABLE_TRUNCATED"); break
                    typ, flags, off, va, _, filesz, memsz, _ = struct.unpack("<IIQQQQQQ", raw)
                    bounded=off <= p.stat().st_size and filesz <= p.stat().st_size-off
                    if typ==1 and filesz>memsz: valid=False; errors.append("PT_LOAD_FILESZ_GT_MEMSZ")
                    if not bounded: valid=False; errors.append("SEGMENT_FILE_RANGE_INVALID")
                    segments.append({"index":i,"type":typ,"flags":flags,"offset":off,"vaddr":va,"filesz":filesz,"memsz":memsz,"executable":bool(flags&1),"bounded":bounded,"zero_initialized_bytes":max(0,memsz-filesz)})
                for i in range(shnum):
                    f.seek(shoff+i*shentsize); raw=f.read(shentsize)
                    if len(raw)!=shentsize: valid=False; errors.append("ELF_SHDR_TABLE_TRUNCATED"); break
                    name,typ,flags,addr,off,size=struct.unpack_from("<IIQQQQ",raw)
                    if typ != 8: valid &= off <= p.stat().st_size and size <= p.stat().st_size-off
                    sections.append({"name_offset":name,"type":typ,"flags":flags,"address":addr,"offset":off,"size":size,"executable":bool(flags&4)})
        execs=[x for x in segments if x["type"]==1 and x["executable"] and x["filesz"] and x["bounded"]]
        # ELF specifies e_entry=0 when the file has no associated entry point.
        # Do not treat that sentinel as mapped merely because a PT_LOAD starts at VA 0.
        entry_map=next((x for x in execs if entry != 0 and x["vaddr"]<=entry<x["vaddr"]+x["filesz"]),None)
        overlaps=[]
        loads=[x for x in segments if x["type"]==1]
        for i,a in enumerate(loads):
            for b in loads[i+1:]:
                if max(a["vaddr"],b["vaddr"]) < min(a["vaddr"]+a["memsz"],b["vaddr"]+b["memsz"]): overlaps.append([a["index"],b["index"]])
        for seg in execs:
            if seg["bounded"]:
                seg["sha256"]=hash_range(p,seg["offset"],seg["filesz"])
                seg["entropy_bits_per_byte"]=entropy_range(p,seg["offset"],seg["filesz"])
        if not valid: warnings.extend(errors)
        if not execs: warnings.append("no file-backed executable PT_LOAD segment")
        if not entry_map: warnings.append("entry point is outside file-backed executable PT_LOAD")
        result["elf"]={"class":64,"endian":"little","abi":head[7],"osabi":{0:"SYSV"}.get(head[7],"other"),"type":e_type,"type_name":{2:"EXEC",3:"DYN",1:"REL"}.get(e_type,"other"),"machine":machine,"architecture":{62:"x86-64",183:"AArch64",243:"RISC-V"}.get(machine,"unknown"),"entry":entry,"entry_valid":entry_map is not None,"program_headers":segments,"program_header_count":phnum,"sections":sections,"section_header_count":shnum,"bounds_valid":bool(valid),"overlapping_segments":overlaps,"dynamic_segments":[x for x in segments if x["type"]==2],"executable_segment_count":len(execs),"declared_executable_bytes":sum(x["filesz"] for x in segments if x["type"]==1 and x["executable"]),"validated_executable_bytes":sum(x["filesz"] for x in execs),"executable_bytes":sum(x["filesz"] for x in execs),"error_codes":errors,"warnings":warnings}
    return result


def hash_range(path,offset,size):
    p=Path(path); total=p.stat().st_size
    if offset<0 or size<0 or offset>total or size>total-offset: raise ValueError("RANGE_OUT_OF_BOUNDS")
    h=hashlib.sha256()
    with p.open("rb") as f:
        f.seek(offset); left=size
        while left:
            chunk=f.read(min(CHUNK,left))
            if not chunk: raise ValueError("UNEXPECTED_EOF")
            h.update(chunk); left-=len(chunk)
    return h.hexdigest()


def cached_detect(path,cache):
    p=Path(path).resolve(); st=p.stat(); key=str(p)
    data=json.loads(cache.read_text()) if cache.exists() else {"schema":SCHEMA,"parser_version":PARSER_VERSION,"entries":{}}
    if data.get("schema")!=SCHEMA or data.get("parser_version")!=PARSER_VERSION: data={"schema":SCHEMA,"parser_version":PARSER_VERSION,"entries":{}}
    entries=data["entries"]
    old=entries.get(key)
    if old and old.get("mtime_ns")==st.st_mtime_ns and old.get("size")==st.st_size: return old["result"]
    result=detect(p); entries[key]={"mtime_ns":st.st_mtime_ns,"size":st.st_size,"result":result}
    cache.parent.mkdir(parents=True,exist_ok=True); tmp=cache.with_suffix(cache.suffix+".tmp"); tmp.write_text(json.dumps(data),encoding="utf-8"); os.replace(tmp,cache)
    return result


def compare(a,b):
    size_a,size_b=Path(a).stat().st_size,Path(b).stat().st_size
    if size_a != size_b: return {"same_size":False,"size_a":size_a,"size_b":size_b,"equal_bytes":None,"confidence":"not-compared"}
    equal=True
    with Path(a).open("rb") as fa,Path(b).open("rb") as fb:
        while True:
            x,y=fa.read(CHUNK),fb.read(CHUNK)
            if x!=y: equal=False; break
            if not x: break
    return {"same_size":True,"size_a":size_a,"size_b":size_b,"equal_bytes":equal,"confidence":"exact"}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("paths",nargs="+"); ap.add_argument("--json",type=Path); ap.add_argument("--compare",nargs=2); ap.add_argument("--entropy",action="store_true"); ap.add_argument("--cache",type=Path); args=ap.parse_args()
    rows=[cached_detect(p,args.cache) if args.cache else detect(p) for p in args.paths]
    if args.entropy:
        for row,p in zip(rows,args.paths): row["entropy_bits_per_byte"]=entropy_range(p)
    output={"schema":SCHEMA,"parser_version":PARSER_VERSION,"files":rows}
    if args.compare: output["comparison"]=compare(*args.compare)
    encoded=json.dumps(output,indent=2)
    if args.json: args.json.write_text(encoded+"\n",encoding="utf-8")
    else: print(encoded)

if __name__ == "__main__": main()
