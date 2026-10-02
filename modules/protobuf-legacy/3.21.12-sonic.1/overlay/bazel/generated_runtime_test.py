import argparse
import os
import struct
import subprocess
from pathlib import Path

from python.runfiles import runfiles


def elf_contract(path: Path) -> tuple[int, str | None, list[str]]:
    data = path.read_bytes()
    if data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("Expected a little-endian ELF64 library")
    machine = struct.unpack_from("<H", data, 18)[0]
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    entry_size, entry_count = struct.unpack_from("<HH", data, 54)
    segments = [struct.unpack_from("<IIQQQQQQ", data, program_offset + index * entry_size) for index in range(entry_count)]
    dynamic = next(segment for segment in segments if segment[0] == 2)
    tags = {}
    needed = []
    for offset in range(dynamic[2], dynamic[2] + dynamic[5], 16):
        tag, value = struct.unpack_from("<QQ", data, offset)
        if tag == 0:
            break
        tags[tag] = value
        if tag == 1:
            needed.append(value)
    string_address = tags[5]
    load = next(segment for segment in segments if segment[0] == 1 and segment[3] <= string_address < segment[3] + segment[5])
    string_table = load[2] + string_address - load[3]
    def string_at(offset):
        start = string_table + offset
        return data[start:data.index(b"\0", start)].decode()
    soname = string_at(tags[14]) if 14 in tags else None
    return machine, soname, [string_at(offset) for offset in needed]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--architecture", choices=("amd64", "arm64"), required=True)
    args = parser.parse_args()
    resolver = runfiles.Create()
    assert resolver is not None
    consumer = resolver.Rlocation(args.consumer)
    library = resolver.Rlocation(args.library)
    assert consumer and library
    expected = Path(library).resolve()
    machine, soname, _ = elf_contract(expected)
    assert machine == {"amd64": 62, "arm64": 183}[args.architecture], (machine, args.architecture)
    assert soname == "libprotobuf.so.32", soname
    _, _, needed = elf_contract(Path(consumer).resolve())
    assert "libprotobuf.so.32" in needed, needed
    assert not any("protobuf-lite" in name for name in needed), needed
    environment = dict(os.environ)
    environment.pop("LD_LIBRARY_PATH", None)
    environment.pop("LD_PRELOAD", None)
    result = subprocess.run([consumer], env=environment, text=True, capture_output=True, check=True)
    selected = [line.removeprefix("PROTOBUF_LIBRARY=") for line in result.stdout.splitlines() if line.startswith("PROTOBUF_LIBRARY=")]
    assert selected == [str(expected)], (selected, expected, result.stdout, result.stderr)


if __name__ == "__main__":
    main()
