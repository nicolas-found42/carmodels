"""Original MC3 unskinned model dispatch with an explicit observer material.

The observer replaces material draw callbacks, not original model selection.
It certifies mask/LOD/bucket/frame dispatch; it does not execute a material or
choose an original actor's stock customization state.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf, encode_ee_job
from mc3_pck import Pck, read_vehicle
from mc3_specular_native import EXECUTABLE_SHA
from mc3_vehicle_inputs import native_material_inputs

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'research/evidence/midnight-club-3-remix/previews/vehicle-dispatch.json'
PROOF_SHA = '3342161aef37554972bb3036765574792dd4eb63e3b1db3e069d03440313b838'
CODE, OBSERVER, VTABLE, PARAMS, MASK, PALETTE, RESULT, SOURCE = (
    0x1000000, 0x1001000, 0x1002000, 0x1003000, 0x1004000,
    0x1130000, 0x1180000, 0x1400000)
DMA, DMA_END, STRIDE, LIMIT = 0x1100000, 0x1110000, 80, 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    need(sha(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()) == PROOF_SHA,
         'vehicle dispatcher receipt differs')
    return proof


def from_executable(executable):
    need(sha(executable) == EXECUTABLE_SHA, 'vehicle dispatcher executable differs')
    proof = source_contract()
    for row in proof['intervals']:
        need(sha(_read_elf(executable, row['start'], row['end']-row['start'])) == row['sha256'],
             'vehicle dispatcher source interval differs')
    return proof


def _li(words, register, value):
    words.extend([0x3c000000 | register << 16 | value >> 16,
                  0x34000000 | register << 21 | register << 16 | value & 65535])


def observer():
    """Self-authored callback: record five args and the original SPAD frame."""
    words = []
    _li(words, 9, RESULT)
    words += [0x8d2a0000, 0x000a5980, 0x000a6100, 0x016c5821,
              0x01695821, 0x256b0010]
    for register, offset in [(4, 0), (5, 4), (6, 8), (7, 12), (8, 16)]:
        words.append(0xac000000 | 11 << 21 | register << 16 | offset)
    _li(words, 12, 0x70000000)
    for i in range(12):
        words += [0x8d8d0000 | i*4, 0xad6d0000 | (20+i*4)]
    words += [0x254a0001, 0xad2a0000, 0x03e00008, 0]
    return struct.pack('<'+'I'*len(words), *words)


def native_context(path, *, lod, bucket, mask_words, palette_words):
    """Prepare exact source groups plus controlled callback instrumentation.

    None disables the optional bone mask, matching the original null argument.
    Non-null masks and frame words are explicit caller inputs, never defaults.
    External source meshes that are null in this PCK remain null.
    """
    need(type(lod) is int and 0 <= lod <= 2 and type(bucket) is int and 0 <= bucket < 32,
         'vehicle dispatcher LOD or bucket differs')
    raw = Path(path).read_bytes()
    pck, vehicle = Pck(raw), read_vehicle(path)
    count = len(vehicle['skeleton']['bones'])
    need(count <= 256 and SOURCE+len(raw) <= 0x1fe0000, 'vehicle dispatcher source bound exceeded')
    need(type(palette_words) is list and len(palette_words) == count*12
         and all(type(v) is int and 0 <= v <= 0xffffffff for v in palette_words),
         'vehicle dispatcher explicit frame palette differs')
    need(mask_words is None or (type(mask_words) is list and len(mask_words) == (count+31)//32
         and all(type(v) is int and 0 <= v <= 0xffffffff for v in mask_words)),
         'vehicle dispatcher explicit mask differs')
    data = bytearray(raw)

    def write(offset, value):
        struct.pack_into('<I', data, offset, value)

    root, collection = vehicle['model_offset'], vehicle['material_collection_offset']
    need(raw[root+4] == 1, 'vehicle dispatcher requires one source material set')
    write(root+8, SOURCE+collection)
    array = pck.pointer(pck.u32(collection+4), len(vehicle['materials'])*4)
    write(collection+4, SOURCE+array)
    for material in vehicle['materials']:
        offset = material['offset']
        write(array+material['index']*4, SOURCE+offset)
        write(offset, VTABLE)  # Only the callback table is instrumentation.
    joins = []
    for index, name in enumerate(('high', 'middle', 'low')):
        need(any(part['mesh'] is not None for part in vehicle['lods'][name]),
             'vehicle dispatcher empty-group fallback is outside this control profile')
        group = pck.pointer(pck.u32(root+16+index*4), 20)
        write(root+16+index*4, SOURCE+group)
        write(group+4, 0x626d08)
        meshes = pck.pointer(pck.u32(group+8), len(vehicle['lods'][name])*4)
        write(group+8, SOURCE+meshes)
        for part_index, part in enumerate(vehicle['lods'][name]):
            mesh = part['mesh']
            if mesh is None:
                continue
            offset = mesh['offset']
            need(raw[offset+4] == 0 and raw[offset+6] == part['bone'],
                 'vehicle dispatcher unskinned source bone differs')
            write(meshes+part_index*4, SOURCE+offset)
            write(offset+12, SOURCE+pck.pointer(pck.u32(offset+12), len(mesh['draws'])*2))
            joins.append({'lod': name, 'mesh_offset': offset, 'bone': part['bone'],
                          'materials': [draw['material'] for draw in mesh['draws']]})
    need(sum(len(row['materials']) for row in joins) <= LIMIT,
         'vehicle dispatcher observer allocation bound exceeded')
    inputs = native_material_inputs(raw, collection)
    params = struct.pack('<'+'I'*len(inputs), *(row['word'] for row in inputs))
    words = [0x03e0b82d]
    _li(words, 8, 0x70000000)
    _li(words, 9, DMA)
    words.append(0xad0905ac)
    _li(words, 9, DMA_END)
    words.append(0xad0905b0)
    for register, value in [(4, SOURCE+root), (5, PARAMS), (6, PALETTE),
                            (7, bucket), (8, lod), (9, MASK if mask_words is not None else 0), (10, 0)]:
        _li(words, register, value)
    words += [0x0c000000 | 0x2a6448 >> 2, 0]
    _li(words, 8, 0x70000000)
    words.append(0x8d0905ac)
    _li(words, 8, RESULT)
    words += [0xad090004, 0x02e00008, 0]
    table = bytearray(0x34)
    struct.pack_into('<I', table, 0x28, OBSERVER)
    mask = (struct.pack('<I', MASK+16)+bytes(12)+struct.pack('<'+'I'*len(mask_words), *mask_words)
            if mask_words is not None else bytes(16))
    patches = [(CODE, struct.pack('<'+'I'*len(words), *words)), (OBSERVER, observer()),
               (VTABLE, table), (SOURCE, data), (PARAMS, params), (MASK, mask),
               (PALETTE, struct.pack('<'+'I'*len(palette_words), *palette_words)),
               (RESULT, bytes(16+LIMIT*STRIDE)), (0x70fa40, bytes(4)), (0x615d80, bytes(4))]
    binding = {'source_sha256': pck.sha256, 'source_bytes': len(raw), 'model_offset': root,
               'source_mesh_joins': joins, 'source_material_offsets': [m['offset'] for m in vehicle['materials']],
               'source_material_flags': [pck.u32(m['offset']+4) for m in vehicle['materials']],
               'parameter_words': [row['word'] for row in inputs], 'lod': lod, 'bucket': bucket,
               'mask_words': mask_words, 'palette_words': palette_words}
    return patches, binding


def reference_job(executable, path, **context):
    from_executable(executable)
    patches, binding = native_context(path, **context)
    return encode_ee_job(CODE, {}, patches), binding


def browser_source_pack(executable, path, **context):
    """Private source transport for separately reviewed bounded EE execution."""
    proof = from_executable(executable)
    patches, binding = native_context(path, **context)
    offset = struct.unpack_from('<I', executable, 28)[0]
    width, count = struct.unpack_from('<HH', executable, 42)
    chunks, regions, code = [], [], []
    for i in range(count):
        kind, source, address, _, filesz, memsz, flags, _ = struct.unpack_from('<8I', executable, offset+i*width)
        if kind == 1:
            need(filesz <= memsz and source+filesz <= len(executable) and address+memsz <= 0x2000000,
                 'vehicle dispatcher segment extent differs')
            chunks.append({'address': address, 'data_hex': executable[source:source+filesz].hex()})
            regions.append({'start': address, 'size': memsz, 'read': True, 'write': bool(flags & 2)})
    for address, data in patches:
        chunks.append({'address': address, 'data_hex': data.hex()})
        if not any(r['start'] <= address and address+len(data) <= r['start']+r['size'] for r in regions):
            regions.append({'start': address, 'size': len(data), 'read': True, 'write': True})
    regions += [{'start': 0x70000000, 'size': 0x4000, 'read': True, 'write': True},
                {'start': DMA, 'size': DMA_END-DMA, 'read': True, 'write': True},
                {'start': 0x1fe0000, 'size': 0x20000, 'read': True, 'write': True}]
    for row in proof['intervals']:
        data = _read_elf(executable, row['start'], row['end']-row['start'])
        code.extend([row['start']+i, struct.unpack_from('<I', data, i)[0]] for i in range(0, len(data), 4))
    for address, data in patches[:2]:
        code.extend([address+i, struct.unpack_from('<I', data, i)[0]] for i in range(0, len(data), 4))
    return {'entry': CODE, 'chunks': chunks, 'regions': regions, 'code': code,
            'source_binding': binding, 'claim_limits': proof['claim_limits']}


def output(ram):
    need(len(ram) == 0x2000000, 'vehicle dispatcher output extent differs')
    count, end = struct.unpack_from('<2I', ram, RESULT)
    need(count <= LIMIT and DMA <= end <= DMA_END, 'vehicle dispatcher output bounds differ')
    rows = []
    for i in range(count):
        row = struct.unpack_from('<17I', ram, RESULT+16+i*STRIDE)
        need(row[0] >= SOURCE and row[1] >= SOURCE and row[2] == PARAMS,
             'vehicle dispatcher observer pointer differs')
        rows.append({'material_offset': row[0]-SOURCE, 'mesh_offset': row[1]-SOURCE,
                     'draw_index': row[3], 'lod': row[4], 'frame_words': list(row[5:])})
    return {'ram_sha256': sha(ram), 'records': rows, 'dma_sha256': sha(ram[DMA:end]), 'dma_bytes': end-DMA}


def expected_records(binding):
    """Independent scalar selection model for the explicit observer controls."""
    rows = []
    lod = ('high', 'middle', 'low')[binding['lod']]
    for mesh in binding['source_mesh_joins']:
        bone = mesh['bone']
        mask = binding['mask_words']
        if mesh['lod'] != lod or (mask is not None and not mask[bone//32] & (1 << (bone & 31))):
            continue
        for index, material in enumerate(mesh['materials']):
            if binding['source_material_flags'][material] >> 7 & 31 == binding['bucket']:
                rows.append({'material_offset': binding['source_material_offsets'][material],
                             'mesh_offset': mesh['mesh_offset'], 'draw_index': index,
                             'lod': binding['lod'],
                             'frame_words': binding['palette_words'][bone*12:bone*12+12]})
    return rows


def control_palette(count):
    """Explicit test frames: identity basis and x=bone index, never actor state."""
    words = []
    for i in range(count):
        words.extend(struct.unpack('<12I', struct.pack('<12f', 1, 0, 0, 0, 1, 0, 0, 0, 1, i, 0, 0)))
    return words


def compact_output(actual):
    return {name: value for name, value in actual.items() if name != 'records'} | {
        'record_count': len(actual['records']),
        'records_sha256': sha(json.dumps(actual['records'], sort_keys=True, separators=(',', ':')).encode())}


def execute_reference(executable, source_paths, directory, runner=None):
    from mc3_reference_runtime import run_job
    runner = runner or run_job
    executable, directory = Path(executable), Path(directory)
    proof = from_executable(executable.read_bytes())
    need(not directory.exists(), 'vehicle dispatcher reference directory exists')
    directory.mkdir(parents=True)
    results = []
    for case in proof['cases']:
        source = proof['sources'][case['source']]
        count = source['joint_count']
        context = {key: case[key] for key in ('lod', 'bucket', 'mask_words')}
        context['palette_words'] = control_palette(count)
        job, binding = reference_job(executable.read_bytes(), source_paths[case['source']], **context)
        need(binding['source_sha256'] == source['source_sha256'] and sha(job) == case['job_sha256'],
             'vehicle dispatcher original input differs')
        path = directory/(case['name']+'.job')
        path.write_bytes(job)
        execution = runner(path, directory/case['name'], mode='ee', executable=executable)
        actual = output((directory/case['name']/'ee-ram.bin').read_bytes())
        need(actual['records'] == expected_records(binding), 'original dispatcher selection differs')
        need(compact_output(actual) == case['expected'], 'original dispatcher output differs')
        results.append({'name': case['name'], 'execution': execution, 'output': compact_output(actual)})
    (directory/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    return results
