"""Source-bound MC3 VU input jobs for an independent PCSX2 interpreter.

No vertex, clipping or floating-point operation is approximated here. The job
retains the original microprogram and source VIF lanes; the pinned interpreter
executes them. Camera/object matrix words must come from the native EE helper
jobs, whose input and output bindings are recorded by the caller.
"""

import base64
import hashlib
import json
from pathlib import Path
import struct

from mc3_tire_vu import unpack_microprogram
from mc3_pck import vif_planes


EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/environment/geometry-native.json')
EXECUTABLE_SHA = '1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d'
PROOF_SHA = '501be5410c8590707c6276c86ae64313594eac51a11a55aafdf4a470958b8d7a'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def _read_elf(executable, start, length):
    need(executable[:7] == b'\x7fELF\x01\x01\x01', 'unsupported geometry executable')
    phoff = struct.unpack_from('<I', executable, 28)[0]
    width, count = struct.unpack_from('<HH', executable, 42)
    need(width >= 32 and phoff + width * count <= len(executable), 'invalid geometry ELF segments')
    matches = []
    for i in range(count):
        kind, offset, address, _, size = struct.unpack_from('<IIIII', executable, phoff + i * width)
        if kind == 1 and address <= start < start + length <= address + size:
            need(offset + size <= len(executable), 'truncated geometry ELF segment')
            matches.append(executable[offset + start - address:offset + start - address + length])
    need(len(matches) == 1, 'missing or ambiguous geometry source range')
    return matches[0]


def source_contract(executable=None, receipt=None):
    """Check bounded instruction pins, optionally against the private source ELF."""
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    encoded = json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()
    need(hashlib.sha256(encoded).hexdigest() == PROOF_SHA, 'geometry source receipt changed')
    need(proof['source_executable_sha256'] == EXECUTABLE_SHA, 'geometry executable identity mismatch')
    if executable is not None:
        need(hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
             'geometry executable identity mismatch')
        for pin in proof['source_intervals'].values():
            data = _read_elf(executable, pin['start'], pin['end'] - pin['start'])
            need(hashlib.sha256(data).hexdigest() == pin['sha256'], 'geometry source interval changed')
        pairs = unpack_microprogram(_read_elf(executable, 0x5E9610, 12000))
        for row in proof['selected_vu_instructions']:
            need(pairs[row['pc']] == (row['lower'], row['upper']), 'geometry VU instruction changed')
    return proof['contract']


class _PacketView:
    def __init__(self, data):
        self.data = data

    def bounds(self, offset, size=1):
        need(0 <= offset <= offset + size <= len(self.data), 'geometry VIF extent outside packet')
        return offset


def batch_patches(pack, native):
    """Rederive the supported original floor UNPACKs, including masked normal W."""
    data = source_packet(pack, native)
    planes = vif_planes(_PacketView(data), 0, len(data))
    indices = [i for i, plane in enumerate(planes) if plane['offset'] == native['batch_offset']]
    need(len(indices) == 1, 'native floor batch header missing')
    selected = planes[indices[0]:indices[0] + 4]
    need(len(selected) == 4, 'native floor batch incomplete')
    header, position, uv, normal = selected
    origin = header['address']
    need(origin in (0x9E, 0x1C5), 'unsupported native floor origin')
    expected = [(0x60, origin, 2, 1, 32), (0x69, origin + 98, 48, 3, 16),
                (0x6D, origin + 50, 48, 4, 16), (0x7A, origin + 2, 48, 3, 8)]
    for plane, layout in zip(selected, expected):
        actual = tuple(plane[key] for key in ('command', 'address', 'count', 'components', 'bits'))
        need(actual == layout and plane['cl'] == plane['wl'] == 1 and plane['mode'] == 0,
             'unsupported native floor UNPACK layout')
    need([x[0] for x in header['values']] == native['header_words'], 'native floor header lanes changed')
    for plane, key in [(position, 'position_integers'), (uv, 'uv_integers'), (normal, 'normal_integers')]:
        need([list(x) for x in plane['values']] == native[key], 'native floor source lanes changed')
    uv_end = uv['payload_offset'] + uv['count'] * 8
    mask_row = struct.pack('<7I', 0x20000000, 0x40404040, 0x30000000, 0, 0, 0, 0xFFFFFFFF)
    need(data[uv_end:normal['offset']] == mask_row, 'native floor normal W mask changed')
    need(struct.unpack_from('<II', data, normal['payload_offset'] + 48 * 3) ==
         (0x04000000 | origin, 0x14000006), 'native floor ITOP/MSCAL changed')
    patches = []
    for plane in selected:
        values = []
        for vector in plane['values']:
            if plane['components'] == 1:
                vector = vector * 4
            elif plane['components'] == 3:
                vector = (*vector, -1 if plane is normal else 0)
            values.extend(x & 0xFFFFFFFF for x in vector)
        patches.append((plane['address'] * 16, struct.pack('<' + 'I' * len(values), *values)))
    return origin, patches


