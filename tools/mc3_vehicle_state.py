"""Original MC3 EE render-state packing controls for the browser GS/VU join.

The native helper is unchanged; a wrapper copies only its DMA cursor to RAM.
All engine state and framebuffer inputs are explicit controlled contexts.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/vehicle-state.json'
INTERVALS = [(0x2ad228, 0x2adb44, '5581ad4d51b71e3560f390bb3bbf1d70fa9d83ab0141a3aaac88ceca2ec0fdc1'),
             (0x528c18, 0x528c6c, 'e9142f6089a23606e09460996e06d8596787638fa0dcb3a3e939555c8ede7c75'),
             (0x615e20, 0x615e48, '1fe63eaab7bc5abcac0e8cd9926a7b857e7135b7ebe39afb704ea8c22ddc8828')]


def need(value, message):
    if not value:
        raise ValueError(message)


def source_contract(executable):
    need(hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA, 'native state executable changed')
    for start, end, digest in INTERVALS:
        need(hashlib.sha256(_read_elf(executable, start, end-start)).hexdigest() == digest,
             'native state source interval changed')


def reference_job(context):
    words = context['words']
    need(len(words) == 21 and all(type(v) is int and 0 <= v <= 0xffffffff for v in words),
         'invalid native state words')
    need(context['bpp'] == 32 and context['zbits'] == 16 and context['colorMode'] in (1, 2),
         'unsupported native state context')
    spad = bytearray(16384)
    struct.pack_into('<21I', spad, 0x60, *words)
    # Force complete supported update, excluding shader pointer/microcode load.
    struct.pack_into('<I', spad, 0x10c, 0x1cffff)
    struct.pack_into('<I', spad, 0x114, context['colorMode'])
    struct.pack_into('<I', spad, 0x118, context['primitiveBase'])
    struct.pack_into('<2I', spad, 0x5ac, 0x1006000, 0x100f000)
    code = struct.pack('<10I', 0x0c000000 | (0x2ad228 >> 2), 0, 0x3c087000, 0x8d0905ac,
                       0x3c0a0100, 0xad490000, 0x3c1f0001, 0x03e00008, 0, 0)
    patches = [(0x100a000, code), (0x70000000, spad),
               (0x715c7c, struct.pack('<I', context['frameBase'])),
               (0x70e510, struct.pack('<I', context['frameWidth'])),
               (0x70fad8, struct.pack('<2I', context['bpp'], context['zbits'])),
               (0x6f4888, struct.pack('<Q', context['zbuf']))]
    data = bytearray(b'MC3EE001')+struct.pack('<5I', 0x100a000, 100000, 0, 0, len(patches))
    for address, raw in patches:
        data += struct.pack('<2I', address, len(raw))+raw
    return bytes(data)


def decode_reference(ram):
    need(len(ram) == 32*1024*1024, 'native state RAM extent changed')
    end = struct.unpack_from('<I', ram, 0x1000000)[0]
    need(0x1006000 < end <= 0x100f000 and end % 16 == 0, 'native state DMA cursor invalid')
    raw, gs, vu, cursor = ram[0x1006000:end], [], {}, 0
    while cursor < len(raw):
        tag, zero, flush, command = struct.unpack_from('<4I', raw, cursor)
        size = (tag & 65535)*16
        need(tag >> 16 == 0x1000 and zero == 0 and flush == 0x11000000
             and cursor+16+size <= len(raw), 'unexpected native state DMA packet')
        payload = raw[cursor+16:cursor+16+size]
        if command >> 24 == 0x6c:
            need(size == 16 and command >> 16 & 255 == 1, 'unexpected native state VIF packet')
            slot = command & 1023
            need(slot not in vu, 'duplicate native state VU destination')
            vu[slot] = list(struct.unpack('<4I', payload))
        else:
            need(command >> 16 == 0x5000 and command & 65535 == len(payload)//16,
                 'unexpected native state DIRECT packet')
            low, high = struct.unpack_from('<QQ', payload)
            count = low & 32767
            need(low == count | 0x1000000000008000 and high == 14 and len(payload) == (count+1)*16,
                 'unexpected native state GIF tag')
            for offset in range(16, len(payload), 16):
                value, register = struct.unpack_from('<QQ', payload, offset)
                gs.append([register, str(value)])
        cursor += 16+size
    return dict(dma_sha256=hashlib.sha256(raw).hexdigest(), gs=gs, vu=vu)


def execute_reference(executable, contexts, output, runner=None):
    from mc3_reference_runtime import run_job
    runner = run_job if runner is None else runner
    executable, output = Path(executable), Path(output)
    source_contract(executable.read_bytes())
    need(not output.exists(), 'choose a fresh native state output')
    output.mkdir(parents=True)
    rows = []
    for context in contexts:
        name = context['name']
        need(name.isascii() and name.replace('-', '').isalnum(), 'invalid native state reference name')
        path, directory = output/(name+'.job'), output/name
        path.write_bytes(reference_job(context))
        receipt = runner(path, directory, mode='ee', executable=executable)
        need(receipt['status'] == 'executed' and receipt['original_mc3_executable_sha256'] == EXECUTABLE_SHA,
             'native state execution identity changed')
        rows.append({**context, **decode_reference((directory/'ee-ram.bin').read_bytes()), 'execution': receipt})
    (output/'reference.json').write_text(json.dumps(rows, indent=2)+'\n')
    return rows
