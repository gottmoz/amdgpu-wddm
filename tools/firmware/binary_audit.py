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
MAGICS = ((b"\x7fELF", "ELF"), (b"MZ", "PE/DOS"), (b"SLB2", "SLB2"), (b"\x54\x14\xf5\xee", "PUP"), (b"PK\x03\x04", "ZIP"))


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entropy_range(path, offset=0, size=None):
    counts = [0] * 256
    p=Path(path); left=p.stat().st_size-offset if size is None else size; total=0
    with Path(path).open("rb") as stream:
        stream.seek(offset)
        while left:
            chunk=stream.read(min(CHUNK,left))
            if not chunk: break
            for value in chunk:
                counts[value] += 1
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
        valid = ehsize == 64 and phentsize in (0, 56) and phnum < 4096 and shentsize in (0, 64) and shnum < 65536
        if valid:
            with p.open("rb") as f:
                for i in range(phnum):
                    f.seek(phoff+i*phentsize); raw=f.read(phentsize)
                    if len(raw)!=phentsize: valid=False; break
                    typ, flags, off, va, _, filesz, memsz, _ = struct.unpack("<IIQQQQQQ", raw)
                    bounded=off <= p.stat().st_size and filesz <= p.stat().st_size-off
                    valid &= bounded and filesz <= memsz
                    segments.append({"type":typ,"flags":flags,"offset":off,"vaddr":va,"filesz":filesz,"memsz":memsz,"executable":bool(flags&1),"bounded":bounded,"zero_initialized_bytes":max(0,memsz-filesz)})
                for i in range(shnum):
                    f.seek(shoff+i*shentsize); raw=f.read(shentsize)
                    if len(raw)!=shentsize: valid=False; break
                    name,typ,flags,addr,off,size=struct.unpack_from("<IIQQQQ",raw)
                    if typ != 8: valid &= off <= p.stat().st_size and size <= p.stat().st_size-off
                    sections.append({"name_offset":name,"type":typ,"flags":flags,"address":addr,"offset":off,"size":size,"executable":bool(flags&4)})
        execs=[x for x in segments if x["type"]==1 and x["executable"] and x["filesz"]]
        entry_map=next((x for x in execs if x["vaddr"]<=entry<x["vaddr"]+x["filesz"]),None)
        overlaps=[]
        for i,a in enumerate(segments):
            for b in segments[i+1:]:
                if max(a["vaddr"],b["vaddr"]) < min(a["vaddr"]+a["memsz"],b["vaddr"]+b["memsz"]): overlaps.append([segments.index(a),segments.index(b)])
        for seg in execs:
            if seg["bounded"]:
                seg["sha256"]=hash_range(p,seg["offset"],seg["filesz"])
                seg["entropy_bits_per_byte"]=entropy_range(p,seg["offset"],seg["filesz"])
        if not valid: warnings.append("invalid or truncated ELF header/segment/section bounds")
        if not execs: warnings.append("no file-backed executable PT_LOAD segment")
        if not entry_map: warnings.append("entry point is outside file-backed executable PT_LOAD")
        result["elf"]={"class":64,"endian":"little","abi":head[7],"osabi":{0:"SYSV"}.get(head[7],"other"),"type":e_type,"type_name":{2:"EXEC",3:"DYN",1:"REL"}.get(e_type,"other"),"machine":machine,"architecture":{62:"x86-64",183:"AArch64",243:"RISC-V"}.get(machine,"unknown"),"entry":entry,"entry_valid":entry_map is not None,"program_headers":segments,"program_header_count":phnum,"sections":sections,"section_header_count":shnum,"bounds_valid":bool(valid),"overlapping_segments":overlaps,"dynamic_segments":[x for x in segments if x["type"]==2],"executable_segment_count":len(execs),"executable_bytes":sum(x["filesz"] for x in execs),"warnings":warnings}
    return result


def hash_range(path,offset,size):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        f.seek(offset); left=size
        while left:
            chunk=f.read(min(CHUNK,left))
            if not chunk: break
            h.update(chunk); left-=len(chunk)
    return h.hexdigest()


def cached_detect(path,cache):
    p=Path(path).resolve(); st=p.stat(); key=str(p)
    data=json.loads(cache.read_text()) if cache.exists() else {}
    old=data.get(key)
    if old and old.get("mtime_ns")==st.st_mtime_ns and old.get("size")==st.st_size: return old["result"]
    result=detect(p); data[key]={"mtime_ns":st.st_mtime_ns,"size":st.st_size,"result":result}
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
        for row,p in zip(rows,args.paths): row["entropy_bits_per_byte"]=entropy(p)
    output={"files":rows}
    if args.compare: output["comparison"]=compare(*args.compare)
    encoded=json.dumps(output,indent=2)
    if args.json: args.json.write_text(encoded+"\n",encoding="utf-8")
    else: print(encoded)

if __name__ == "__main__": main()
