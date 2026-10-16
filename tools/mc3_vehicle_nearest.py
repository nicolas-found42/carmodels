"""Explicit nearest triangle controls for pinned official software GS, not actor state."""
import argparse
import copy
import json
from pathlib import Path
from mc3_vehicle_sampler import images, verify_sources, SOURCES
from mc3_vehicle_fragment import base_state, registers, rectangle
from mc3_vehicle_gif import initial_registers, packed
from mc3_vehicle_raster import cases
from mc3_reference_runtime import ad, run_gs, upload_rgba, write_gs_dump

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/vehicle-nearest.json'


def controls():
    source = images()
    rows = []
    for name, image, clamp, projective in [
            ('window-repeat', 'window', 0, False), ('window-clamp', 'window', 5, False),
            ('carbon-projective', 'carbon', 0, True),
            ('carbon-region', 'carbon', 3 | 3 << 2 | 7 << 4 | 16 << 14 | 15 << 24 | 32 << 34, False)]:
        vertices = copy.deepcopy(cases()[1]['vertices'])
        for i, (vertex, uv) in enumerate(zip(vertices, [[-.25000003, 1.2500001], [2.2000003, -.6000001], [.6000001, .8000002]], strict=True)):
            q = [0.5, 1.25, 2][i] if projective else 1
            vertex['stq'], vertex['rgba'] = [uv[0]*q, uv[1]*q, q], [128]*4
        rows.append(dict(name=name, texture=source[image], vertices=vertices, constantQ=not projective,
                         tex1='0x0000000000000000', clamp=f'0x{clamp:016x}'))
    return rows


def packets(case):
    image = case['texture']
    tex0 = 0x2000 | 1 << 14 | (image['width'].bit_length()-1) << 26 | (image['height'].bit_length()-1) << 30 | 1 << 34
    initial = [(a, tex0 if a == 6 else v) for a, v in initial_registers()]
    initial += [(0x14, int(case['tex1'], 16)), (8, int(case['clamp'], 16))]
    clear = base_state();clear['ztst'] = 1
    return [ad(initial+registers(clear, 4, True)), rectangle(0, 0, 256, 256, 0, [0]*4),
            upload_rgba(bytes(image['data']), image['width'], image['height'], 0x2000),
            ad(initial), packed(case['vertices'], 3 | 16), ad([(0, 0), (0x61, 0)])]


def reference(output, source_dir):
    proof = verify_sources({name: (source_dir/name).read_bytes() for name in SOURCES})
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in controls():
        dump = output/(case['name']+'.gs');write_gs_dump(dump, packets(case))
        receipt = run_gs(dump, output/case['name'], save_depth=True)
        row = dict(case=case, execution=receipt)
        for field in ['frames', 'depth_frames']:
            frames = {v['file'].split('_')[1]: v for v in receipt[field]}
            if len(frames) != 3 or len({(v['sha256'], tuple(v['size'])) for v in frames.values()}) != 1:
                raise ValueError('original nearest frames differ')
            row[field] = list(frames.values())
        records.append(row)
        print('PASS original nearest', case['name'], flush=True)
    return dict(schema=1, records=records, **proof,
                claim_limits=['Explicit MXL0 MMAG0 controls; not source-authored actor binding or physical PS2.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--write-fixture', action='store_true')
    args = parser.parse_args()
    result = reference(args.output, args.source_dir)
    encoded = json.dumps(result, separators=(',', ':'))+'\n'
    (args.output/'reference.json').write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)


if __name__ == '__main__':
    main()
