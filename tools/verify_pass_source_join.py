#!/usr/bin/env python3
"""Join the 100 aligned pass-4/5 draws to source Headers and the pass-4 render target.

Offline capture content, not an execution trace or a renderer. --write exports
capture-time GS memory and writes the receipt; ordinary runs reproduce both.
"""
import json
from pathlib import Path
import struct
import sys

import gsdump
import ps2_container
import ps2_sections
from recover_car_mips import png_bytes
import static_inputs
import verifier_common as common
import verify_vu_handler_dump as comparison

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/evidence/vu-dispatch/pass-source-join.json'
IMAGE = OUT.parent / 'pass4-retained-target.png'
GS = ROOT / 'research/evidence/continuation/runtime/linux/race95-GS.bin'
GS_PIN = '854147006e377425b3c3ebd93e4754a3cdc9b35e3fb9885bb480ee35cfaa84a9'
FUNCTION_PINS = {
    '0021bf28': '8dba1e04bbc99aabff2acdd1300e2e13779c4c513a098fa75120c307911a83e4',
    '0021c3e0': '618edec8f6437d909769be78b61ac3abc1db5aff05a3e9350c6ef670a066bee3',
    '0021b850': 'bd94c10f33a7b9db1fc65d0401ea83d18ff9efa59e77fa4e294bab4ae5d4a24d',
    '00127738': '6f557beea56273c17c994e33d3474df222a67e3ff5a4271cb3cc8c49759fab60',
    '00127730': '029550db2a974f585919addb8db51151a55583fb288e64101e4b9a25852b8570',
}


class JoinError(ValueError):
    pass


need = common.make_need(JoinError)


def runtime_paths():
    return [GS, comparison.gj.DUMP, comparison.ring_tools.vb.CAPTURES['race95'],
            ROOT / 'research/evidence/continuation/runtime/linux/race95-vu1Memory.bin',
            ROOT / 'research/evidence/continuation/runtime/linux/race95-state-identity.json']


def load_inputs():
    for path in runtime_paths():
        if not path.is_file():
            raise SystemExit('runtime input missing: %s (see docs/static-inputs.md)' % path.name)
    inputs = comparison.load_inputs()
    mem = comparison.ring_tools.vb.CAPTURES['race95'].read_bytes()
    gs = GS.read_bytes()
    need(common.sha256(gs) == GS_PIN, 'retained GS memory differs from capture pin')
    census_path = comparison.ring_tools.vb.CENSUS
    census = json.loads(census_path.read_bytes())
    cars = {}
    for car in census['cars']:
        path = next((ROOT / 'reference/ford/cars' / car['code'] / 'model').iterdir())
        data = path.read_bytes()
        need(common.sha256(data) == car['sha256'], 'source model identity differs: ' + car['code'])
        parsed = ps2_container.parse(data)
        _, geo = ps2_sections.geometry(data, parsed)
        cars[car['code']] = (data, geo['headers'], parsed['textures']['items'])
    export = static_inputs.typed_export()
    inventory_raw = (export / 'inventory.json').read_bytes()
    elf = static_inputs.executable().read_bytes()
    pins = static_inputs.pins()
    need(common.sha256(inventory_raw) == pins['inventory_sha256'], 'typed inventory pin differs')
    need(common.sha256(elf) == pins['executable_sha256'], 'executable pin differs')
    inventory = json.loads(inventory_raw)
    phoff = struct.unpack_from('<I', elf, 28)[0]
    stride, count = struct.unpack_from('<HH', elf, 42)
    loads = [struct.unpack_from('<8I', elf, phoff + i * stride) for i in range(count)]
    checked = {}
    for entry, pin in FUNCTION_PINS.items():
        source = (export / 'decompilation/functions' / (entry + '.c')).read_bytes()
        need(common.sha256(source) == pin, 'decompilation function pin differs: ' + entry)
        fn = next(f for f in inventory['functions'] if f['entry'] == entry)
        for instruction in fn['instructions']:
            address = int(instruction['address'], 16)
            data = bytes.fromhex(instruction['bytes'])
            segments = [s for s in loads if s[0] == 1 and s[2] <= address and address + len(data) <= s[2] + s[4]]
            need(len(segments) == 1, 'instruction segment is ambiguous')
            segment = segments[0]
            offset = segment[1] + address - segment[2]
            need(elf[offset:offset + len(data)] == data, 'instruction differs from executable')
        checked[entry] = {'decompilation_sha256': pin, 'instructions_checked_against_elf': len(fn['instructions'])}
    transfers, dump_sha = gsdump.load_transfers(comparison.gj.DUMP, comparison.gj.DUMP_PIN)
    inputs.update(mem=mem, gs=gs, cars=cars, transfers=transfers, source_functions=checked)
    inputs['pins'].update(retained_gs_sha256=GS_PIN, census_sha256=common.sha256(census_path.read_bytes()),
                          inventory_sha256=pins['inventory_sha256'], executable_sha256=pins['executable_sha256'])
    need(inputs['pins']['dump_decompressed_sha256'] == dump_sha, 'dump identity differs across reads')
    return inputs