def geometry_patches(pack, native):
    """Retain all source UNPACK planes for a world/sky visibility execution.

    XYZ-only position/normal loads ignore the unused fourth unpack lane. Masked
    world normals use the source reserved palette row. This is a geometry proof;
    hidden materials' shading is deliberately not inferred from this function.
    """
    data = source_packet(pack, native)
    planes = vif_planes(_PacketView(data), 0, len(data))
    starts = [i for i, p in enumerate(planes) if p['offset'] == native['batch_offset']]
    need(len(starts) == 1, 'native geometry batch header missing')
    start = starts[0]
    header = planes[start]
    need(header['components'] == 1 and header['count'] == 2, 'unsupported native geometry header')
    origin = header['address']
    need(origin in (0x98, 0x9E, 0x1C5), 'unsupported native geometry origin')
    end = next((i for i in range(start + 1, len(planes)) if
                planes[i]['components'] == 1 and planes[i]['count'] == 2 and
                planes[i]['address'] in (0x98, 0x9E, 0x1C5)), len(planes))
    selected, patches = planes[start:end], []
    need([v[0] for v in header['values']] == native['header_words'], 'native geometry header changed')
    world = native['world_layout']
    expected = {'position_integers': origin + (98 if world else 86),
                'uv_integers': origin + (50 if world else 44),
                'normal_integers': origin + 2}
    if not world:
        expected['color_integers'] = origin + 128
    for key, address in expected.items():
        expanded = {}
        for plane in selected:
            for i, vector in enumerate(plane['values']):
                if address <= plane['address'] + i < address + len(native[key]):
                    need(plane['address'] + i not in expanded, 'overlapping native source lanes')
                    expanded[plane['address'] + i] = [
                        v - 0x100000000 if plane['bits'] == 32 and v >= 0x80000000 else v
                        for v in vector]
        need([expanded.get(address + i) for i in range(len(native[key]))] == native[key],
             'native geometry source lanes changed: ' + key)
    for plane in selected:
        need(plane['cl'] <= plane['wl'], 'unsupported native VIF destination skip')
        values = []
        for i, vector in enumerate(plane['values']):
            if len(vector) == 1:
                vector = vector * 4
            elif len(vector) == 2:
                vector = vector * 2
            elif len(vector) == 3:
                following = plane['values'][i + 1][0] if i + 1 < len(plane['values']) else 0
                vector = (*vector, -1 if plane['command'] & 0x10 else following)
            values.extend(v & 0xFFFFFFFF for v in vector)
        patches.append((plane['address'] * 16, struct.pack('<' + 'I' * len(values), *values)))
    return origin, patches


