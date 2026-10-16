"""Independent original software-GS fixed-UV sprite raster controls."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump
from mc3_vehicle_fragment import base_state, registers, rectangle
from verify_mc3_raster_reference import rgbaq

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/vehicle-sprite.json'
COMMIT = 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3'
SOURCES = {
    'GSRasterizer.cpp': 'a83f3c54c7754b4c384472bf8d284a03ccee9fdd70b2eefaa0ad67ff317f39ac',
    'GSSetupPrimCodeGenerator.all.cpp': '7c7a1143cab5b9dd362be602289aad8cf8e966a60ad9c9e3e93afeda62a293af',
    'GSRendererSW.cpp': '0382633722f2cb1b042cfa2fb4919deb2cb754ecdbdd46356731e76ceec2bae3',
}


def verify_sources(files):
    for name, digest in SOURCES.items():
        if name not in files or hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError('pinned sprite source changed: '+name)


def cases():
    image = dict(width=8, height=8, data=[v for y in range(8) for x in range(8)
                 for v in [(x*31+y*17) % 256, (x*13+y*29) % 256, (x*23+y*7) % 256, 64+(x+y)*9]])
    vertices = [dict(xy=[203, 287], z=100, rgba=[217, 29, 13, 17], uv=[7, 13]),
                dict(xy=[3659, 3881], z=60000, rgba=[128, 128, 128, 128], uv=[123, 119])]
    result = []
    for name in ['flat', 'textured', 'reverse-x', 'reverse-y', 'reverse-both', 'scissor', 'blend-mask', 'depth-clamp']:
        state = base_state()
        vs = copy.deepcopy(vertices)
        textured = name != 'flat'
        if name == 'flat':
            vs[1]['rgba'] = [173, 41, 222, 143]
        if name in ('reverse-x', 'reverse-y', 'reverse-both'):
            for axis in ([0, 1] if name == 'reverse-both' else [0 if name == 'reverse-x' else 1]):
                vs[0]['xy'][axis], vs[1]['xy'][axis] = vs[1]['xy'][axis], vs[0]['xy'][axis]
        if name == 'blend-mask':
            state.update(abe=True, blend=[0, 2, 1, 1, 0], fbmask=0xff000000)
        if name == 'depth-clamp':
            vs[1]['z'] = 0x10000
        result.append(dict(name=name, vertices=vs, texture=image, textured=textured, state=state,
                           xyOffset=[0, 0], scissor=[39, 29, 201, 209] if name == 'scissor' else [0, 0, 256, 256],
                           background=[7, 19, 31, 91]))
    return result


def packets(case):
    clear = base_state();clear['ztst'] = 1
    result = [ad([(0x18, 0), (0x40, 255 << 16 | 255 << 48), (0x45, 0), (0x1a, 1), (0x22, 0)]),
              ad(registers(clear, 4, True)), rectangle(0, 0, 256, 256, 0, case['background']),
              upload_rgba(bytes(case['texture']['data']), 8, 8), ad([(0x3f, 0)])]
    values = [(r, v) for r, v in registers(case['state'], 0 if case['textured'] else 4, True) if r != 0]
    values += [(0x06, 0x2000 | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34), (0x14, 288), (8, 0),
               (0x40, case['scissor'][0] | (case['scissor'][2]-1) << 16
                | case['scissor'][1] << 32 | (case['scissor'][3]-1) << 48),
               (0, 6 | int(case['textured']) << 4 | int(case['state']['abe']) << 6 | 1 << 8)]
    result.append(ad(values))
    for vertex in case['vertices']:
        result.append(ad([(1, rgbaq(*vertex['rgba'])), (3, vertex['uv'][0] | vertex['uv'][1] << 16),
                          (5, vertex['xy'][0] | vertex['xy'][1] << 16 | vertex['z'] << 32)]))
    result.append(ad([(0, 0), (0x61, 0)]))
    return result


def reference(output, source_dir):
    verify_sources({name: (source_dir/name).read_bytes() for name in SOURCES})
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in cases():
        dump = output/(case['name']+'.gs');write_gs_dump(dump, packets(case))
        receipt = run_gs(dump, output/case['name'], save_depth=True)
        original_packets = packets(case)
        row = dict(case=case, execution=receipt,
                   draw_chunks=[base64.b64encode(v).decode() for v in [original_packets[0], *original_packets[5:]]])
        for field in ['frames', 'depth_frames']:
            frames = list({v['file'].split('_')[1]: v for v in receipt[field]}.values())
            if len(frames) != 3 or len({(v['sha256'], tuple(v['size'])) for v in frames}) != 1:
                raise ValueError('original sprite frames differ')
            row[field] = frames
        records.append(row)
        print('PASS original sprite', case['name'], row['frames'][0]['sha256'], flush=True)
    return dict(schema=1, reference_commit=COMMIT, sources=SOURCES, records=records,
                claim_limits=['Explicit PSMCT32/Z16S fixed-UV bilinear sprites, not nearest/STQ sprite profiles or whole vehicle frames.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--write-fixture', action='store_true')
    args = parser.parse_args()
    value = reference(args.output, args.source_dir)
    encoded = json.dumps(value, separators=(',', ':'))+'\n'
    (args.output/'reference.json').write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)
    print('Original sprite contexts', len(value['records']), hashlib.sha256(encoded.encode()).hexdigest())


if __name__ == '__main__':
    main()
