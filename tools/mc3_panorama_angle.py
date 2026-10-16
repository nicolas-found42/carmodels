"""Original MC3 panorama angle and caller conversion reference inputs.

The caller interval is relocated intact, including its native virtual texture
width getter. Explicit camera-axis and image fields are test inputs, not a live
vehicle frame. Wrappers only store outputs and return to the reference adapter.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/panorama-angle.json'
PROOF_SHA = '11893f1974ebbd4b8f9717c3bee2fcc0ba514ca4a25a5313d313533bcd22f9af'


def source_contract(executable=None, receipt=None):
    proof = json.loads(FIXTURE.read_text()) if receipt is None else receipt
    digest = hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if digest != PROOF_SHA:
        raise ValueError('panorama angle receipt changed')
    if executable is not None:
        if hashlib.sha256(executable).hexdigest() != EXECUTABLE_SHA:
            raise ValueError('panorama angle executable changed')
        for source in proof['source_intervals']:
            if hashlib.sha256(_read_elf(executable, source['start'], source['bytes'])).hexdigest() != source['sha256']:
                raise ValueError('panorama angle source interval changed')
    return proof


def angle_job(executable, x_word, z_word):
    source_contract(executable)
    for word in (x_word, z_word):
        if type(word) is not int or not 0 <= word <= 0xffffffff:
            raise ValueError('invalid panorama axis word')
    code = struct.pack('<9I', 0x0c000000 | (0x41cc50 >> 2), 0, 0x3c0801f0,
                       0xe5002000, 0x3c1f0001, 0x03e00008, 0, 0, 0)
    return encode_ee_job(0x1f00000, {}, [(0x1f00000, code)], {12: x_word, 13: z_word})


def caller_job(executable, x_word, z_word, width):
    source_contract(executable)
    for word in (x_word, z_word):
        if type(word) is not int or not 0 <= word <= 0xffffffff:
            raise ValueError('invalid panorama axis word')
    if type(width) is not int or not 1 <= width <= 1024 or width & (width-1):
        raise ValueError('unsupported native panorama width')
    code = _read_elf(executable, 0x5636e0, 0xa4)+struct.pack('<6I', 0x3c0801f0, 0xad112000,
                     0xe5142004, 0x3c1f0001, 0x03e00008, 0)
    context, capture, image = bytearray(0x1a0), bytearray(0x2900), bytearray(160)
    struct.pack_into('<I', context, 0x19c, 0x1f08000)
    struct.pack_into('<I', capture, 0x34, 0x1f09000)
    capture[0x28d0] = 1
    struct.pack_into('<I', image, 0, 0x627280)
    struct.pack_into('<Q', image, 0x10, (width.bit_length()-1) << 26 | 8 << 30)
    patches = [(0x1f00000, code), (0x615b40, struct.pack('<I', 0x1f04000)),
               (0x1f04000, context), (0x1f05000, capture),
               (0x1f08000, struct.pack('<3I', x_word, 0, z_word)), (0x1f09000, image)]
    return encode_ee_job(0x1f00000, {23: 0x610000, 19: 0x1f05000}, patches)


def execute_reference(executable, output):
    """Reexecute all pinned original helper/caller jobs and compare stored words."""
    from mc3_reference_runtime import run_job
    proof = source_contract(executable)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source = output/'SLUS_213.55'
    source.write_bytes(executable)
    receipts = []
    for kind in ('angles', 'callers'):
        for index, row in enumerate(proof[kind]):
            name = f'{kind}-{index}'
            raw = angle_job(executable, row['x_word'], row['z_word']) if kind == 'angles' else \
                caller_job(executable, row['x_word'], row['z_word'], row['width'])
            job = output/(name+'.job')
            job.write_bytes(raw)
            receipt = run_job(job, output/name, mode='ee', executable=source)
            if receipt['job_sha256'] != row['execution']['job_sha256'] \
                    or receipt['outputs']['ee-ram.bin']['sha256'] != row['execution']['outputs']['ee-ram.bin']['sha256']:
                raise ValueError('original panorama reference input/RAM differs')
            ram = (output/name/'ee-ram.bin').read_bytes()
            expected = (row['angle_word'],) if kind == 'angles' else (row['offset16'], row['scaled_word'])
            if struct.unpack_from('<'+'I'*len(expected), ram, 0x1f02000) != expected:
                raise ValueError('original panorama reference output words differ')
            receipts.append(receipt)
    (output/'comparison.json').write_text(json.dumps(receipts, indent=2)+'\n')
    return receipts