def floor_job(pack, executable, *, clip_matrix_words, object_matrix_words, pass_index, cull_selector=2):
    """Make a source floor job; supplied matrix words require separate EE execution verification.

    The caller binds both the EE jobs/outputs and this job to the original input
    digest. This API deliberately accepts raw words, never host matrices which
    would silently add a second floating-point implementation.
    """
    source_contract(executable)
    need(pass_index in (0, 1), 'unsupported native floor pass')
    need(cull_selector in (0, 2) and (pass_index == 0 or cull_selector == 2),
         'unsupported native floor cull context')
    clip = _words(clip_matrix_words, 16, 'clip matrix')
    model = _words(object_matrix_words, 16, 'object matrix')
    pairs = unpack_microprogram(_read_elf(executable, 0x5E9610, 12000))
    microprogram = bytearray(16384)
    for pc, pair in pairs.items():
        struct.pack_into('<II', microprogram, pc * 8, *pair)
    memory = bytearray(16384)
    memory[4 * 16:8 * 16] = clip
    memory[12 * 16:16 * 16] = model
    # Original source constant data, not a reconstructed GIF packet.
    memory[35 * 16:40 * 16] = _read_elf(executable, 0x613F1C, 80)
    memory[44 * 16:48 * 16] = _read_elf(executable, 0x613F70, 64)
    struct.pack_into('<8f', memory, 8 * 16, 512, -512, -32767.5 / 16, 0,
                     1856, 1952, 32767.5 / 16, 1)
    struct.pack_into('<16f', memory, 16 * 16, 1, 0, 0, 0, 0, 1, 0, 0,
                     0, 0, 1, 0, 0, 0, 0, 1)
    cull = (0, 0x80, 0xC0)[cull_selector]
    struct.pack_into('<4I', memory, 34 * 16, cull | pass_index, 0x30024004, 0, 0)
    struct.pack_into('<4f', memory, 42 * 16, 128, 128, 128, 128)
    # This source palette entry is independently pinned by native-scene.json.
    memory[895 * 16:896 * 16] = bytes.fromhex('9196163f8b8b0b3f8482023f0000803f')
    struct.pack_into('<4I', memory, 45 * 16, 0x58, 0, 0x1B, 0)
    struct.pack_into('<4I', memory, 47 * 16, 0x258, 0, 0x1B, 0)
    calls = [{'pc': 10, 'top': 0, 'itop': 0}]
    rows = []
    for draw in pack['draws']:
        if draw['material_index'] != 8:
            continue
        native = draw['native']
        origin, patches = batch_patches(pack, native)
        calls.append({'pc': 6, 'top': 0, 'itop': origin, 'patches': patches})
        rows.append({'material_index': 8, 'pass_index': pass_index,
                     'source_packet_sha256': pack['native_packets'][native['packet']]['sha256'],
                     'batch_offset': native['batch_offset']})
    need(len(rows) == 4, 'native floor batch coverage changed')
    result = encode_job(microprogram, memory, calls)
    return result, {'schema': 1, 'job_sha256': hashlib.sha256(result).hexdigest(),
                    'matrix_words_sha256': hashlib.sha256(clip + model).hexdigest(),
                    'initial_memory_sha256': hashlib.sha256(memory).hexdigest(), 'batches': rows}


def visibility_job(pack, executable, city, *, clip_matrix_words, rotation_words, cull_flags):
    """Execute every nonfloor world batch as a conservative visibility proof.

    Both cull0 and cull2 controls must yield zero scissored fragments. The result
    proves absence of hidden material contributions, not their color equations.
    """
    need(cull_flags in (0, 0xC0), 'unsupported geometry visibility cull control')
    rotation = _words(rotation_words, 9, 'rotation')
    identity_model = [0x3F800000, 0, 0, 0, 0, 0x3F800000, 0, 0,
                      0, 0, 0x3F800000, 0, 0, 0, 0, 0x3F800000]
    seed, _ = floor_job(pack, executable, clip_matrix_words=clip_matrix_words,
                        object_matrix_words=identity_model, pass_index=0)
    micro, memory = seed[8:8 + 16384], bytearray(seed[8 + 16384:8 + 32768])
    need(hashlib.sha256(city).hexdigest() == pack['source']['city']['sha256'],
         'native visibility city source changed')
    need(len(city) >= 784 + 4096, 'native visibility palette truncated')
    memory[768 * 16:1024 * 16] = city[784:784 + 4096]
    struct.pack_into('<I', memory, 34 * 16, cull_flags)
    calls, rows = [], []
    for index, draw in enumerate(pack['draws']):
        if draw['material_index'] == 8:
            continue
        native = draw['native']
        need(native['world_layout'], 'unsupported native world visibility layout')
        origin, patches = geometry_patches(pack, native)
        model = bytearray()
        for i in range(3):
            model += rotation[i * 12:i * 12 + 12] + bytes(4)
        model += struct.pack('<3fI', *native['instance_translation'], 0x3F800000)
        calls.append({'pc': 10, 'top': 0, 'itop': origin, 'patches': [(12 * 16, bytes(model))]})
        calls.append({'pc': 6, 'top': 0, 'itop': origin, 'patches': patches})
        rows.append({'draw_index': index, 'material_index': draw['material_index'],
                     'source_packet_sha256': pack['native_packets'][native['packet']]['sha256'],
                     'batch_offset': native['batch_offset'], 'call_index': len(calls) - 1})
    need(len(rows) == 412, 'native world visibility coverage changed')
    job = encode_job(micro, memory, calls)
    return job, {'schema': 1, 'job_sha256': hashlib.sha256(job).hexdigest(),
                 'cull_flags': cull_flags, 'records': rows,
                 'claim_limit': 'Conservative source geometry visibility; hidden shading is not asserted.'}


