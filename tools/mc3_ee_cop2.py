"""Original EE COP2 macro ADD/MUL instruction controls for MC3's Euler helper."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job

FIXTURE = Path(__file__).resolve().parents[1]/'research/evidence/midnight-club-3-remix/previews/ee-cop2.json'
INTERVAL_SHA = '30d9db3bcf0f03272e00ae21f1e838e9ae9796a39f0462806b54730c99ba271f'
START, INPUT, OUTPUT = 0x1000000, 0x1100000, 0x1200000
SOURCE = [(0x41c780, 0x4be8412a), (0x41c78c, 0x4be52199), (0x41c790, 0x4be521d8),
          (0x41c79c, 0x4be53183), (0x41c7a0, 0x4be539c2), (0x41c7a8, 0x4be431aa),
          (0x41c7ac, 0x4be439ea), (0x41c7b0, 0x4be53181), (0x41c7b8, 0x4be539c0)]
ADDI_SOURCE = [(0x41c784, 0x20e70040), (0x41c794, 0x20e7fff0), (0x41c7a4, 0x2108ffff)]
LIMITS = ['Only source-observed macro ADD broadcast and MUL full/broadcast families are added.',
          'MADD/accumulator behavior is retained, with snapshotted register operands for aliases.',
          'Full ADD, other macro operations, nonfinite operands and finite overflow remain rejected.',
          'Native controls compare all 128 VF words, not flags or instruction-cycle timing.',
          'Source-observed ADDI only supports sums within signed32; signed-overflow trap handling fails closed.',
          'Isolated original EE instruction execution is not whole MC3 gameplay rendering equivalence.']


def macro(fn, vd=4, vs=8, vt=5, mask=15):
    return 0x4a000000 | mask << 21 | vt << 16 | vs << 11 | vd << 6 | fn


def source_proof(executable):
    if hashlib.sha256(executable).hexdigest() != EXECUTABLE_SHA:
        raise ValueError('original MC3 executable differs')
    def read(address, size):
        return _read_elf(executable, address, size)
    for address, word in SOURCE+ADDI_SOURCE:
        if read(address, 4) != struct.pack('<I', word):
            raise ValueError('original Euler COP2 instruction differs')
    raw = read(0x41c6d8, 0x104)
    if hashlib.sha256(raw).hexdigest() != INTERVAL_SHA:
        raise ValueError('original Euler instruction interval differs')
    return dict(executable_sha256=EXECUTABLE_SHA, address=0x41c6d8, bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), hex=raw.hex(),
                observed=[dict(address=a, instruction=w) for a, w in SOURCE+ADDI_SOURCE])


def inputs():
    # Literal raw finite/subnormal/signed-zero operands; native outputs are not predicted here.
    words = [0x3f800001, 0xbfc00000, 0x33800000, 0x80000000, 0x00800000, 0x3f000000,
             0x007fffff, 0x00000001, 0x3fffffff, 0x40000000, 0xbf800000, 0x80800000]
    return [words[(reg*3+lane*5) % len(words)] for reg in range(32) for lane in range(4)]


def cases():
    rows = [dict(name=f'source-{address:x}', instruction=word) for address, word in SOURCE]
    for fn in [0, 1, 2, 3, 24, 25, 26, 27, 42, 8, 9, 10, 11]:
        for name, vd, vs, vt, mask in [('all', 4, 8, 5, 15), ('masked', 4, 8, 5, 5),
                                      ('empty-mask', 4, 8, 5, 0), ('destination-source', 8, 8, 5, 15),
                                      ('destination-broadcast', 5, 8, 5, 15), ('same-all', 5, 5, 5, 15),
                                      ('zero-destination', 0, 8, 5, 15), ('zero-source', 4, 0, 5, 15),
                                      ('zero-broadcast', 4, 8, 0, 15)]:
            rows.append(dict(name=f'op{fn:02x}-{name}', instruction=macro(fn, vd, vs, vt, mask)))
    for fn in [0, 1, 2, 3, 24, 25, 26, 27, 42]:
        rows.append(dict(name=f'op{fn:02x}-finite-boundary', instruction=macro(fn), profile='finite-boundary'))
    return rows


def case_inputs(case):
    words = inputs()
    if case.get('profile') == 'finite-boundary':
        words[8*4:8*4+4] = [0x7f7fffff, 0xff7fffff, 0x00800000, 0x80800000]
        words[5*4:5*4+4] = [0x00800000 if case['instruction'] & 63 <= 3 else 0x3f800000]*4
    return words


def native_inputs(controls):
    return b''.join(struct.pack('<128I', *case_inputs(case)) for case in controls)


def wrapper(controls):
    words = []
    for index, case in enumerate(controls):
        words += [0x3c080000 | (((INPUT+index*512) >> 16) & 65535), 0x35080000 | ((INPUT+index*512) & 65535),
                  0x3c090000 | (((OUTPUT+index*512) >> 16) & 65535), 0x35290000 | ((OUTPUT+index*512) & 65535)]
        words += [0xd9000000 | r << 16 | r*16 for r in range(32)]
        words += [macro(60, 6, 30, 31), case['instruction']]
        words += [0xf9200000 | r << 16 | r*16 for r in range(32)]
    words += [0x03e00008, 0]
    return words


def addi_cases():
    rows = [dict(name=f'source-{address:x}', instruction=word, low=0x1800000) for address, word in ADDI_SOURCE]
    for name, low, immediate in [('maximum', 0x7fffffff, 0), ('minimum', 0x80000000, 0),
                                 ('positive-edge', 0x7ffffffe, 1), ('negative-edge', 0x80000001, -1),
                                 ('minimum-plus', 0x80000000, 32767), ('maximum-minus', 0x7fffffff, -32768)]:
        rows.append(dict(name=name, instruction=0x20e70000 | (immediate & 65535), low=low))
    rows += [dict(name='separate-destination', instruction=0x20e60040, low=0x80000000),
             dict(name='zero-destination', instruction=0x20e00040, low=123)]
    for row in rows:
        row['input_words'] = [row.pop('low'), 0xdeadbeef, 0x12345678, 0x9abcdef0,
                              0, 0x11111111, 0x87654321, 0x0fedcba9]
    return rows


def addi_wrapper(rows):
    code = []
    for index, row in enumerate(rows):
        rs, rt = row['instruction'] >> 21 & 31, row['instruction'] >> 16 & 31
        code += [0x3c0a0130, 0x354a0000 | index*32, 0x3c0b0140, 0x356b0000 | index*16,
                 0x79400000 | rs << 16]
        if rs != rt:
            code.append(0x79400010 | rt << 16)
        code += [row['instruction'], 0x7d600000 | rt << 16]
    return code+[0x03e00008, 0]


def addi_reference(executable, output):
    rows = addi_cases()
    words = addi_wrapper(rows)
    job = encode_ee_job(START, {}, [(START, struct.pack('<'+'I'*len(words), *words)),
                                   (0x1300000, b''.join(struct.pack('<8I', *v['input_words']) for v in rows))])
    path = output/'addi.job';path.write_bytes(job)
    receipt = run_job(path, output/'addi-native', mode='ee', executable=executable)
    ram = (output/'addi-native/ee-ram.bin').read_bytes()
    for index, row in enumerate(rows):
        row['expected_words'] = list(struct.unpack_from('<4I', ram, 0x1400000+index*16))
    return dict(cases=rows, execution=receipt)


def reference(executable, output):
    executable, output = Path(executable), Path(output)
    proof = source_proof(executable.read_bytes())
    controls = cases()
    code = struct.pack('<'+'I'*len(wrapper(controls)), *wrapper(controls))
    job = encode_ee_job(START, {}, [(START, code), (INPUT, native_inputs(controls))])
    output.mkdir(parents=True, exist_ok=False)
    (output/'control.job').write_bytes(job)
    receipt = run_job(output/'control.job', output/'native', mode='ee', executable=executable)
    ram = (output/'native/ee-ram.bin').read_bytes()
    for index, case in enumerate(controls):
        case['expected_vf'] = list(struct.unpack_from('<128I', ram, OUTPUT+index*512))
    result = dict(schema=1, source=proof, inputs=inputs(), cases=controls, seed_accumulator=macro(60, 6, 30, 31),
                  execution=receipt, addi=addi_reference(executable, output), claim_limits=LIMITS)
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--write-fixture', action='store_true')
    args = parser.parse_args()
    result = reference(args.executable, args.output)
    if args.write_fixture:
        FIXTURE.write_text(json.dumps(result, indent=2)+'\n')
