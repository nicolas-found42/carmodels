"""Original EE MTLO/MADD low-word accumulator controls for native MC3 dispatcher."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/ee-mac.json'
SOURCE = [(0x2a80a0, 0x00400013), (0x2a80ac, 0x72622000)]
PINS = {'R5900OpcodeTables.cpp': 'b96376cfff67799af5fe72bbfe4490c077f3368740dbf368d0a0e6f7be877f59',
        'MMI.cpp': '5b5a045dfbf896bc470d8aed658dfc492a07a5b74859a0d7832b2969f539159a',
        'R5900OpcodeImpl.cpp': '6ae749a7e3a297a291f1844d2f96a17bf7c53a9c6f6f4ab4ddab27781a78c2b4'}
COMMIT = 'fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3'
START, INPUT, OUTPUT = 0x1000000, 0x1300000, 0x1400000


def cases():
    rows = []
    profiles = [('source', 0x1001000, 0, 7, 48), ('carry-low32', 0xffffffff, 0, 1, 1),
                ('negative-product', 0, 0, 0xffffffff, 1), ('borrow', 0, 1, 0xffffffff, 1),
                ('sign-low32', 0x7fffffff, 0, 1, 1), ('sign-high32', 0xffffffff, 0x7fffffff, 1, 1),
                ('wrap64', 0xffffffff, 0xffffffff, 1, 1), ('positive-product', 0, 0, 0x7fffffff, 0x7fffffff),
                ('minimum-product', 0x80000000, 0, 0x80000000, 0xffffffff),
                ('ignored-upper32', 17, 3, 23, 19), ('zero-product', 0xfedcba98, 0x89abcdef, 0, 0xffffffff)]
    for name, lo, hi, a, b in profiles:
        for suffix, rd in [('dest', 4), ('alias-left', 19), ('alias-right', 2), ('zero-dest', 0)]:
            rows.append(dict(name=name+'-'+suffix, kind='madd', instruction=0x70000000 | 19 << 21 | 2 << 16 | rd << 11,
                             lo_words=[lo, 0x11223344], hi_words=[hi, 0x55667788], a=a, b=b))
    for name, low, high in [('source', 0x1001000, 0), ('raw64', 0x89abcdef, 0xfedcba98),
                            ('signed32', 0x80000000, 0x01234567), ('zero', 0, 0)]:
        rows.append(dict(name='mtlo-'+name, kind='mtlo', instruction=0x00400013, lo_words=[17, 19],
                         hi_words=[0x9abcdef0, 0x12345678], a=0, b=low, b_high=high))
    for row in rows:
        registers = {2: [row.pop('b'), row.pop('b_high', 0xa5a5a5a5), 0x12345678, 0x9abcdef0],
                     19: [row.pop('a'), 0xb6b6b6b6, 0x87654321, 0x0fedcba9],
                     4: [0, 0xc7c7c7c7, 0xcafefeed, 0xfedcba98],
                     13: [*row['lo_words'], 0x11111111, 0x22222222],
                     14: [*row['hi_words'], 0x33333333, 0x44444444]}
        row['registers'] = sorted(registers.items())
    return rows


def job(rows):
    words, data = [], bytearray()
    for index, row in enumerate(rows):
        words += [0x3c0a0130, 0x354a0000 | index*128, 0x3c0b0140, 0x356b0000 | index*48]
        raw = bytearray(128)
        for offset, (reg, value) in enumerate(row['registers']):
            struct.pack_into('<4I', raw, offset*16, *value);words += [0x79400000 | reg << 16 | offset*16]
        data.extend(raw)
        # MTHI is an oracle-only initial-state setter, not newly enabled in the
        # browser. Native output observes HI directly through existing MFHI.
        words += [0x01a00013, 0x01c00011, row['instruction']]
        rd = 2 if row['kind'] == 'mtlo' else row['instruction'] >> 11 & 31
        words += [0x7d600000 | rd << 16, 0x00006012, 0x7d6c0010, 0x00007810, 0x7d6f0020]
    words += [0x03e00008, 0]
    return encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(words), *words)), (INPUT, data)])


def reference(executable, sources, output):
    executable, output = Path(executable), Path(output);original = executable.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXECUTABLE_SHA:
        raise ValueError('original MC3 executable differs')
    for name, digest in PINS.items():
        if hashlib.sha256(Path(sources[name]).read_bytes()).hexdigest() != digest:
            raise ValueError('original native MAC source differs: '+name)
    for a, w in SOURCE:
        if _read_elf(original, a, 4) != struct.pack('<I', w):
            raise ValueError('original MTLO/MADD instruction differs')
    rows = cases();data = job(rows)
    output.mkdir(parents=True, exist_ok=False);(output/'control.job').write_bytes(data)
    receipt = run_job(output/'control.job', output/'native', mode='ee', executable=executable)
    ram = (output/'native/ee-ram.bin').read_bytes()
    for index, row in enumerate(rows):
        row['expected_destination'] = list(struct.unpack_from('<4I', ram, OUTPUT+index*48))
        row['expected_lo'] = list(struct.unpack_from('<2I', ram, OUTPUT+index*48+16))
        row['expected_hi'] = list(struct.unpack_from('<2I', ram, OUTPUT+index*48+32))
    result = dict(schema=1, source=dict(executable_sha256=EXECUTABLE_SHA, observed=SOURCE, commit=COMMIT, sources=PINS),
                  cases=rows, execution=receipt,
                  claim_limits=['Observed MTLO low64 copy and MADD signed32 product plus LO/HI low32 accumulator only.',
                                'MTHI/MFHI are oracle-only initial-state/observation instructions; they remain unsupported in the browser.',
                                'All native128 destination and low64 LO/HI words compared, including carry/sign/wrap/alias/register0 controls.',
                                'Upper64 of the hardware128 LO/HI registers, flags/timing and whole gameplay rendering remain outside scope.'])
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True);parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decoder-source', type=Path, required=True);parser.add_argument('--operation-source', type=Path, required=True)
    parser.add_argument('--scalar-source', type=Path, required=True);parser.add_argument('--write-fixture', action='store_true');args = parser.parse_args()
    proof = reference(args.executable, dict(zip(PINS, [args.decoder_source, args.operation_source, args.scalar_source], strict=True)), args.output)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(proof, indent=2)+'\n')
