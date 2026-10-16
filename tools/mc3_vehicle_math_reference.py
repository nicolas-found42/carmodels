"""Deterministic, independently executed MC3 vehicle arithmetic contexts.

Original VU instruction pairs perform all vertex arithmetic. Synthetic setup
resets inputs; a post-kernel observer transports raw registers through GIF NOP
payloads. Expected output words never participate in job construction.
"""
import hashlib
import json
from pathlib import Path
import random
import struct

from mc3_environment_raster import _read_elf
from mc3_tire_vu import unpack_microprogram
from mc3_vehicle_vu import kernel_job, source_contract

AREA = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews'
EVIDENCE = AREA / 'vehicle-math-reference.json'
PROGRAMS = ('carpaint_3pass_dc', 'carbon_fiber_dc', 'light_texgen_dc', 'texgen_fresnel_dc')
SEED = 127173
PROOF_SHA = 'c8b3850831455aff18561ad1393ae27575bee19304c1b5ea05378c9cb408e8af'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def words(values):
    return list(struct.unpack('<4I', struct.pack('<4f', *values)))


def contexts():
    """Explicit synthetic finite inputs, regenerated independently of goldens."""
    rng, result = random.Random(SEED), []
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    for index in range(32):
        mvp = [[f32(rng.uniform(-.8, .8)) for _ in range(4)] for _ in range(4)]
        mvp[3][3] = f32(2 + rng.random())
        normal = [rng.randrange(-128, 128) for _ in range(3)]
        position = [f32(rng.uniform(-.6, .6)) for _ in range(3)]
        uv = [[f32(rng.uniform(-1, 1)), f32(rng.uniform(-1, 1)), 0, 0] for _ in range(3)]
        uv[2][2] = 1
        if index == 31:
            uv[0][2], uv[1][2], uv[2][2] = .125, -.0625, .75
        result.append({'normal': normal, 'position': position, 'mvp': mvp, 'uvMatrix': uv,
                       'lightRows': [[f32(rng.uniform(-1, 1)/128) for _ in range(3)] for _ in range(3)],
                       'lightColors': [[f32(rng.uniform(0, .6)) for _ in range(3)]+[0] for _ in range(3)]
                       + [[f32(rng.uniform(0, .25)) for _ in range(3)]+[1]],
                       'material': [f32(rng.uniform(1, 128)) for _ in range(4)],
                       'parameters': [f32(rng.uniform(.01, .9)), .05, .95, f32(rng.uniform(.1, 1))]})
    return result