def tex0_fields(value):
    return {'TBP0': value & 0x3fff, 'TBW': (value >> 14) & 63, 'PSM': (value >> 20) & 63,
            'width': 1 << ((value >> 26) & 15), 'height': 1 << ((value >> 30) & 15)}


def target_image(gs, texture):
    # PCSX2 v2.8.2 GSState::Freeze version 9: no alignment padding in WriteState.
    prefix = 4 + 15 * 8 + 2 * 12 * 8 + 32 + 8 + 2 * 4 + 2 * 4 + 3 * 8 + 16 + 3 * 4 + 1
    tail = 4 * (16 + 4) + 4  # four GIFPath tag/reg pairs, then m_q
    need(struct.unpack_from('<I', gs)[0] == 9 and len(gs) == prefix + 4194304 + tail,
         'unsupported GS freeze layout')
    need(texture['PSM'] == 10, 'unsupported sampled texture format')
    vm = gs[prefix:prefix + 4194304]
    rgba, packed = bytearray(), bytearray()
    for y in range(texture['height']):
        for x in range(texture['width']):
            bx, by = (x % 64) // 16, (y % 64) // 8
            # GSTables.cpp _blockTable16S and columnTable16 as bit permutations.
            block = ((bx & 1) << 1) | ((bx & 2) << 3) | (by & 1) | ((by & 2) << 2) | (by & 4)
            px, py = x % 16, y % 8
            column = ((px & 1) << 1) | ((px & 2) << 2) | ((px & 4) << 2) | ((px & 8) >> 3)
            column |= ((py & 1) << 2) | ((py & 2) << 4) | ((py & 4) << 4)
            page = (y // 64) * texture['TBW'] + x // 64
            address = ((texture['TBP0'] + 32 * page + block) * 256 + 2 * column) % 4194304
            word = vm[address:address + 2]
            packed.extend(word)
            value = int.from_bytes(word, 'little')
            rgba.extend(((value & 31) << 3, ((value >> 5) & 31) << 3, ((value >> 10) & 31) << 3, 255))
    png = png_bytes(texture['width'], texture['height'], bytes(rgba))
    return png, {'gs_freeze_vram_offset': prefix, 'packed_row_major_sha256': common.sha256(packed),
                 'preview_rgba_sha256': common.sha256(rgba), 'png_sha256': common.sha256(png),
                 'png_path': str(IMAGE.relative_to(ROOT)), 'alpha': 'opaque RGB preview; not GS TEXA or framebuffer alpha'}


def dump_bindings(transfers, targets):
    registers, writes, bindings, rendered = {}, {}, {}, []
    for ti, data in enumerate(transfers[:max(targets) + 1]):
        for off, lo, hi, nloop, flg, nreg, _ in gsdump.iter_tags(data):
            if flg == 0 and hi == 0xe:
                need(nreg == 1, 'unsupported A+D tag shape')
                for i in range(nloop):
                    value, register = struct.unpack_from('<QQ', data, off + 16 + 16 * i)
                    registers[register] = value
                    writes[register] = {'transfer': ti, 'payload_offset': off + 16 + 16 * i}
            if flg == 0 and hi == 0x412:
                # This dump's geometry uses context 1; inherited state must be present.
                prim = (lo >> 47) & 0x7ff
                if ti in targets:
                    need(prim & 0x200 == 0 and prim & 0x10, 'target texture context/TME differs')
                    need(6 in registers and 0x4c in registers, 'target GS binding missing')
                    bindings[ti] = {'TEX0_1': registers[6], 'tex0_write': dict(writes[6]),
                                    'FRAME_1': registers[0x4c], 'vertices': nloop, 'prim': prim}
                frame = registers.get(0x4c, 0)
                if (frame & 0x1ff) * 32 == 0x29c0 and (frame >> 24) & 63 == 10:
                    need(registers.get(0x40) == 0x7f000000ff0000, 'render-target scissor differs')
                    rendered.append({'transfer': ti, 'vertices': nloop, 'FRAME_1': frame,
                                     'SCISSOR_1': registers[0x40]})
    need(set(bindings) == set(targets), 'target geometry binding coverage differs')
    return bindings, rendered


def derive(inputs):
    content = comparison.derive(inputs)
    need(len(content['rows']) == 100, 'aligned draw coverage differs')
    cars, mem = inputs['cars'], inputs['mem']
    pairs = [(i, t) for i, t in inputs['align']['matched_pairs'] if inputs['align']['draws'][i].get('pass_id') in (4, 5)]
    bases = comparison.ring_tools.car_bases(mem, {c: (d, h) for c, (d, h, _) in cars.items()})
    need({c: hex(b) for c, b in bases.items()} == inputs['align']['car_bases_in_ee'], 'located car bases differ')
    bindings, rendered = dump_bindings(inputs['transfers'], [t for _, t in pairs])
    pointer = struct.unpack_from('<I', mem, 0x28f1b0)[0]
    need(0 < pointer <= len(mem) - 64, 'global pass4 texture object outside EE memory')
    object_words = struct.unpack_from('<16I', mem, pointer)
    # FUN_0021b850 emits TEX0 low = object[4]|object[1], high = object[3]|CLUT<<5.
    # The retained object is direct colour, hence no CLUT allocation.
    object_tex0 = (object_words[3] << 32) | object_words[4] | object_words[1]
    texture = tex0_fields(object_tex0)
    need(texture == {'TBP0': 0x29c0, 'TBW': 4, 'PSM': 10, 'width': 256, 'height': 128},
         'global pass4 texture object layout differs')
    need(struct.unpack_from('<I', mem, 0x2907b0)[0] == pointer, 'view texture table differs from pass4 global')
    need(all(not b <= pointer < b + len(cars[c][0]) for c, b in bases.items()), 'pass4 object lies inside a car model')
    first_sample = min(t for i, t in pairs if inputs['align']['draws'][i]['pass_id'] == 4)
    before = [r for r in rendered if r['transfer'] < first_sample]
    need(before, 'no preceding draw to sampled render target')
    rows = []
    for i, transfer in pairs:
        draw = inputs['align']['draws'][i]
        candidates = comparison.ring_tools.header_for({c: (d, h) for c, (d, h, _) in cars.items()},
                                                      bases, draw['ptr6'], draw['ptr4'], draw['count'])
        need(len(candidates) == 1 and [list(c) for c in candidates] == draw['source_headers'],
             'wrong Header: retained pointers/count do not identify the declared source Header')
        car, index = candidates[0]
        data, headers, _ = cars[car]
        header = headers[index]
        for plane, pointer_name in [('six_byte', 'ptr6'), ('four_byte', 'ptr4'), ('third_four_byte', 'ptr2')]:
            span = header['planes'].get(plane)
            if span is not None:
                ptr = draw[pointer_name]
                need(ptr == bases[car] + span['offset'] and mem[ptr:ptr + span['size']] == data[span['offset']:span['end']],
                     'source Header plane bytes differ: ' + plane)
        p = draw['pass_id']
        need(header['flags'] & (0x10 if p == 4 else 8), 'Header pass eligibility flag missing')
        need(draw['effective_flags'] & (0x88 if p == 4 else 0x48) == (0x80 if p == 4 else 0x40),
             'effective pass eligibility mask differs')
        binding = bindings[transfer]
        need((binding['vertices'], binding['prim']) == (draw['count'], draw['prim']), 'GS draw descriptor differs')
        row = {'retained_index': i, 'transfer': transfer, 'pass_word': p, 'chain_address': draw['chain_addr'],
               'car': car, 'header_index': index, 'header_offset': header['offset'], 'header_flags': header['flags'],
               'header_raw_hex': data[header['offset']:header['offset'] + header['size']].hex(),
               'vertices': draw['count'], 'effective_flags': draw['effective_flags'],
               'source_planes': {name: {'offset': span['offset'], 'sha256': common.sha256(data[span['offset']:span['end']])}
                                 for name, span in header['planes'].items()}, 'gs_binding': binding}
        if p == 4:
            need(binding['TEX0_1'] == object_tex0, 'wrong texture: GS TEX0 differs from global pass4 texture object')
            row['sampled_texture'] = {'identity': 'view-render-target-0', 'car_texture_index': None, **texture}
        rows.append(row)
    need([sum(r['pass_word'] == p for r in rows) for p in (4, 5)] == [37, 63], 'pass counts differ')
    png, image = target_image(inputs['gs'], texture)
    libraries = {c: [{'index': t['index'], 'name': t['name'], 'width': t['width'], 'height': t['height']} for t in cars[c][2]] for c in bases}
    need(all((t['width'], t['height']) != (256, 128) for ts in libraries.values() for t in ts),
         'loaded car library contains sampled texture dimensions')
    return {'schema': 'fr2-pass-source-join/v1', 'scope': '100 retained/GSDump content-aligned draws; no same-frame execution proof.',
            'pins': inputs['pins'], 'source_functions': inputs['source_functions'], 'loaded_car_bases': {c: hex(b) for c, b in bases.items()},
            'by_pass_word': {str(p): {'draws': sum(r['pass_word'] == p for r in rows),
                                    'cars': sorted({r['car'] for r in rows if r['pass_word'] == p}),
                                    'header_indices': sorted({r['header_index'] for r in rows if r['pass_word'] == p})} for p in (4, 5)},
            'flag_rule': {'pass4': 'Header bit 0x10 maps to effective 0x80; (effective & 0x88)==0x80 and per-draw global enable required.',
                          'pass5': 'Header bit 0x08 maps to effective 0x40; (effective & 0x48)==0x40 and per-draw global enable required.',
                          'checked_target_draws': len(rows), 'sufficient_by_header_flags_alone': False},
            'pass4_texture': {'identity': 'view-render-target-0', 'classification': 'not a car texture', 'car_texture_index': None,
                              **texture, 'TEX0_1': object_tex0, 'global_address': 0x28f1b0, 'view_table_address': 0x2907b0,
                              'ee_object_address': pointer, 'object_64_bytes_sha256': common.sha256(mem[pointer:pointer + 64]),
                              'loaded_car_texture_libraries': libraries,
                              'preceding_render_target_draws': len(before), 'first_render_target_draw': before[0],
                              'last_render_target_draw_before_sampling': before[-1], 'first_sample_transfer': first_sample,
                              'export_origin': str(GS.relative_to(ROOT)), **image,
                              'decoder_reference': {
                                  'version': 'PCSX2 v2.8.2, GPL-3.0+',
                                  'freeze': 'https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSState.cpp',
                                  'swizzle': 'https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSTables.cpp',
                                  'rgb_expansion': 'https://github.com/PCSX2/pcsx2/blob/v2.8.2/pcsx2/GS/GSLocalMemory.h'}},
            'rows': rows, 'render_fidelity_complete': False,
            'claim_limits': ['Six models are loaded, but these 100 aligned optional-pass draws all join to COBRA. No coverage claim for other cars.',
                             'The Header rule is conditional on runtime enable/context; paused globals are not per-draw history.',
                             'The PNG exports capture-time race95 GS memory at the sampled address. It is not the post-render contents at race94 transfer 5456.',
                             'The dump renders to this address before sampling. This tool does not replay those draws or establish final sampled pixel values.',
                             'No new capture, shading implementation, full pass-4 UV/pass-5 S equivalence, or 158 unmatched-descriptor resolution.']}, png


def controls(inputs):
    def wrong_header(i):
        index = next(a for a, _ in i['align']['matched_pairs'] if i['align']['draws'][a].get('pass_id') == 4)
        i['align']['draws'][index]['source_headers'] = [['COBRA', 1]]

    def wrong_texture(i):
        target = next(t for a, t in i['align']['matched_pairs'] if i['align']['draws'][a].get('pass_id') == 4)
        bindings, _ = dump_bindings(i['transfers'], [target])
        write = bindings[target]['tex0_write']
        data = bytearray(i['transfers'][write['transfer']])
        struct.pack_into('<Q', data, write['payload_offset'], 0x5dc00a800)  # real pass-5 texture
        i['transfers'][write['transfer']] = bytes(data)

    result = common.run_controls(inputs, [('wrong Header', wrong_header), ('wrong texture', wrong_texture)],
                                 lambda i: derive(i)[0], JoinError)
    for control, intended in zip(result, ('wrong Header:', 'wrong texture:')):
        need(control['reason'].startswith(intended), 'control failed for an unrelated reason')
    return result


def main():
    if '--available' in sys.argv:
        export = static_inputs.configured('CARMODELS_TYPED_EXPORT')
        executable = static_inputs.configured('CARMODELS_EXECUTABLE')
        if not export or not executable:
            return 1
        paths = runtime_paths() + [Path(executable).expanduser(), Path(export).expanduser() / 'inventory.json']
        paths += [Path(export).expanduser() / 'decompilation/functions' / (entry + '.c') for entry in FUNCTION_PINS]
        return 0 if all(p.is_file() for p in paths) else 1
    inputs = load_inputs()
    receipt, png = derive(inputs)
    receipt['controls'] = controls(inputs)
    if '--write' in sys.argv:
        IMAGE.parent.mkdir(parents=True, exist_ok=True)
        IMAGE.write_bytes(png)
    else:
        need(IMAGE.is_file() and IMAGE.read_bytes() == png, 'exported texture PNG differs from retained GS image')
    return common.finish(receipt, OUT, sys.argv, ROOT, {'draws': len(receipt['rows']), 'controls': receipt['controls']})


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (JoinError, comparison.ComparisonError, FileNotFoundError) as error:
        sys.exit('VERIFY FAILED: ' + str(error))
