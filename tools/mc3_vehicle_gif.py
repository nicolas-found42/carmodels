"""Construct native GIF consumer controls and retain original VU transports."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import struct

from mc3_reference_runtime import BINARY_SHA, ad, gif_chunks, run_gs, upload_rgba, write_gs_dump
from mc3_vehicle_fragment import base_state, registers, rectangle
from mc3_vehicle_raster import cases as triangle_cases
from verify_mc3_raster_reference import rgbaq

FIXTURE = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/vehicle-gif.json'


def tag(loops, regs, *, primitive=None, reglist=False):
    low = loops | 1 << 15 | int(reglist) << 58 | (len(regs) & 15) << 60
    if primitive is not None:
        low |= 1 << 46 | primitive << 47
    return struct.pack('<QQ', low, sum(r << (i*4) for i, r in enumerate(regs)))


def packed(vertices, primitive=None, fixed=False, xyz2=False):
    result = bytearray(tag(len(vertices), [3 if fixed else 2, 1, 5 if xyz2 else 4], primitive=primitive))
    for v in vertices:
        if fixed:
            result.extend(struct.pack('<4I', *v['uv'], 0, 0))
        else:
            result.extend(struct.pack('<3fI', *v['stq'], 0))
        result.extend(struct.pack('<4I', *v['rgba']))
        result.extend(struct.pack('<4I', *v['xy'], v['z'] if xyz2 else v['z'] << 4,
                                  int(v.get('adc', False)) << 15))
    return bytes(result)


def reglist(vertices, primitive=None):
    result = bytearray(tag(len(vertices), [2, 1, 4], primitive=primitive, reglist=True))
    for v in vertices:
        result.extend(struct.pack('<2f', *v['stq'][:2]))
        result.extend(struct.pack('<If', rgbaq(*v['rgba']) & 0xffffffff, v['stq'][2]))
        result.extend(struct.pack('<Q', v['xy'][0] | v['xy'][1] << 16 | v['z'] << 32))
    if len(result) % 16:
        result.extend(bytes(8))
    return bytes(result)


def tex0(base):
    return base | 1 << 14 | 3 << 26 | 3 << 30 | 1 << 34


def initial_registers():
    source = base_state()
    values = dict(registers(source, 0, True))
    values.update({0x1a: 1, 0x22: 0, 0x45: 0, 0x18: 0, 0x40: 255 << 16 | 255 << 48,
                   0x06: tex0(0x2000), 0x08: 0, 0x14: 96, 0x3b: 0})
    for first, second in [(0x06, 0x07), (0x08, 0x09), (0x14, 0x15), (0x18, 0x19),
                          (0x40, 0x41), (0x42, 0x43), (0x47, 0x48), (0x4a, 0x4b), (0x4c, 0x4d), (0x4e, 0x4f)]:
        values[second] = values[first]
    return sorted(values.items())


def controls():
    source = triangle_cases()[1]
    vertices = copy.deepcopy(source['vertices'])
    for i, v in enumerate(vertices):
        v['uv'] = [[20, 27], [180, 15], [40, 150]][i]
    image1 = source['texture']
    image2 = dict(width=8, height=8, data=[(v*3+19) % 256 if i % 4 != 3 else 128 for i, v in enumerate(image1['data'])])
    images = {'0x2000': image1, '0x2400': image2}
    result = []

    def add(name, parts):
        result.append(dict(name=name, initial=[[a, f'0x{v:016x}'] for a, v in initial_registers()],
                           chunks=[base64.b64encode(p).decode() for p in parts], images=images))

    # First two XYZF2 ADC bits do not suppress the later complete triangle.
    vs = copy.deepcopy(vertices)
    vs[0]['adc'] = True
    vs[1]['adc'] = True
    add('packed-strip-adc', [packed(vs, 4 | 8)])
    # REGLIST PRE is ignored by the selected GS, odd register counts pad to128.
    vs = copy.deepcopy(vertices)
    for v, q in zip(vs, [.5, 1.75, .875]):
        v['stq'] = [v['stq'][0]*q, v['stq'][1]*q, q]
    add('reglist-context2', [ad([(0, 3 | 8 | 16 | 512)]), reglist(vs, primitive=0)])
    # Actual A+D state transitions choose texture2, subtract blend and RGB mask,
    # followed by the native destination-alpha additive reflection equation.
    add('multipass-bindings', [ad([(0x42, 0x0a)]), packed(vertices, 4 | 8 | 16 | 64),
                              ad([(6, tex0(0x2400)), (0x42, 0x81), (0x4c, 4 << 16 | 0xff000000 << 32)]),
                              packed(vertices, 5 | 8 | 16 | 64),
                              ad([(6, tex0(0x2000)), (0x42, 0x58)]),
                              packed([{**v, 'rgba': [127, 127, 127, 0]} for v in vertices], 4 | 16 | 64)])
    # Same-class PRIM changes must not split Q tracing. A zero-loop PRE between
    # the first two and last vertices must not change primitive assembly.
    vs = copy.deepcopy(vertices)
    for v in vs:
        v['z'] = 2000
    later = [{**v, 'stq': [v['stq'][0]*2, v['stq'][1]*2, 2]} for v in vs]
    add('constant-depth-q-dispatch', [packed(vs[:2], 4 | 8 | 16), tag(0, [0], primitive=0),
                                      packed(vs[2:]), ad([(0x42, 255), (0x49, 1), (0x3b, 1 << 40)]),
                                      packed(later, 5 | 8 | 16)])
    add('fixed-uv-mixed-clamp', [ad([(8, 1)]), packed(vertices, 4 | 8 | 16 | 256, fixed=True)])
    add('packed-xyz2', [packed(vertices, 4 | 8, xyz2=True)])
    add('prmode-context2', [ad([(0x1a, 0), (0x1b, 8 | 16 | 512), (0, 3 | 0x1f8)]), reglist(vertices, primitive=0)])
    # Pinned GSState ignores PRMODE writes while AC1; changing AC alone does
    # not restore another saved attribute word. Under AC0 PRIM changes type
    # only, retaining the most recently installed effective flags.
    regions = [[{**v, 'xy': [v['xy'][0]//3+region*85*16, v['xy'][1]//2]} for v in vertices]
               for region in range(3)]
    add('prmode-dynamic-toggle', [ad([(0, 3 | 8), (0x1b, 16 | 512), (0x1a, 0)]), reglist(regions[0]),
                                  ad([(0x1b, 8 | 16 | 512), (0, 3), (0x1a, 1)]), reglist(regions[1]),
                                  ad([(0x1b, 0), (0x1a, 0), (0, 3 | 256)]), reglist(regions[2])])
    return result


def native_transports(root):
    rows = []
    for directory in sorted(Path(root).glob('*-run')):
        raw = (directory/'gif-chunks.bin').read_bytes()
        receipt = json.loads((directory/'receipt.json').read_text())
        job = Path(root)/(directory.name.removesuffix('-run')+'.job')
        if (receipt['status'] != 'executed' or receipt['mode'] != 'vu'
                or receipt['runtime']['binary_sha256'] != BINARY_SHA
                or hashlib.sha256(raw).hexdigest() != receipt['outputs']['gif-chunks.bin']['sha256']
                or hashlib.sha256(job.read_bytes()).hexdigest() != receipt['job_sha256']):
            raise ValueError('original whole-program transport/job identity differs')
        chunks = gif_chunks(raw)
        stream = b''.join(chunks)
        offset, latch_q, st, rgba, q = 0, 0x3f800000, None, None, None
        vertices = bytearray()
        while offset < len(stream):
            low, high = struct.unpack_from('<QQ', stream, offset)
            offset += 16
            count, nreg, fmt = low & 32767, (low >> 60) & 15 or 16, (low >> 58) & 3
            if count:
                latch_q = 0x3f800000
            if fmt != 0:
                raise ValueError('native corpus transport requires additional format proof')
            for i in range(count*nreg):
                reg = high >> ((i % nreg)*4) & 15
                words = struct.unpack_from('<4I', stream, offset)
                if reg == 2:
                    st, latch_q = words[:2], words[2]
                elif reg == 1:
                    rgba, q = [word & 255 for word in words], latch_q
                elif reg in (4, 5):
                    xy = [words[0] & 65535, words[1] & 65535]
                    z = words[2] >> 4 & 0xffffff if reg == 4 else words[2]
                    fog = words[3] >> 4 & 255 if reg == 4 else 0
                    vertices.extend(struct.pack('<HHI4B3IHHBBH', *xy, z, *rgba, *st, q,
                                                65535, 65535, fog, bool(words[3] & 0x8000), 0))
                offset += 16
        rows.append(dict(program=directory.name.removesuffix('-run'), source_sha256=hashlib.sha256(raw).hexdigest(),
                         job_sha256=receipt['job_sha256'], adapter_sha256=receipt['adapter_sha256'],
                         runtime_binary_sha256=receipt['runtime']['binary_sha256'],
                         chunks=[base64.b64encode(p).decode() for p in chunks], vertices=len(vertices)//32,
                         vertex_words_sha256=hashlib.sha256(vertices).hexdigest()))
    if len(rows) != 13:
        raise ValueError('all13 original whole-program transports are required')
    return rows


def reference(output, native_root):
    records = []
    for case in controls():
        source = base_state()
        source['ztst'] = 1
        init = [(a, int(v, 16)) for a, v in case['initial']]
        packets = [ad(init + registers(source, 4, True)), rectangle(0, 0, 256, 256, 0, [0, 0, 0, 0])]
        for key, image in case['images'].items():
            packets.append(upload_rgba(bytes(image['data']), image['width'], image['height'], int(key, 16)))
        packets += [ad(init), *[base64.b64decode(p) for p in case['chunks']], ad([(0, 0), (0x61, 0)])]
        dump = output/(case['name']+'.gs')
        write_gs_dump(dump, packets)
        receipt = run_gs(dump, output/case['name'], save_depth=True)
        finals = {}
        for field in ['frames', 'depth_frames']:
            frames = {}
            for row in receipt[field]:
                frames[row['file'].split('_')[1]] = row
            if len(frames) != 3 or len({(r['sha256'], tuple(r['size'])) for r in frames.values()}) != 1:
                raise ValueError('native GIF reference frames differ')
            finals[field] = list(frames.values())
        records.append(dict(case=case, **finals, runtime=receipt['runtime'], dump_sha256=receipt['dump_sha256']))
        print(case['name'], 'three RGBA', finals['frames'][-1]['sha256'],
              'three Z16', finals['depth_frames'][-1]['sha256'], flush=True)
    return dict(schema=1, records=records, native_transports=native_transports(native_root),
                claim_limits=['Original13VU transports plus explicit controlled software-GS draws; not complete live vehicle frames or physical PS2.'])


def verify_reference(actual, expected):
    if actual['native_transports'] != expected['native_transports']:
        raise ValueError('original whole-program transport inputs differ')
    if len(actual['records']) != len(expected['records']):
        raise ValueError('native GIF control count differs')
    for row, saved in zip(actual['records'], expected['records']):
        if row['case'] != saved['case'] or row['dump_sha256'] != saved['dump_sha256']:
            raise ValueError('native GIF control inputs differ')
        for field in ['frames', 'depth_frames']:
            if [(v['size'], v['sha256']) for v in row[field]] != [(v['size'], v['sha256']) for v in saved[field]]:
                raise ValueError('native GIF output bytes differ')
    return dict(status='pass', controls=len(actual['records']), programs=len(actual['native_transports']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-root', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write-fixture', action='store_true')
    mode.add_argument('--verify-fixture', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    value = reference(args.output, args.native_root)
    encoded = json.dumps(value, separators=(',', ':'))+'\n'
    (args.output/'reference.json').write_text(encoded)
    if args.write_fixture:
        FIXTURE.write_text(encoded)
    if args.verify_fixture:
        verify_reference(value, json.loads(FIXTURE.read_text()))


if __name__ == '__main__':
    main()
