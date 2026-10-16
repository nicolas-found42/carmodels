"""Source raw VIF -> unchanged official VIF dispatcher/VU -> GIF oracle.

Inputs use the explicit controlled uniform context from vehicle-draw-reference;
raw source packets now replace its historical reconstructed vertex-plane patches.
Cross-program controls do not claim authored material dispatch or gameplay state.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import uuid

from mc3_reference_runtime import (ROOT, DEFAULT_IMAGE, BINARY_SHA, Cursor, identity,
                                   contract as runtime_contract)
from mc3_vehicle_draw_reference import source_contract, _read_elf, unpack_microprogram
from mc3_pck import read_vehicle

ADAPTER = ROOT/'tools/reference-runtime/mc3_transfer_reference.cpp'
EVIDENCE = ROOT/'research/evidence/midnight-club-3-remix/previews/vehicle-transfer-reference.json'
RECEIPT_SHA = '50d72f622b107c24475db91b0d2063b7af9ba23f846e0da0dc9b84f8cd1bbe9d'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode_job(micro, memory, stream):
    vif, regs = bytes(144), bytearray(384)
    regs[64:66] = bytes((1, 1))
    job = b'MC3CV001'+micro+memory+vif+regs+struct.pack('<I', len(stream))+stream
    validate_job(job)
    return job


def validate_job(data):
    cur = Cursor(data)
    if cur.take(8) != b'MC3CV001':
        raise ValueError('coupled reference magic differs')
    cur.take(32768)
    vif, regs = cur.take(144), cur.take(384)
    if any(vif) or regs[:64] != bytes(64) or regs[64:66] != bytes((1, 1)) or any(regs[66:]):
        raise ValueError('coupled reference initial VIF context differs')
    size = cur.u32()
    if not 4 <= size <= 10485760 or size % 4:
        raise ValueError('coupled reference transfer size differs')
    cur.take(size)
    if cur.offset != len(data):
        raise ValueError('coupled reference has trailing data')


def source_jobs(executable, source_paths):
    proof = source_contract(executable)
    jobs = []
    for probe in proof['probes']:
        path = Path(source_paths[probe['car']])
        raw = path.read_bytes()
        if sha(raw) != probe['source_sha256']:
            raise ValueError('coupled source vehicle differs')
        vehicle = read_vehicle(path)
        draw = next(draw for part in vehicle['lods']['high'] if part['mesh']
                    for draw in part['mesh']['draws'] if draw['packet_offset'] == probe['packet_offset'])
        packet = raw[draw['packet_offset']:draw['packet_offset']+draw['packet_bytes']]
        if sha(packet) != probe['packet_sha256']:
            raise ValueError('coupled source VIF differs')
        program = proof['programs'][probe['program']]
        pairs = unpack_microprogram(_read_elf(executable, program['address'], program['bytes']))
        micro, memory = bytearray(16384), bytearray(16384)
        for pc, pair in pairs.items():
            struct.pack_into('<II', micro, pc*8, *pair)
        for row in proof['uniform_words']:
            struct.pack_into('<'+'I'*len(row['words']), memory, row['slot']*16, *row['words'])
        memory[35*16:40*16] = _read_elf(executable, 0x613F1C, 80)
        memory[44*16:48*16] = _read_elf(executable, 0x613F70, 64)
        for slot in (45, 47):
            struct.pack_into('<4I', memory, slot*16, 0x58, 0, 0x1B, 0)
        # Original caller prelude plus explicit drained transfer boundaries.
        # A whole-QW prefix preserves every original packet alignment.
        stream = struct.pack('<8I', 0, 0, 0, 0x1400000A, 0x10000000, 0, 0, 0)+packet
        stream += struct.pack('<4I', 0x10000000, 0, 0, 0)
        job = encode_job(micro, memory, stream)
        jobs.append(dict(name=probe['program'], job=job, source=dict(
            car=probe['car'], source_sha256=probe['source_sha256'],
            packet_offset=probe['packet_offset'], packet_bytes=len(packet),
            packet_sha256=sha(packet), program_packet_sha256=program['sha256'],
            program_index=program['index'], source_material_index=probe['material_index'],
            source_material_program_index=probe['source_pass_program_index'],
            initial_memory_sha256=sha(memory), microcode_sha256=sha(micro),
            stream_sha256=sha(stream), job_sha256=sha(job))))
    return jobs


def run_job(job, output, image=DEFAULT_IMAGE):
    validate_job(job)
    profile = identity(image)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output/'input.job').write_bytes(job)
    name = 'mc3-transfer-'+uuid.uuid4().hex
    args = ['docker', 'run', '--rm', '--name', name, '--network=none',
            '--platform', 'linux/amd64', '--entrypoint', '/bin/bash',
            '-v', f'{ROOT}:/repo:ro', '-v', f'{output}:/work', image]
    script = ('g++ -O2 -shared -fPIC /repo/tools/reference-runtime/mc3_transfer_reference.cpp -ldl -o /work/adapter.so && '
              'MC3_COUPLED_JOB=/work/input.job MC3_COUPLED_OUT=/work LD_PRELOAD=/work/adapter.so /opt/squashfs-root/AppRun')
    try:
        result = subprocess.run(args+['-c', script], capture_output=True, text=True, timeout=120)
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, check=False)
    (output/'execution.log').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError('coupled original reference execution failed: '+result.stderr[-2000:])
    raw = (output/'gif-chunks.bin').read_bytes()
    cur, chunks = Cursor(raw), []
    while cur.offset < len(raw):
        chunks.append(cur.take(cur.u32()))
    memory = (output/'final-vumem.bin').read_bytes()
    regs = (output/'final-vuregs.bin').read_bytes()
    if len(memory) != 16384 or len(regs) != 1680:
        raise ValueError('coupled native result size differs')
    receipt = dict(profile=profile, adapter_sha256=sha(ADAPTER.read_bytes()),
                   base_adapter_sha256=runtime_contract()['adapter_source_sha256'],
                   job_sha256=sha(job), gif_bytes=sum(map(len, chunks)),
                   gif_sha256=sha(b''.join(chunks)), transport_sha256=sha(raw),
                   memory_sha256=sha(memory), vf_sha256=sha(regs[:512]))
    (output/'execution.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt



def contract():
    raw = EVIDENCE.read_bytes()
    if sha(raw) != RECEIPT_SHA:
        raise ValueError('coupled reference receipt differs')
    proof = json.loads(raw)
    if (proof['adapter_sha256'] != sha(ADAPTER.read_bytes())
            or proof['base_adapter_sha256'] != runtime_contract()['adapter_source_sha256']):
        raise ValueError('coupled reference adapter differs')
    return proof


def execute_reference(executable, source_paths, output):
    proof = contract()
    jobs = source_jobs(executable, source_paths)
    if [row['source'] for row in jobs] != [row['source'] for row in proof['probes']]:
        raise ValueError('coupled reference source bindings differ')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    receipts = []
    for item, probe in zip(jobs, proof['probes']):
        result = run_job(item['job'], output/item['name'])
        if {key: result[key] for key in probe['expected']} != probe['expected']:
            raise ValueError('coupled original execution differs: '+item['name'])
        receipts.append(result)
    return receipts


def synthetic_job():
    """Self-authored minimal transfer control, explicitly not a game packet."""
    micro = bytearray(16384)
    struct.pack_into('<4I', micro, 0, 0x8000033C, 0x400002FF, 0x8000033C, 0x000002FF)
    stream = struct.pack('<8I', 0x6C010010, 1, 2, 3, 4, 0x14000000, 0x10000000, 0)
    return encode_job(micro, bytes(16384), stream)



def transfer_symbols(data):
    if sha(data) != BINARY_SHA:
        raise ValueError('coupled reference binary identity differs')
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count = struct.unpack_from('<HH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*width) for i in range(count)]
    names = {'_Z12VIF1transferPjib', '_Z15vifTransferLoopILi1EEvRPj'}
    result = {}
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        table = data[strings[4]:strings[4]+strings[5]]
        for start in range(section[4], section[4]+section[5], section[9]):
            name, _, _, index, address, size = struct.unpack_from('<IBBHQQ', data, start)
            name = table[name:table.index(b'\0', name)].decode()
            if name not in names:
                continue
            segment = sections[index]
            source = segment[4]+address-segment[3]
            result[name] = dict(address=hex(address), bytes=size,
                                instruction_sha256=sha(data[source:source+size]))
    if result.keys() != names:
        raise ValueError('coupled reference transfer symbols missing')
    return result


def from_binary(data):
    proof = contract()
    if transfer_symbols(data) != proof['native_transfer_symbols']:
        raise ValueError('coupled reference source symbols differ')
    return proof
