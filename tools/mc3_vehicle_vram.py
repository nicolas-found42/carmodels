"""Pinned original GS IMAGE controls and exhaustive address-table evidence."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, write_gs_dump
from mc3_vehicle_fragment import base_state, registers
from mc3_vehicle_gif import initial_registers, packed

COMMIT = 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3'
FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/vehicle-vram.json'
SUPPORT_SOURCES = {'GSLocalMemory.h': '8cd6ed874f53aafde5f3d294048b2b0beed87765ab099a5f8aa93899cb988a19',
                   'GSLocalMemory.cpp': '46da01086c93f3839c0c20787433f8cd0b7b89790d42f12414f9589c66fd4e51',
                   'GSTables.h': '34c60c7163952ed34c4b150e603d8bc78aa35ed6661d684c485510167b9cc0eb',
                   'GSClut.cpp': '9f4ed253c162855bc4d2838c08b522cbd28b6af96d03abd44cf0f83415bb1e32'}
SOURCE_SHA = 'a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8'
LIMITS = [
        'Explicit zero 4 MiB initial VRAM in reference controls; runtime requires explicit existing VRAM.',
        'CT32/PSMT8/PSMT4 host-to-local traversal 0; CSM1 CT32 CSA0 palettes only.',
        'CLD1 native draw controls; other CLD modes source-derived and unit-controlled, not native cache goldens.',
        'Final address overflow, CSM2, CSA offsets, other pixel formats and transfer directions fail closed.',
        'Controlled original GS events, not a booted MC3 gameplay frame.']
PROFILES = {0: (8, 8, [1, 4, 8, 2, 16, 32]),
            19: (16, 16, [4, 16, 32, 2, 8, 33, 96, 128]),
            20: (32, 16, [8, 32, 64, 2, 4, 16, 65, 192, 256])}


def xor_bits(value, basis):
    result = 0
    for bit, word in enumerate(basis):
        if value & 1 << bit:
            result ^= word
    return result


def verify_tables(source):
    counts = {}
    for psm, (width, height, basis) in PROFILES.items():
        name = {0: '32', 19: '8', 20: '4'}[psm]
        match = re.search(r'columnTable'+name+r'\[\d+\]\[\d+\]\s*=\s*\{(.*?)\n\};', source, re.S)
        text = re.sub(r'//[^\n]*', '', match.group(1))
        actual = [int(v) for v in re.findall(r'\d+', text)]
        expected = [xor_bits(x+y*width, basis) for y in range(height) for x in range(width)]
        if expected != actual:
            raise ValueError('column address formula differs from original table: '+name)
        counts[name] = len(actual)
    for name, width, basis in [('32', 8, [1, 4, 16, 2, 8]),
                                ('8', 8, [1, 4, 16, 2, 8]), ('4', 4, [2, 8, 1, 4, 16])]:
        match = re.search(r'_blockTable'+name+r'\[\d+\]\[\d+\]\s*=\s*\{(.*?)\n\};', source, re.S)
        actual = [int(v) for v in re.findall(r'\d+', match.group(1))]
        if actual != [xor_bits(i, basis) for i in range(32)]:
            raise ValueError('block address formula differs from original table')
    return counts


def image_upload(data, width, height, base, psm=0, bw=1, x=0, y=0):
    padded = data + bytes((-len(data)) % 16)
    regs = [(0x50, base << 32 | bw << 48 | psm << 56),
            (0x51, x << 32 | y << 48), (0x52, width | height << 32), (0x53, 0)]
    return dict(registers=[[r, str(v)] for r, v in regs], hex=padded.hex(),
                packet=(ad(regs)+struct.pack('<QQ', len(padded)//16 | 1 << 15 | 2 << 58, 0)+padded).hex())


def controls():
    rows = []
    palette = bytes(v for i in range(256) for v in [i, (i*7)&255, (255-i), (i*13)&255])
    for name, upload_psm, sample_psm, width, height, bw in [
            ('ct32', 0, 0, 16, 16, 1), ('indexed8', 19, 19, 32, 32, 1),
            ('indexed4', 20, 20, 32, 32, 1), ('packed32-as8', 0, 19, 16, 16, 1),
            ('packed32-as4', 0, 20, 16, 16, 1), ('indexed8-odd-width-page', 19, 19, 128, 128, 3),
            ('indexed4-odd-pixels', 20, 20, 3, 3, 1)]:
        bits = {0: 32, 19: 8, 20: 4}[upload_psm]
        data = bytes((i*37+11)&255 for i in range((width*height*bits+7)//8))
        size = 128 if 'odd-width' in name else 32 if sample_psm else 16
        tex0 = (0x2000 | bw << 14 | sample_psm << 20 | (size.bit_length()-1) << 26 |
                (size.bit_length()-1) << 30 | 1 << 34 | 0x3000 << 37 | 1 << 61)
        uploads = [image_upload(data, width, height, 0x2000, upload_psm, bw),
                   image_upload(palette, 16, 16, 0x3000)]
        if sample_psm == 20:
            uploads[-1] = image_upload(palette[:64], 8, 2, 0x3000)
        vertices = [dict(xy=[0, 0], z=0, uv=[8, 8], rgba=[128]*4),
                    dict(xy=[size*16, 0], z=0, uv=[size*16+8, 8], rgba=[128]*4),
                    dict(xy=[0, size*16], z=0, uv=[8, size*16+8], rgba=[128]*4)]
        rows.append(dict(name=name, tex0=str(tex0), uploads=uploads, size=size, vertices=vertices))
    return rows


def verify_sources(source_dir):
    for name, digest in SUPPORT_SOURCES.items():
        if hashlib.sha256((source_dir/name).read_bytes()).hexdigest() != digest:
            raise ValueError('pinned original GS source changed: '+name)
    return {name: dict(sha256=digest, url=f'https://raw.githubusercontent.com/PCSX2/pcsx2/{COMMIT}/pcsx2/GS/{name}')
            for name, digest in SUPPORT_SOURCES.items()}


def reference(output, source_dir):
    output.mkdir(parents=True, exist_ok=False)
    source = (source_dir/'GSTables.cpp').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise ValueError('pinned original GSTables source changed')
    proof = dict(commit=COMMIT, supporting_sources=verify_sources(source_dir), gstables_sha256=hashlib.sha256(source).hexdigest(),
                 exhaustive_columns=verify_tables(source.decode()), table_source_hex=source.hex())
    rows = []
    for case in controls():
        initial = initial_registers()+[(0x14, 32), (8, 5), (0x06, int(case['tex0']))]
        # Upload before TEX0 so the literal CLD=1 loads the uploaded CLUT.
        packets = [bytes.fromhex(u['packet']) for u in case['uploads']]
        source_state = base_state()
        source_state['ztst'] = 1
        packets += [ad(registers(source_state, 0, True)+initial),
                    packed(case['vertices'], 3 | 16 | 256, fixed=True), ad([(0, 0), (0x61, 0)])]
        dump = output/(case['name']+'.gs')
        write_gs_dump(dump, packets)
        receipt = run_gs(dump, output/case['name'], save_depth=True)
        rows.append(dict(case=case, execution=receipt, draw_chunks=[p.hex() for p in packets[len(case['uploads']):]]))
    result = dict(source=proof, controls=rows, claim_limits=LIMITS)
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    args = parser.parse_args()
    reference(args.output, args.source_dir)
