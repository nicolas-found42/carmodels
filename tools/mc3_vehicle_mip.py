"""Explicit constant-LOD controls for the pinned original software GS.

Synthetic original GS events isolate sampler behavior; no authored vehicle
material selection or running-game frame is asserted.
"""
import argparse
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from mc3_vehicle_fragment import base_state, registers, rectangle
from mc3_vehicle_gif import initial_registers, packed
from mc3_vehicle_sampler import SOURCES, verify_sources

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/vehicle-mip.json'
EXTRA_SOURCES = {
    'GSScanlineEnvironment.h': 'b9972ac00b97f66a2084f1269ce3ea4493d3135f4f258c8de45eb7efa4ac282d',
    'GSVector4i.h': 'f469fab789fd335e9544149eccd00bb20ab4e39566d1ca1df573fa2cdf049992',
}


def controls():
    rows = []
    levels = [{'width': size, 'height': size, 'data_hex': (bytes(color)*size*size).hex()}
              for size, color in [(8, [20, 40, 60, 32]), (4, [40, 60, 80, 64]),
                                  (2, [200, 220, 240, 192])]]
    for mmin, k, start in [(2, 8, 0), (2, 24, 0), (3, 4, 0), (3, 8, 0),
                           (3, 24, 1), (4, 15, 0), (4, 24, 0), (5, 4, 0),
                           (5, 8, 0), (5, 24, 0), (5, 24, 3), (5, 31, 0),
                           (5, 32, 0), (5, 48, 0)]:
        vertices = [{'xy': [x*16, y*16], 'z': 10, 'stq': [s, t, 1], 'rgba': [128]*4}
                    for x, y, s, t in [(start, 0, 0, 0), (start+16, 0, 1, 0), (start, 16, 0, 1)]]
        tex1 = 1 | 2 << 2 | 1 << 5 | mmin << 6 | k << 32
        rows.append(dict(name=f'mmin{mmin}-k{k}-x{start}', tex1=str(tex1), clamp='0',
                         levels=levels, vertices=vertices))
    pattern_levels = []
    for level, size in enumerate([8, 4, 2]):
        raw = bytes((x*37+y*19+channel*53+level*41) & 255
                    for y in range(size) for x in range(size) for channel in range(4))
        pattern_levels.append(dict(width=size, height=size, data_hex=raw.hex()))
    for mmin, k, start in [(2, 8, 1), (3, 24, 1), (4, 24, 0), (5, 24, 3), (5, 48, 1)]:
        vertices = [{'xy': [x*16, y*16], 'z': 10, 'stq': [s, t, 1], 'rgba': [128]*4}
                    for x, y, s, t in [(start, 0, -.23, 1.2), (start+16, 0, 1.7, -.31),
                                       (start, 16, .27, .83)]]
        rows.append(dict(name=f'pattern-mmin{mmin}-k{k}-x{start}',
                         tex1=str(1 | 2 << 2 | 1 << 5 | mmin << 6 | k << 32),
                         clamp='0', levels=pattern_levels, vertices=vertices))
    return rows


def packets(case):
    tex0 = 0x2000 | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34
    initial = [(a, tex0 if a == 6 else v) for a, v in initial_registers()]
    initial += [(0x14, int(case['tex1'])), (8, int(case['clamp'])),
                (0x34, 0x2100 | 1 << 14 | 0x2200 << 20 | 1 << 34)]
    state = base_state()
    state['ztst'] = 1
    output = [ad(initial+registers(state, 4, True)), rectangle(0, 0, 256, 256, 0, [0]*4)]
    for base, level in zip([0x2000, 0x2100, 0x2200], case['levels'], strict=True):
        output.append(upload_rgba(bytes.fromhex(level['data_hex']), level['width'], level['height'], base))
    return output+[ad(initial), packed(case['vertices'], 3 | 16), ad([(0, 0), (0x61, 0)])]


def reference(output, source_dir):
    files = {name: (source_dir/name).read_bytes() for name in SOURCES | EXTRA_SOURCES}
    source = verify_sources(files)
    for name, digest in EXTRA_SOURCES.items():
        if hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError('pinned mip source changed: '+name)
    source['sources'] = dict(source['sources']) | EXTRA_SOURCES
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in controls():
        dump = output/(case['name']+'.gs')
        write_gs_dump(dump, packets(case))
        execution = run_gs(dump, output/case['name'], save_depth=True)
        row = dict(case=case, execution=execution)
        for name in ['frames', 'depth_frames']:
            final = {v['file'].split('_')[1]: v for v in execution[name]}
            if len(final) != 3 or len({(v['sha256'], tuple(v['size'])) for v in final.values()}) != 1:
                raise ValueError('original mip frames differ')
            row[name] = list(final.values())
        rows.append(row)
        print('PASS original constant mip', case['name'], flush=True)
    result = dict(schema=1, **source, records=rows,
                  claim_limits=['Explicit LCM1/MXL2, positive constant K and MMIN2..5 controls; variable Q LOD is separate.',
                                'Three controlled CT32 levels and nonzero alpha differences expose lane behavior.',
                                'Pinned AVX2/FMA software GS, not physical PS2 or a booted MC3 frame.',
                                'No vehicle shader binding, texture residency or showcase activation claim.'])
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--write-fixture', action='store_true')
    args = parser.parse_args()
    proof = reference(args.output, args.source_dir)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, indent=2)+'\n')