def reference_contract(receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    need(digest(proof) == PROOF_SHA, 'vehicle numerical reference receipt changed')
    need(proof['contexts'] == contexts() and proof['contexts_sha256'] == digest(contexts()),
         'vehicle numerical reference context changed')
    return proof


def context_memory(context):
    memory = bytearray(16384)
    def row(index, values):
        struct.pack_into('<4I', memory, index*16, *words(values))
    for key, start in [('mvp', 20), ('uvMatrix', 16), ('lightColors', 28)]:
        for index, vector in enumerate(context[key]):
            row(start+index, vector)
    for index, vector in enumerate(context['lightRows']):
        row(24+index, vector+[0])
    for index, vector in [(8, [1, 1, 1, 0]), (9, [0, 0, 0, 0]), (42, context['material']),
                          (52, [2, .25, 0, 0]), (53, context['parameters']),
                          (86, context['position']+[0])]:
        row(index, vector)
    struct.pack_into('<4i', memory, 32, *context['normal'], 0)
    # An observer GIF NOP payload carries all31 nonzero raw vector registers.
    struct.pack_into('<QQ', memory, 900*16, 31 | 1 << 15 | 1 << 60, 0xF)
    vf = {index: [0]*4 for index in range(1, 32)}
    for register, slot in [(1, 20), (2, 21), (3, 22), (4, 23), (5, 8), (6, 9)]:
        vf[register] = list(struct.unpack_from('<4I', memory, slot*16))
    return bytes(memory), vf


def reference_job(executable, program, inputs=None):
    need(program in PROGRAMS, 'unsupported vehicle reference program')
    inputs = contexts() if inputs is None else inputs
    need(inputs == contexts(), 'vehicle reference contexts changed')
    source = source_contract(executable)['kernels'][program]
    states = [context_memory(context) for context in inputs]
    first, _ = kernel_job(executable, program, *states[0])
    micro = bytearray(first[8:8+16384])
    pairs = unpack_microprogram(_read_elf(executable, source['address'], source['bytes']))
    def pair(pc, lower, upper=0x2FF):
        struct.pack_into('<II', micro, pc*8, lower, upper)
    stop = source['last_pc']+1
    if program == 'carpaint_3pass_dc':
        # Original next pair performs the second generated UV's Q multiply.
        pair(stop, *pairs[stop])
        stop += 1
    for pc in range(stop, stop+5):
        pair(pc, 0x8000033C)
    pc = stop+5
    if program == 'texgen_fresnel_dc':
        # Starting VI09 is zero, so native SQ at0105 writes STQ toVU2.
        pair(pc, 0x01FF0000 | 2)
        pc += 1
        for _ in range(5):
            pair(pc, 0x8000033C)
            pc += 1
    for register in range(1, 32):
        pair(pc, 0x03E00000 | register << 11 | (900+register))
        pc += 1
    pair(pc, 0x100F0384)
    pc += 1
    for _ in range(4):
        pair(pc, 0x8000033C)
        pc += 1
    pair(pc, 0x80007800 | 0x6FC)
    pc += 1
    for _ in range(4):
        pair(pc, 0x8000033C)
        pc += 1
    pair(pc, 0x8000033C, 0x400002FF)
    pair(pc+1, 0x8000033C)
    # Each call resets integer inputs before entering the untouched kernel.
    pc = 0x700
    for register in range(1, 16):
        pair(pc, 0x10000000 | register << 16)
        pc += 1
    pair(pc, 0x100F0000 | source['first_pc'])
    pc += 1
    for _ in range(4):
        pair(pc, 0x8000033C)
        pc += 1
    pair(pc, 0x48007800)
    pair(pc+1, 0x8000033C)
    job = bytearray(b'MC3VU001') + micro + bytes(16384) + struct.pack('<I', len(states))
    for memory, vf in states:
        job += struct.pack('<6I', 0x700, 0, 0, 100000, 1, 31)
        job += struct.pack('<II', 0, 16384) + memory
        for register, vector in sorted(vf.items()):
            job += struct.pack('<I4I', register, *vector)
    original = b''.join(struct.pack('<II', *pairs[i]) for i in range(source['first_pc'], stop))
    return bytes(job), {'source_first_pc': source['first_pc'], 'source_last_pc': stop-1,
                        'source_kernel_sha256': hashlib.sha256(original).hexdigest(),
                        'contexts_sha256': digest(inputs), 'job_sha256': hashlib.sha256(job).hexdigest()}


def observer_outputs(program, data, calls):
    from mc3_reference_runtime import gif_chunks
    chunks = gif_chunks(data)
    need(len(calls) == 32, 'incomplete vehicle reference calls')
    result, cursor = [], 0
    rgba_register = dict(zip(PROGRAMS, [24, 25, 22, 14]))[program]
    for index, call in enumerate(calls):
        need(call['index'] == index and call['pc'] == 0x700 and call['top'] == call['itop'] == 0
             and call['start_chunk'] == cursor and cursor <= call['end_chunk'] <= len(chunks),
             'vehicle observer call binding changed')
        cursor = call['end_chunk']
        raw = b''.join(chunks[call['start_chunk']:cursor])
        need(len(raw) == 512 and raw[:16] == struct.pack('<QQ', 31 | 1 << 15 | 1 << 60, 0xF),
             'vehicle observer transport changed')
        def vector(register):
            return list(struct.unpack_from('<4I', raw, 16+(register-1)*16))
        output = {'rgba': vector(rgba_register)}
        if program == 'carpaint_3pass_dc':
            output.update(st_words=vector(22)[2:], second_stq_words=vector(21)[:3])
        elif program != 'carbon_fiber_dc':
            output['stq_words'] = vector(20 if program == 'light_texgen_dc' else 31)[:3]
        result.append(output)
    need(cursor == len(chunks), 'unbound vehicle observer chunks')
    return result


def execute_reference(executable, output, runner=None):
    from mc3_reference_runtime import run_job
    runner = run_job if runner is None else runner
    proof = reference_contract()
    output = Path(output)
    need(not output.exists(), 'choose a fresh vehicle reference output directory')
    output.mkdir(parents=True)
    result = {}
    for program in PROGRAMS:
        job, binding = reference_job(executable, program)
        expected = proof['programs'][program]
        need(binding == expected['binding'], 'vehicle numerical reference source/job changed')
        path, directory = output/(program+'.job'), output/program
        path.write_bytes(job)
        receipt = runner(path, directory)
        need(receipt['status'] == 'executed' and receipt['job_sha256'] == binding['job_sha256']
             and receipt['runtime']['binary_sha256'] == proof['reference_binary_sha256']
             and receipt['adapter_sha256'] == proof['adapter_sha256'],
             'vehicle numerical reference execution binding changed')
        actual = observer_outputs(program, (directory/'gif-chunks.bin').read_bytes(),
                                  json.loads((directory/'calls.json').read_text()))
        need(actual == expected['outputs'], 'vehicle numerical reference output changed')
        result[program] = {'binding': binding, 'outputs': actual, 'execution': receipt}
    (output/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
