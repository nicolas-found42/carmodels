"""Original MC3 camera/frame/light uploader with explicit caller-owned state.

This producer supplies original instructions to the selected EE reference. It
does not derive a camera matrix, normalize a light, or substitute Three state.
The bounded contexts are numerical controls, not snapshots of a running actor.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf, encode_ee_job
from mc3_specular_native import EXECUTABLE_SHA

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'research/evidence/midnight-club-3-remix/previews/vehicle-uniforms.json'
PROOF_SHA = '9e6c29e892567a0263cb1fef99d288a09ec48ec2d5c1010d4f01f85ddbe70733'
CODE, LIGHT, FRAME, CONFIG, CAMERA, RESULT = (0x1000000+i*0x1000 for i in range(6))
DMA, DMA_END = 0x1100000, 0x1110000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    canonical = json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()
    need(sha(canonical) == PROOF_SHA, 'vehicle uniform receipt differs')
    return proof


def from_executable(executable):
    need(sha(executable) == EXECUTABLE_SHA, 'vehicle uniform executable differs')
    proof = source_contract()
    for row in proof['intervals']:
        need(sha(_read_elf(executable, row['start'], row['end']-row['start'])) == row['sha256'],
             'vehicle uniform source interval differs')
    return proof


def _words(values, count):
    need(isinstance(values, list) and len(values) == count
         and all(type(v) is int and 0 <= v <= 0xffffffff for v in values),
         'vehicle uniform raw words differ')
    return struct.pack('<'+'I'*count, *values)


def caller(context):
    """Self-authored isolated caller; all arithmetic/upload routines unchanged."""
    need(context['backend'] in (0, 1), 'vehicle uniform backend differs')
    need(set(context) == {'backend', 'projection_words', 'pose_words', 'frame_words',
                         'light_words', 'display_words', 'clip_scale_word'},
         'vehicle uniform explicit context fields differ')
    projection = _words(context['projection_words'], 4)
    pose = _words(context['pose_words'], 16)
    frame = _words(context['frame_words'], 12)
    lights = _words(context['light_words'], 34)
    for values in (projection, pose, frame, lights):
        need(all(math.isfinite(v) for v in struct.unpack('<'+'f'*(len(values)//4), values)),
             'vehicle uniform nonfinite input differs')
    fov, aspect, near, far = struct.unpack('<4f', projection)
    need(0 < fov < 180 and aspect > 0 and 0 < near < far,
         'vehicle uniform projection input differs')
    need([context['pose_words'][i] for i in (3, 7, 11, 15)] == [0, 0, 0, 0x3f800000],
         'vehicle uniform affine pose differs')
    display = context['display_words']
    # Explicit supported display profile. Arbitrary camera/display production
    # state requires additional original executions before extending this API.
    need(display == [256, 256, 1792, 1792, 0x477fff00, 0, 0, 0],
         'vehicle uniform display profile differs')
    need(context['clip_scale_word'] == 0x3f800000, 'vehicle uniform clip scale differs')
    camera = bytearray(0x1b0)
    camera[0x90:0xd0] = pose
    struct.pack_into('<2I', camera, 0x194, 0x3f800000, context['clip_scale_word'])
    words = [0x03e0b82d]  # Preserve isolated caller return in s7.

    def li(reg, value):
        words.extend([0x3c000000 | reg << 16 | value >> 16,
                      0x34000000 | reg << 21 | reg << 16 | value & 65535])

    def call(entry):
        words.extend([0x0c000000 | entry >> 2, 0])

    li(8, 0x70000000)
    li(9, DMA)
    words.append(0xad0905ac)
    li(9, DMA_END)
    words.append(0xad0905b0)
    li(4, CAMERA)
    li(9, CONFIG)
    for i in range(4):
        words.append(0xc4000000 | 9 << 21 | (12+i) << 16 | i*4)
    call(0x5311f8)
    li(4, CAMERA)
    for reg, value in [(5, 0), (6, 0), (7, 256), (8, 256)]:
        li(reg, value)
    li(9, CONFIG)
    for i in range(2):
        words.append(0xc4000000 | 9 << 21 | (12+i) << 16 | 16+i*4)
    call(0x530f38)
    li(4, CAMERA)
    call(0x527b98)
    for entry, argument in [(0x2ae348, LIGHT), (0x2adb48, FRAME), (0x2adc78, 0x70000000)]:
        li(4, argument)
        call(entry)
    # Export actual native DMA end from SPAD through an inert transport store.
    li(8, 0x70000000)
    words.append(0x8d0905ac)
    li(8, RESULT)
    words.extend([0xad090000, 0x02e00008, 0])
    return [(CODE, struct.pack('<'+'I'*len(words), *words)), (LIGHT, lights),
            (FRAME, frame), (CONFIG, projection+struct.pack('<2I', 0, 0x3f800000)),
            (CAMERA, camera), (RESULT, bytes(4)), (0x70e50c, bytes(4)),
            (0x70e510, struct.pack('<2I', *display[:2])),
            (0x70e5b8, struct.pack('<2I', *display[2:4])),
            (0x70e5c0, struct.pack('<I', display[4])),
            (0x715c90, struct.pack('<I', display[5])),
            (0x61c390, struct.pack('<2I', *display[6:])),
            (0x61c4c2, bytes([context['backend']]))]


def reference_job(executable, context):
    from_executable(executable)
    return encode_ee_job(CODE, {}, caller(context))


def browser_source_pack(executable, context):
    """Private original-source transport for a separately bounded EE executor."""
    proof = from_executable(executable)
    patches = caller(context)
    offset = struct.unpack_from('<I', executable, 28)[0]
    width, count = struct.unpack_from('<HH', executable, 42)
    chunks, regions, code = [], [], []
    for i in range(count):
        kind, source, address, _, filesz, memsz, flags, _ = struct.unpack_from('<8I', executable, offset+i*width)
        if kind == 1:
            need(filesz <= memsz and source+filesz <= len(executable) and address+memsz <= 0x2000000,
                 'vehicle uniform segment extent differs')
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
    code.extend([CODE+i, struct.unpack_from('<I', patches[0][1], i)[0]]
                for i in range(0, len(patches[0][1]), 4))
    return {'entry': CODE, 'chunks': chunks, 'regions': regions, 'code': code,
            'context': context, 'claim_limits': proof['claim_limits']}


def output(ram):
    need(len(ram) == 0x2000000, 'vehicle uniform RAM extent differs')
    end = struct.unpack_from('<I', ram, RESULT)[0]
    need(DMA < end <= DMA_END and end % 16 == 0, 'vehicle uniform DMA end differs')
    dma = ram[DMA:end]
    at, packets = 0, []
    while at < len(dma):
        tag, unused, vif0, vif1 = struct.unpack_from('<4I', dma, at)
        need(tag >> 16 == 0x1000 and unused == 0, 'vehicle uniform DMA tag differs')
        count = tag & 65535
        need(at+16+count*16 <= len(dma), 'vehicle uniform DMA extent differs')
        packets.append({'vif_words': [vif0, vif1],
                        'payload_words': list(struct.unpack_from('<'+'I'*(count*4), dma, at+16))})
        at += 16+count*16
    return {'dma_sha256': sha(dma), 'dma_bytes': len(dma), 'packets': packets,
            'camera_words': list(struct.unpack_from('<108I', ram, CAMERA))}


def execute_reference(executable, directory, runner=None):
    from mc3_reference_runtime import run_job
    runner = run_job if runner is None else runner
    executable, directory = Path(executable), Path(directory)
    proof = from_executable(executable.read_bytes())
    need(not directory.exists(), 'choose a fresh vehicle uniform directory')
    directory.mkdir(parents=True)
    rows = []
    for case in proof['cases']:
        job = directory/(case['name']+'.job')
        job.write_bytes(reference_job(executable.read_bytes(), case['context']))
        need(sha(job.read_bytes()) == case['job_sha256'], 'vehicle uniform job differs')
        execution = runner(job, directory/case['name'], mode='ee', executable=executable)
        actual = output((directory/case['name']/'ee-ram.bin').read_bytes())
        need(actual == case['expected'], 'original vehicle uniform output differs')
        rows.append({'name': case['name'], 'execution': execution, 'output': actual})
    (directory/'comparison.json').write_text(json.dumps(rows, indent=2)+'\n')
    return rows
