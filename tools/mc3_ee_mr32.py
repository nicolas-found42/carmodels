"""Original EE VMR32 raw-lane macro controls for MC3 compact frame composition."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job

COMMIT = 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3'

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/ee-mr32.json'
SOURCE = [(0x23e320, 0x4be6333d), (0x23e324, 0x4be73b3d),
          (0x23e328, 0x4be6333d), (0x23e32c, 0x4be5333d)]
PINS = {'R5900OpcodeTables.cpp': 'b96376cfff67799af5fe72bbfe4490c077f3368740dbf368d0a0e6f7be877f59',
        'VUops.cpp': '1cb75c6d9e2a16cbf29d6f4ba11ce8d4cbb06061c73006b4691854556c9ba0ee'}
START, INPUT, OUTPUT = 0x1000000, 0x1100000, 0x1200000


def source_proof(executable, decoder, operations):
    if hashlib.sha256(executable).hexdigest() != EXECUTABLE_SHA:
        raise ValueError('original MC3 executable differs')
    for name, data in [('R5900OpcodeTables.cpp', decoder), ('VUops.cpp', operations)]:
        if hashlib.sha256(data).hexdigest() != PINS[name]:
            raise ValueError('pinned original EE macro source differs: '+name)
    raw = _read_elf(executable, 0x23e320, 16)
    for address, word in SOURCE:
        if struct.unpack_from('<I', raw, address-0x23e320)[0] != word:
            raise ValueError('original MC3 MR32 source instruction differs')
    return dict(executable_sha256=EXECUTABLE_SHA, address=0x23e320, hex=raw.hex(),
                sha256=hashlib.sha256(raw).hexdigest(), decoder_commit=COMMIT,
                sources={name: dict(sha256=digest, url=f'https://raw.githubusercontent.com/PCSX2/pcsx2/{COMMIT}/pcsx2/{name}')
                         for name, digest in PINS.items()})


def inputs():
    words = [0x00000001, 0x80000000, 0x7fc12345, 0xff800000, 0xdeadbeef, 0x3f800000,
             0x7fa12345, 0xffffffff, 0x80000001, 0x00800000, 0x12345678, 0x7f800000]
    return [words[(reg*3+lane*5) % len(words)] for reg in range(32) for lane in range(4)]


def mr32(ft, fs, mask=15):
    return 0x4a00033d | mask << 21 | ft << 16 | fs << 11


def cases():
    rows = [dict(name=f'source-{a:x}', instruction=w) for a, w in SOURCE]
    for mask in range(16):
        rows += [dict(name=f'mask-{mask}-separate', instruction=mr32(7, 6, mask)),
                 dict(name=f'mask-{mask}-alias', instruction=mr32(6, 6, mask))]
    rows += [dict(name='zero-destination', instruction=mr32(0, 6)),
             dict(name='zero-source', instruction=mr32(6, 0))]
    return rows


def wrapper(rows):
    code = []
    for i, row in enumerate(rows):
        code += [0x3c080110, 0x35080000 | i*512, 0x3c090120, 0x35290000 | i*512]
        code += [0xd9000000 | r << 16 | r*16 for r in range(32)]
        code += [row['instruction']]
        code += [0xf9200000 | r << 16 | r*16 for r in range(32)]
    return code+[0x03e00008, 0]


def reference(executable, decoder, operations, output):
    executable, output = Path(executable), Path(output)
    source = source_proof(executable.read_bytes(), Path(decoder).read_bytes(), Path(operations).read_bytes())
    rows = cases();words = wrapper(rows)
    data = encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(words), *words)),
                                   (INPUT, struct.pack('<128I', *inputs())*len(rows))])
    output.mkdir(parents=True, exist_ok=False);(output/'control.job').write_bytes(data)
    receipt = run_job(output/'control.job', output/'native', mode='ee', executable=executable)
    ram = (output/'native/ee-ram.bin').read_bytes()
    for i, row in enumerate(rows):
        row['expected_vf'] = list(struct.unpack_from('<128I', ram, OUTPUT+i*512))
    result = dict(schema=1, source=source, inputs=inputs(), cases=rows, execution=receipt,
                  claim_limits=['Only observed VMR32 macro encoding and masked raw VF lane rotation.',
                                'All 128 VF raw words compared; flags, timing and other SPECIAL2 operations remain outside scope.',
                                'Raw NaN/infinite/subnormal bits are copied without arithmetic or normalization.',
                                'Isolated original instructions, not a complete vehicle/gameplay rendering claim.'])
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--decoder-source', type=Path, required=True)
    parser.add_argument('--operation-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--write-fixture', action='store_true');args = parser.parse_args()
    proof = reference(args.executable, args.decoder_source, args.operation_source, args.output)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, indent=2)+'\n')
