"""Execute original MC3 morph preprocessing with explicit source stream inputs.

This isolates the unchanged carpaint VU loop and consumes palettes produced by
original EE22ac20. It proves arithmetic, selector masking and positionW
preservation, not collision simulation or a complete vehicle draw.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf
from mc3_tire_vu import unpack_microprogram
from mc3_vehicle_animation import source_contract as animation_contract
from mc3_vehicle_vu import NOP

EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/vehicle-deformation.json')
PROOF_SHA = 'c2c8de0202585cde88466f45e0b68162e8007072cd7fc222191274af0e106409'
TOP = 64


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(executable=None, receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    need(hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
         == PROOF_SHA, 'vehicle deformation receipt changed')
    if executable is not None:
        need(hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
             'vehicle deformation source changed')
        source = proof['program']
        packet = _read_elf(executable, source['address'], source['bytes'])
        need(hashlib.sha256(packet).hexdigest() == source['sha256'], 'morph program changed')
        pairs = unpack_microprogram(packet)
        raw = b''.join(struct.pack('<II', *pairs[pc]) for pc in
                       range(source['first_pc'], source['last_pc']+1))
        need(hashlib.sha256(raw).hexdigest() == source['kernel_sha256'], 'morph loop changed')
        animation_contract(executable)
    return proof


def deformation_job(executable, state_byte):
    """Original36-pair loop, explicit six-vertex synthetic source stream."""
    proof = source_contract(executable)
    matches = [p for p in proof['probes'] if p['state_byte'] == state_byte]
    need(type(state_byte) is int and len(matches) == 1, 'unmeasured morph state')
    palette = next(p for p in animation_contract()['numerical_probes']
                   if p['kind'] == 'morph' and p['state_byte'] == state_byte)['output']['palette_words']
    source = proof['program']
    pairs = unpack_microprogram(_read_elf(executable, source['address'], source['bytes']))
    micro, memory = bytearray(16384), bytearray(16384)
    for pc, pair in pairs.items():
        struct.pack_into('<II', micro, pc*8, *pair)
    struct.pack_into('<IIII', micro, (source['last_pc']+1)*8,
                     NOP[0], NOP[1] | 0x40000000, *NOP)
    inputs = proof['inputs']
    struct.pack_into('<f', memory, TOP*16, inputs['position_scale'])
    struct.pack_into('<I', memory, (TOP+1)*16+12, len(inputs['positions']))
    for i, (position, morph) in enumerate(zip(inputs['positions'], inputs['morphs'])):
        struct.pack_into('<3iI', memory, (TOP+86+i)*16, *position, inputs['position_w_word'])
        struct.pack_into('<4I', memory, (TOP+128+i)*16, *morph)
    for i, words in enumerate(palette):
        struct.pack_into('<4I', memory, (792+i)*16, *words)
    job = bytes(bytearray(b'MC3VU001')+micro+memory+
                struct.pack('<I6I', 1, source['first_pc'], 0, TOP, 100000, 0, 0))
    need(hashlib.sha256(job).hexdigest() == matches[0]['job_sha256'], 'morph job changed')
    return job


def execute_reference(executable, output, runner=None):
    """Reexecute original EE palettes, then original VU morph preprocessing."""
    from mc3_reference_runtime import run_job
    from mc3_vehicle_animation import morph_palette_job, read_morph_palette
    runner = run_job if runner is None else runner
    proof = source_contract(executable)
    output = Path(output)
    need(not output.exists(), 'choose a fresh deformation output directory')
    output.mkdir(parents=True)
    source = output/'SLUS_213.55'
    source.write_bytes(executable)
    result = []
    for probe in proof['probes']:
        state = probe['state_byte']
        expected_palette = next(p for p in animation_contract()['numerical_probes']
                                if p['kind'] == 'morph' and p['state_byte'] == state)
        ee_job = morph_palette_job(executable, state)
        ee_path = output/f'{state}-palette.job'
        ee_path.write_bytes(ee_job)
        ee_receipt = runner(ee_path, output/f'{state}-palette', mode='ee', executable=source)
        need(ee_receipt['status'] == 'executed'
             and ee_receipt['job_sha256'] == expected_palette['job_sha256']
             and ee_receipt['runtime']['binary_sha256'] == proof['reference_binary_sha256']
             and ee_receipt['adapter_sha256'] == proof['adapter_sha256'], 'morph palette runtime changed')
        actual_palette = read_morph_palette((output/f'{state}-palette/ee-ram.bin').read_bytes())
        need(actual_palette == expected_palette['output'], 'executed morph palette changed')
        job = deformation_job(executable, state)
        path = output/f'{state}-loop.job'
        path.write_bytes(job)
        receipt = runner(path, output/f'{state}-loop')
        need(receipt['status'] == 'executed' and receipt['job_sha256'] == probe['job_sha256']
             and receipt['runtime']['binary_sha256'] == proof['reference_binary_sha256']
             and receipt['adapter_sha256'] == proof['adapter_sha256'], 'morph runtime changed')
        memory = (output/f'{state}-loop/final-vumem.bin').read_bytes()
        words = [list(struct.unpack_from('<4I', memory, (TOP+86+i)*16))
                 for i in range(len(proof['inputs']['positions']))]
        need(words == probe['output_words'], 'executed deformation changed')
        result.append({'state_byte': state, 'palette_execution': ee_receipt,
                       'loop_execution': receipt, 'output_words': words})
    (output/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
