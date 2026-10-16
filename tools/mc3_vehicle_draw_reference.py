"""Whole original vehicle VU programs over explicit authored VIF batch controls.

Camera, light, material and state uniforms are explicit synthetic controls.
Source geometry is real; tested microprogram selection is a cross-program
control, not an authored pass/registry join. These jobs do not reconstruct
an active vehicle's gameplay state or claim a complete original-game frame.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _PacketView, _read_elf, encode_job
from mc3_pck import Pck, read_vehicle, vif_planes
from mc3_tire_vu import unpack_microprogram
from mc3_vehicle_vu import source_contract as vu_contract

EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/vehicle-draw-reference.json')
PROOF_SHA = '37435b9bb034ce8eaf6f3b2f14e8546c0457f2d22e1e6185801e5f3fea3867ec'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(executable=None, receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    need(hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
         == PROOF_SHA, 'vehicle draw receipt changed')
    vu_contract(executable)
    if executable is not None:
        for source in proof['programs'].values():
            raw = _read_elf(executable, source['address'], source['bytes'])
            need(hashlib.sha256(raw).hexdigest() == source['sha256'], 'vehicle program changed')
    return proof


def batch_patches(packet, batch_offset):
    """Source VIF lanes; only the selected native contiguous layouts are allowed."""
    planes = vif_planes(_PacketView(packet), 0, len(packet))
    starts = [i for i, p in enumerate(planes) if p['offset'] == batch_offset]
    need(len(starts) == 1, 'vehicle source batch missing')
    first = starts[0]
    header = planes[first]
    need(header['components'] == 4 and header['count'] == 2
         and header['address'] in (0x98, 0x1C5), 'vehicle batch header changed')
    last = next((i for i in range(first+1, len(planes)) if planes[i]['components'] in (1, 4)
                 and planes[i]['bits'] == 32 and planes[i]['count'] == 2
                 and planes[i]['address'] in (0x98, 0x1C5)), len(planes))
    patches = []
    for plane in planes[first:last]:
        need(plane['cl'] == plane['wl'] == 1 and plane['mode'] == 0
             and not plane['command'] & 0x10, 'unsupported vehicle VIF state')
        values = []
        for i, vector in enumerate(plane['values']):
            if len(vector) == 1:
                vector = vector*4
            elif len(vector) == 2:
                vector = vector*2
            elif len(vector) == 3:
                following = plane['values'][i+1][0] if i+1 < len(plane['values']) else 0
                vector = (*vector, following)
            values.extend(x & 0xFFFFFFFF for x in vector)
        patches.append((plane['address']*16, struct.pack('<'+'I'*len(values), *values)))
    return header['address'], patches


def reference_jobs(executable, source_paths):
    """Rederive jobs from original ELF plus exact retained main vehicle PCKs."""
    proof = source_contract(executable)
    jobs = []
    for probe in proof['probes']:
        path = Path(source_paths[probe['car']])
        raw = path.read_bytes()
        need(len(raw) == probe['source_bytes'] and hashlib.sha256(raw).hexdigest()
             == probe['source_sha256'], 'vehicle draw PCK changed')
        vehicle, pck = read_vehicle(path), Pck(raw)
        material = probe['material_index']
        offset = vehicle['materials'][material]['offset']
        need(pck.u32(offset+4) & 127 == probe['material_class']
             and raw[offset+12] == probe['source_pass_program_index'], 'vehicle source material changed')
        part = next(p for p in vehicle['lods']['high'] if p['name'] == probe['source_part']
                    and p['bone'] == probe['source_bone'] and p['mesh']
                    and any(d['material'] == material for d in p['mesh']['draws']))
        draw = next(d for d in part['mesh']['draws'] if d['material'] == material)
        need(draw['packet_offset'] == probe['packet_offset'], 'vehicle source draw changed')
        packet = raw[draw['packet_offset']:draw['packet_offset']+draw['packet_bytes']]
        need(hashlib.sha256(packet).hexdigest() == probe['packet_sha256'], 'vehicle VIF packet changed')
        source = proof['programs'][probe['program']]
        pairs = unpack_microprogram(_read_elf(executable, source['address'], source['bytes']))
        micro, memory = bytearray(16384), bytearray(16384)
        for pc, pair in pairs.items():
            struct.pack_into('<II', micro, pc*8, *pair)
        for row in proof['uniform_words']:
            struct.pack_into('<'+'I'*len(row['words']), memory, row['slot']*16, *row['words'])
        memory[35*16:40*16] = _read_elf(executable, 0x613F1C, 80)
        memory[44*16:48*16] = _read_elf(executable, 0x613F70, 64)
        # Explicit state overwrites ALPHA slots within the source template block.
        for slot in (45, 47):
            struct.pack_into('<4I', memory, slot*16, 0x58, 0, 0x1B, 0)
        calls = [{'pc': 10, 'top': 0, 'itop': 0}]
        for batch in draw['batches'][:2]:
            origin, patches = batch_patches(packet, batch['packet_offset']-draw['packet_offset'])
            calls.append({'pc': 6, 'top': 0, 'itop': origin, 'patches': patches})
        job = encode_job(micro, memory, calls)
        need(hashlib.sha256(job).hexdigest() == probe['job_sha256'], 'vehicle whole-program job changed')
        jobs.append({'name': probe['program'], 'job': job, 'probe': probe})
    return jobs


def verify_reference_output(directory, probe):
    """Compare literal native transport, final memory/registers and call cycles."""
    directory = Path(directory)
    receipt = json.loads((directory/'receipt.json').read_text())
    need(receipt['job_sha256'] == probe['job_sha256'] and receipt['status'] == 'executed'
         and receipt['runtime']['binary_sha256'] == probe['runtime_binary_sha256']
         and receipt['adapter_sha256'] == probe['adapter_sha256'], 'vehicle draw runtime changed')
    for name, expected in probe['outputs'].items():
        raw = (directory/name).read_bytes()
        need(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'],
             'vehicle draw output changed: '+name)
    calls = json.loads((directory/'calls.json').read_text())
    need(calls == probe['calls'], 'vehicle draw call/cycle boundaries changed')
    return receipt


def execute_reference(executable, source_paths, output, runner=None):
    from mc3_reference_runtime import run_job
    runner = run_job if runner is None else runner
    output = Path(output)
    need(not output.exists(), 'choose a fresh vehicle whole-program output directory')
    output.mkdir(parents=True)
    results = []
    for row in reference_jobs(executable, source_paths):
        path, directory = output/(row['name']+'.job'), output/row['name']
        path.write_bytes(row['job'])
        runner(path, directory)
        receipt = verify_reference_output(directory, row['probe'])
        results.append({'program': row['name'], 'execution': receipt})
    (output/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    return results
