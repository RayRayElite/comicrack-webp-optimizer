"""Read normal and delay-load Windows DLL imports without executing the file."""
from pathlib import Path
import struct


def imports(path):
    data = Path(path).read_bytes()
    if data[:2] != b'MZ':
        raise ValueError('Not a Windows executable')
    pe = struct.unpack_from('<I', data, 60)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE signature')
    machine, count = struct.unpack_from('<HH', data, pe + 4)
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from('<H', data, optional)[0]
    if magic not in (267, 523):
        raise ValueError('Unsupported PE optional header')
    directory = optional + (96 if magic == 267 else 112)
    imagebase = struct.unpack_from('<I' if magic == 267 else '<Q', data, optional + (28 if magic == 267 else 24))[0]
    sections = []
    for index in range(count):
        size, start, rawsize, offset = struct.unpack_from('<IIII', data, optional + optional_size + index * 40 + 8)
        sections.append((start, max(size, rawsize), offset))

    def locate(rva):
        for start, size, offset in sections:
            if start <= rva < start + size:
                return offset + rva - start
        raise ValueError('RVA outside executable sections')

    def string(rva):
        at = locate(rva)
        return data[at:data.index(b'\0', at)].decode('ascii')

    found = set()
    rva = struct.unpack_from('<I', data, directory + 8)[0]
    if rva:
        at = locate(rva)
        while any(data[at:at + 20]):
            found.add(string(struct.unpack_from('<I', data, at + 12)[0]).lower())
            at += 20
    rva = struct.unpack_from('<I', data, directory + 13 * 8)[0]
    if rva:
        at = locate(rva)
        while any(data[at:at + 32]):
            flags, name = struct.unpack_from('<II', data, at)
            found.add(string(name if flags & 1 else name - imagebase).lower())
            at += 32
    return {'architecture': {0x8664: 'x64', 0x14c: 'x86'}.get(machine, hex(machine)), 'dlls': sorted(found)}


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(imports(sys.argv[1]), indent=2))