def sky_job(pack, executable, *, clip_matrix_words):
    """Retain the original sky program, source vertex colors and inverted Y pose."""
    model = list(struct.unpack('<16I', struct.pack('<16f', 1, 0, 0, 0, 0, -1, 0, 0,
                                                  0, 0, 1, 0, *pack['camera']['eye'], 1)))
    seed, _ = floor_job(pack, executable, clip_matrix_words=clip_matrix_words,
                        object_matrix_words=model, pass_index=0)
    memory = bytearray(seed[8 + 16384:8 + 32768])
    pairs = unpack_microprogram(_read_elf(executable, 0x5EC4F0, 13488))
    micro = bytearray(16384)
    for pc, pair in pairs.items():
        struct.pack_into('<II', micro, pc * 8, *pair)
    struct.pack_into('<I', memory, 34 * 16, 0x80)
    calls, rows = [{'pc': 10, 'top': 0, 'itop': 0}], []
    for draw in pack['sky']['draws']:
        native = draw['native']
        need(not native['world_layout'], 'unsupported native sky geometry layout')
        origin, patches = geometry_patches(pack, native)
        calls.append({'pc': 6, 'top': 0, 'itop': origin, 'patches': patches})
        rows.append({'image': draw['image'], 'material_index': -1, 'pass_index': 0,
                     'source_packet_sha256': pack['native_packets'][native['packet']]['sha256'],
                     'batch_offset': native['batch_offset']})
    need(len(rows) == 5, 'native sky batch coverage changed')
    job = encode_job(micro, memory, calls)
    return job, {'schema': 1, 'job_sha256': hashlib.sha256(job).hexdigest(), 'batches': rows}


def encode_ee_job(entry, gprs, patches, fprs=None):
    """Describe a native helper call without translating its scalar/COP2 math."""
    fprs = {} if fprs is None else fprs
    result = bytearray(b'MC3EE001') + struct.pack('<5I', entry, 100000, len(gprs), len(fprs), len(patches))
    for reg, value in gprs.items():
        need(1 <= reg < 32 and 0 <= value <= 0xFFFFFFFF, 'invalid native EE GPR')
        result += struct.pack('<I4I', reg, value, 0, 0, 0)
    for reg, word in fprs.items():
        need(0 <= reg < 32 and 0 <= word <= 0xFFFFFFFF, 'invalid native EE FPR')
        result += struct.pack('<II', reg, word)
    for address, data in patches:
        need(0 <= address < address + len(data) <= 32 * 1024 * 1024, 'native EE patch outside RAM')
        result += struct.pack('<II', address, len(data)) + data
    return bytes(result)


