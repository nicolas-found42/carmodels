"""Observed SDK/hash EE integer operations, measured by the pinned interpreter."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job
from mc3_ee_mac import PINS, COMMIT

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/ee-division.json'
SOURCE = [(0x545160, 0x0070001a), (0x42df8c, 0x0064001b), (0x42dfa4, 0x00001010),
          (0x545178, 0x64a5027c), (0x54518c, 0x72a31018), (0x545240, 0x72a31018),
          (0x5452c8, 0x70502018), (0x546058, 0x0082102f), (0x54605c, 0x0083202f)]
START, INPUT, OUTPUT = 0x1000000, 0x1300000, 0x1400000
ACCUMULATORS = ['0123456789abcdef', 'fedcba9876543210', 'a5a5a5a55a5a5a5a', 'f0e1d2c3b4a59687']


def cases():
    rows = []
    profiles = [('positive', 17, 3), ('negative-left', 0xfffffff1, 3),
                ('negative-right', 17, 0xfffffffd), ('negative-both', 0xfffffff1, 0xfffffffd),
                ('minimum-overflow', 0x80000000, 0xffffffff), ('minimum', 0x80000000, 3),
                ('maximum', 0x7fffffff, 0xffffffff), ('unsigned-maximum', 0xffffffff, 7),
                ('zero-left', 0, 3), ('zero-both', 0, 0), ('zero-divisor-positive', 17, 0),
                ('zero-divisor-negative', 0x80000001, 0)]
    for kind, fn in [('div', 26), ('divu', 27)]:
        for name, a, b in profiles:
            rows.append(dict(name=kind+'-'+name, kind=kind, instruction=2<<21 | 3<<16 | 4<<11 | fn,
                             a=f'12345678{a:08x}', b=f'fedcba98{b:08x}'))
        rows.append(dict(name=kind+'-aliased-input', kind=kind, instruction=2<<21 | 2<<16 | fn,
                         a='fedcba9880000000', b='fedcba9880000000'))
    for kind, opcode in [('mult1', 0x70000018), ('dsubu', 0x2f)]:
        for name, a, b in [('positive', 17, 3), ('negative', 0xfffffff1, 3),
                           ('minimum', 0x80000000, 0xffffffff), ('maximum', 0x7fffffff, 0x7fffffff),
                           ('wide', 0xfedcba9889abcdef, 0x123456789abcdef0),
                           ('wrap', 0xffffffffffffffff, 0), ('zero', 0, 0)]:
            for suffix, rd in [('distinct', 4), ('left', 2), ('right', 3), ('zero', 0)]:
                rows.append(dict(name=kind+'-'+name+'-'+suffix, kind=kind,
                                 instruction=opcode | 2<<21 | 3<<16 | rd<<11,
                                 a=f'{a:016x}', b=f'{b:016x}'))
    for name, a, imm in [('positive', 17, 0x27c), ('negative-immediate', 17, 0x8000),
                         ('maximum-immediate', 0, 0x7fff), ('carry32', 0xffffffff, 1),
                         ('wrap64', 0xffffffffffffffff, 1), ('borrow64', 0, 0xffff),
                         ('sign64', 0x7fffffffffffffff, 1), ('raw64', 0x123456789abcdef0, 0xffff)]:
        for suffix, rt in [('distinct', 4), ('alias', 2), ('zero', 0)]:
            rows.append(dict(name='daddiu-'+name+'-'+suffix, kind='daddiu',
                             instruction=25<<26 | 2<<21 | rt<<16 | imm,
                             a=f'{a:016x}', b='0000000000000000'))
    for rd in [0, 2, 4]:
        rows.append(dict(name=f'mfhi-{rd}', kind='mfhi', instruction=rd<<11 | 16,
                         a='0000000000000000', b='0000000000000000'))
    return rows


def destination(row):
    return row['instruction'] >> (16 if row['kind'] == 'daddiu' else 11) & 31


def registers(row):
    word = row['instruction'];rs, rt, rd = word>>21 & 31, word>>16 & 31, destination(row)
    values = {r: [0xabcdef00+r, 0x87654321, 0x12340000+r, 0xfedc0000+r]
              for r in {rs, rt, rd}-{0}}
    inputs = [(rs, row['a'])] if row['kind'] == 'daddiu' else [(rs, row['a']), (rt, row['b'])]
    for r, value in inputs:
        if r and row['kind'] != 'mfhi':
            values[r][:2] = [int(value[-8:], 16), int(value[:8], 16)]
    return sorted(values.items())


def job(rows):
    words, data = [], bytearray()
    for index, row in enumerate(rows):
        words += [0x3c0a0130, 0x354a0000 | index*128, 0x3c0b0140, 0x356b0000 | index*64]
        raw = bytearray(128)
        bindings = registers(row) + [(13+i, [int(v[-8:], 16), int(v[:8], 16), 0, 0])
                                     for i, v in enumerate(ACCUMULATORS)]
        for offset, (r, value) in enumerate(bindings):
            if r in [10, 11, 12, 31] or offset >= 8:
                raise ValueError('integer control aliases observer')
            struct.pack_into('<4I', raw, offset*16, *value)
            words += [0x79400000 | r<<16 | offset*16]
        data.extend(raw)
        # Oracle-only MTHI/MTHI1/MTLO1 and observation do not enable those
        # instruction families in the bounded browser executor.
        words += [13<<21 | 19, 14<<21 | 17, 0x70000013 | 15<<21, 0x70000011 | 16<<21,
                  row['instruction'], 0x7d600000 | destination(row)<<16]
        for i, instruction in enumerate([0x00006012, 0x00006010, 0x70006012, 0x70006010]):
            words += [instruction, 0xfd6c0010+i*8]
    words += [0x03e00008, 0]
    return encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(words), *words)), (INPUT, data)])


def reference(executable, sources, output):
    executable, output = Path(executable), Path(output)
    original = executable.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXECUTABLE_SHA:
        raise ValueError('original integer executable differs')
    for name, digest in PINS.items():
        if hashlib.sha256(Path(sources[name]).read_bytes()).hexdigest() != digest:
            raise ValueError('pinned integer source differs: '+name)
    for address, word in SOURCE:
        if _read_elf(original, address, 4) != struct.pack('<I', word):
            raise ValueError('observed integer instruction differs')
    rows = cases();raw = job(rows)
    output.mkdir(parents=True, exist_ok=False);(output/'control.job').write_bytes(raw)
    receipt = run_job(output/'control.job', output/'native', mode='ee', executable=executable)
    ram = (output/'native/ee-ram.bin').read_bytes()
    for i, row in enumerate(rows):
        row['expected_destination'] = list(struct.unpack_from('<4I', ram, OUTPUT+i*64))
        row['expected_accumulators'] = list(struct.unpack_from('<8I', ram, OUTPUT+i*64+16))
    result = dict(schema=1, source=dict(executable_sha256=EXECUTABLE_SHA, observed=SOURCE, commit=COMMIT, sources=PINS),
                  accumulator_inputs=ACCUMULATORS, cases=rows, execution=receipt,
                  claim_limits=['Observed DIV/DIVU/MFHI/DADDIU/DSUBU and MULT1fn18sa0 only.',
                                'Native raw128 GPR destination and both low/upper64 HI/LO halves are observed; untouched halves must retain their seeds.',
                                'MTHI/MTHI1/MTLO1/MFHI1/MFLO1 are oracle-only setup/readout, not newly enabled browser instructions.',
                                'No cycle timing, exceptions beyond these opcodes, complete SDK/gameplay or physicalhardware claim.'])
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--emit-job']:
        sys.stdout.buffer.write(job(cases()))
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True);parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decoder-source', type=Path, required=True);parser.add_argument('--operation-source', type=Path, required=True)
    parser.add_argument('--scalar-source', type=Path, required=True);parser.add_argument('--write-fixture', action='store_true')
    args = parser.parse_args()
    result = reference(args.executable, dict(zip(PINS, [args.decoder_source, args.operation_source, args.scalar_source], strict=True)), args.output)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, separators=(',', ':'))+'\n')
