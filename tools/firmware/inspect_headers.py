"""Verify and print common AMD firmware headers without copying firmware bytes."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib


HEADER = struct.Struct("<IIHHHHIIII")


def inspect(directory: Path, manifest: dict) -> list[dict]:
    rows = []
    for item in manifest["files"]:
        data = (directory / item["name"]).read_bytes()
        if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"{item['name']}: manifest size or SHA-256 mismatch")
        total, header, major, minor, ip_major, ip_minor, version, size, offset, crc = HEADER.unpack_from(data)
        if not (HEADER.size <= header <= offset <= total == len(data) and 0 < size <= total - offset):
            raise ValueError(f"{item['name']}: invalid header bounds")
        if zlib.crc32(data[HEADER.size:]) & 0xFFFFFFFF != crc:
            raise ValueError(f"{item['name']}: header CRC mismatch")
        rows.append({"name": item["name"], "header_version": f"{major}.{minor}",
                     "ip_version": f"{ip_major}.{ip_minor}", "ucode_version": f"0x{version:08x}",
                     "payload_size": size, "payload_offset": offset})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory of locally verified firmware files")
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("cyan_skillfish2.json").read_text(encoding="utf-8"))
    print(json.dumps({"source_commit": manifest["commit"], "headers": inspect(args.directory, manifest)}, indent=2))


if __name__ == "__main__":
    main()