def regenerate(pack, executable, city, output, runner=None):
    """Rerun original EE helpers and VU programs in the independent runtime.

    Returns literal visible GIF records plus conservative hidden-geometry
    executions. The caller must independently rasterize both visibility controls
    and compare the complete final GS image before accepting the regenerated data.
    """
    from mc3_environment import capture_input_sha256
    if runner is None:
        from mc3_reference_runtime import run_job
        runner = run_job
    output = Path(output)
    need(not output.exists() or not any(output.iterdir()), 'geometry regeneration output must be empty')
    output.mkdir(parents=True, exist_ok=True)
    executable = Path(executable)
    original = executable.read_bytes()
    source_contract(original)
    need(all(pack['camera'][key] == value for key, value in {
        'fov': 100, 'near': .25, 'far': 1000, 'right': [1, 0, 0],
        'up': [0, 0, -1], 'backward': [0, 1, 0]}.items()), 'unsupported native capture camera profile')
    need(pack['sky']['native_initial_state'] == {
        'rotation_degrees': 0, 'translation_offset': [0, 0, 0], 'invert_y': True},
        'unsupported native sky initial profile')
    executions = []

    def execute(name, job, mode):
        path = output / (name + '.job')
        path.write_bytes(job)
        receipt = runner(path, output / name, mode=mode, executable=executable if mode == 'ee' else None)
        executions.append({'name': name, 'receipt': receipt})
        return output / name

    def ee(name, entry, gprs, patches, fprs=None):
        path = execute(name, encode_ee_job(entry, gprs, patches, fprs), 'ee')
        return (path / 'ee-ram.bin').read_bytes()

    buffer, argument = 0x1000000, 0x1000100
    # Native camera look direction is target−eye=(0,−1,0). Execute the exact
    # vertical fallback, then apply the six NEG.S stores in5626cc..56270c.
    basis = ee('camera-basis', 0x241128, {4: buffer, 5: argument},
               [(argument, struct.pack('<3f', 0, -1, 0))])
    basis_words = list(struct.unpack_from('<9I', basis, buffer))
    basis_words[:6] = [word ^ 0x80000000 for word in basis_words[:6]]
    pose = []
    for i in range(3):
        pose.extend(basis_words[i * 3:i * 3 + 3])
        pose.append(0)
    pose.extend(struct.unpack('<3I', struct.pack('<3f', *pack['camera']['eye'])))
    pose.append(0x3F800000)
    view = ee('camera-inverse', 0x2434F0, {4: buffer, 5: argument},
              [(argument, _words(pose, 16, 'camera pose'))])[buffer:buffer + 64]
    projection = ee('projection', 0x5311F8, {4: buffer}, [],
                    {12: 0x42C80000, 13: 0x3F800000, 14: 0x3E800000, 15: 0x447A0000})
    projection = projection[buffer + 16:buffer + 80]
    rotations = []
    floor_native = next(d['native'] for d in pack['draws'] if d['material_index'] == 8)
    angles = struct.pack('<3f', *floor_native['instance_euler'])
    need(all(struct.pack('<3f', *d['native']['instance_euler']) == angles for d in pack['draws']),
         'native source instance rotations no longer share one profile')
    for backend in (0, 1):
        native = ee('euler-' + str(backend), 0x240090, {4: buffer, 5: argument},
                    [(argument, angles), (0x61C4C2, bytes([backend]))])
        rotations.append(native[buffer:buffer + 36])
    need(rotations[0] == rotations[1], 'native Euler helper backend outputs differ')
    rotation_words = list(struct.unpack('<9I', rotations[0]))
    clips = []
    scaling = struct.pack('<16f', .25, 0, 0, 0, 0, .25, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    for name, multiply, scale in [('cop1', 0x243040, 0x242BD0), ('cop2', 0x243448, 0x242B58)]:
        vp = ee('vp-' + name, multiply, {4: buffer, 5: argument, 6: argument + 256},
                [(argument, projection), (argument + 256, view)])[buffer:buffer + 64]
        clip = ee('clip-' + name, scale, {4: buffer, 5: argument},
                  [(buffer, vp), (argument, scaling)])[buffer:buffer + 64]
        clips.append(clip)
    need(clips[0] == clips[1], 'native capture matrix backend outputs differ')
    clip_words = list(struct.unpack('<16I', clips[0]))
    object_words = []
    for i in range(3):
        object_words.extend(rotation_words[i * 3:i * 3 + 3])
        object_words.append(0)
    object_words.extend(struct.unpack('<3I', struct.pack('<3f', *floor_native['instance_translation'])))
    object_words.append(0x3F800000)

    def vu(name, job, manifest):
        path = execute(name, job, 'vu')
        chunks = decode_transport((path / 'gif-chunks.bin').read_bytes())
        calls = json.loads((path / 'calls.json').read_text())
        rows = manifest.get('batches', manifest.get('records'))
        result = []
        for i, row in enumerate(rows):
            call = calls[row.get('call_index', i + 1)]
            need(call['pc'] == 6 and 0 <= call['start_chunk'] <= call['end_chunk'] <= len(chunks),
                 'native VU output call boundary changed')
            result.append({**row, 'gif_chunks': [base64.b64encode(chunk).decode() for chunk in
                           chunks[call['start_chunk']:call['end_chunk']]]})
        return result

    passes = []
    for index in (0, 1):
        job, manifest = floor_job(pack, original, clip_matrix_words=clip_words,
                                  object_matrix_words=object_words, pass_index=index)
        passes.extend(vu('floor-' + str(index), job, manifest))
    job, manifest = floor_job(pack, original, clip_matrix_words=clip_words,
                              object_matrix_words=object_words, pass_index=0, cull_selector=0)
    base_cull_control = vu('floor-base-cull0', job, manifest)
    job, manifest = sky_job(pack, original, clip_matrix_words=clip_words)
    passes.extend(vu('sky', job, manifest))
    visibility = {}
    for flag in (0, 0xC0):
        job, manifest = visibility_job(pack, original, city, clip_matrix_words=clip_words,
                                       rotation_words=rotation_words, cull_flags=flag)
        visibility[str(flag)] = vu('visibility-' + str(flag), job, manifest)
    result = {'schema': 1, 'capture_input_sha256': capture_input_sha256(pack),
              'native_gs': {'schema': 1, 'context': {'xy_offset': [27648, 29184],
                            'scissor': [0, 0, 256, 256], 'depth_format': 'PSMZ16S'}, 'passes': passes},
              'visibility_controls': visibility, 'executions': executions,
              'base_cull0_control': base_cull_control,
              'matrices': {'clip_words': clip_words, 'rotation_words': rotation_words,
                           'camera_basis_words': basis_words}}
    (output / 'regenerated.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def _words(words, count, label):
    need(isinstance(words, list) and len(words) == count and
         all(type(x) is int and 0 <= x <= 0xFFFFFFFF for x in words),
         'invalid native ' + label + ' words')
    return struct.pack('<' + 'I' * count, *words)


def encode_job(microprogram, initial_memory, calls):
    """Serialize the explicit ABI consumed by the official interpreter adapter."""
    need(len(microprogram) == len(initial_memory) == 16384, 'invalid native VU memory size')
    need(0 < len(calls) <= 2048, 'invalid native VU call count')
    result = bytearray(b'MC3VU001') + microprogram + initial_memory
    result += struct.pack('<I', len(calls))
    for call in calls:
        pc, top, itop = call['pc'], call['top'], call['itop']
        need(all(type(x) is int for x in (pc, top, itop)) and
             0 <= pc < 2048 and 0 <= top < 1024 and 0 <= itop < 1024,
             'invalid native VU call address')
        patches = call.get('patches', [])
        result += struct.pack('<6I', pc, top, itop, 100000, len(patches), 0)
        for offset, data in patches:
            need(type(offset) is int and 0 <= offset < offset + len(data) <= 16384,
                 'native VU patch outside memory')
            result += struct.pack('<II', offset, len(data)) + data
    return bytes(result)


def source_packet(pack, native):
    """Reject stale or altered source packets before retaining unpacked lanes."""
    key = native['packet']
    need(key in pack['native_packets'], 'native geometry packet missing')
    record = pack['native_packets'][key]
    try:
        data = base64.b64decode(record['data_base64'], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError('invalid native geometry packet encoding') from exc
    need(len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'],
         'native geometry packet identity mismatch')
    need(0 <= native['batch_offset'] < len(data), 'native geometry batch outside packet')
    return data


def decode_transport(data):
    """Retain literal GIF transport chunks; topology/XYZF2 decoding belongs to GS."""
    cursor, chunks = 0, []
    while cursor < len(data):
        need(cursor + 4 <= len(data), 'truncated native GIF chunk header')
        size = struct.unpack_from('<I', data, cursor)[0]
        cursor += 4
        need(size > 0 and size % 16 == 0 and cursor + size <= len(data),
             'invalid native GIF transport extent')
        chunks.append(data[cursor:cursor + size])
        cursor += size
    need(chunks, 'empty native GIF transport')
    return chunks
