"""Original source material relocation, camera, binder and raw mesh draw.

This bounded control uses original350Z coloredglass and its inline window image.
Caller camera/light/frame/pass-limit inputs are explicit. It does not select an
actor's stock parts or claim a full vehicle render.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf, encode_ee_job
from mc3_pck import Pck
from mc3_vehicle_inputs import native_material_inputs
from mc3_vehicle_uniforms import caller as uniform_caller
from mc3_vehicle_programs import native_registry
from mc3_specular_native import EXECUTABLE_SHA

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT/'research/evidence/midnight-club-3-remix/previews/vehicle-authored-draw.json'
PROOF_SHA = 'b3718697bc62c621a064660e4f30e0ab558eba5b9e9e5c89087397b71afa48b7'
CODE, MANAGER, FIXUP, ARRAY, PARAMS, RESULT, SOURCE = (
    0x100c000, 0x100d000, 0x100e000, 0x100f000, 0x1010000, 0x1011000, 0x1400000)
DMA, DMA_END = 0x1100000, 0x1180000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(PROOF.read_text()) if receipt is None else receipt
    need(sha(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()) == PROOF_SHA,
         'authored draw receipt differs')
    return proof


def from_executable(executable):
    need(sha(executable) == EXECUTABLE_SHA, 'authored draw executable differs')
    proof = source_contract()
    for row in proof['intervals']:
        need(sha(_read_elf(executable, row['start'], row['end']-row['start'])) == row['sha256'],
             'authored draw original interval differs')
    return proof


def _li(words, register, value):
    words.extend([0x3c000000 | register << 16 | value >> 16,
                  0x34000000 | register << 21 | register << 16 | value & 65535])


def caller(executable, source, context, pass_limit):
    proof = from_executable(executable)
    need(type(source) is bytes and sha(source) == proof['source']['sha256']
         and len(source) == proof['source']['bytes'], 'authored draw source differs')
    need(type(pass_limit) is int and pass_limit in (0, 1), 'authored draw pass limit differs')
    q = Pck(source)
    material, mesh_offset, draw_index = (proof['source'][key] for key in
                                         ('material_offset', 'mesh_offset', 'draw_index'))
    collection = proof['source']['collection_offset']
    data = bytearray(source)
    need(source[mesh_offset+4] == 0 and q.u32(material+4) & 127 == 14,
         'authored source unskinned material class differs')
    struct.pack_into('<I', data, mesh_offset, 0x626d98)
    count = q.u16(mesh_offset+8)
    need(0 <= draw_index < count, 'authored source mesh draw differs')
    table = q.pointer(q.u32(mesh_offset+16), count*8)
    struct.pack_into('<I', data, mesh_offset+16, SOURCE+table)
    for i in range(count):
        descriptor = q.pointer(q.u32(table+i*8), 8)
        packet, qwc, _ = struct.unpack_from('<IHH', source, descriptor)
        packet = q.pointer(packet, qwc*16)
        struct.pack_into('<I', data, table+i*8, SOURCE+descriptor)
        struct.pack_into('<I', data, descriptor, SOURCE+packet)
    # Camera, frame and light math are original routines from the accepted
    # explicit uniform helper. The combined caller preserves its literal DMA.
    uniforms = uniform_caller(context)
    words = list(struct.unpack('<'+'I'*(len(uniforms[0][1])//4), uniforms[0][1]))[:-2]
    _li(words, 4, MANAGER)
    words += [0x0c000000 | 0x2b9b40 >> 2, 0]
    _li(words, 8, 0x70e56c)
    words.append(0xad020000)
    for r, value in [(4, 0), (5, FIXUP), (6, ARRAY), (7, 1)]:
        _li(words, r, value)
    words += [0x0c000000 | 0x3b4800 >> 2, 0]
    _li(words, 8, 0x70000000)
    _li(words, 9, DMA_END)
    words.append(0xad0905b0)
    _li(words, 9, 2)
    words.append(0xad090114)
    for r, value in [(4, SOURCE+material), (5, SOURCE+mesh_offset),
                     (6, PARAMS), (7, draw_index), (8, 0)]:
        _li(words, r, value)
    words += [0x0c000000 | 0x3b76e0 >> 2, 0]
    _li(words, 8, 0x70000000)
    words.append(0x8d0905ac)
    _li(words, 8, RESULT)
    words += [0xad090000, 0x02e00008, 0]
    inputs = native_material_inputs(source, collection)
    program = next(row for row in native_registry(executable) if row['index'] == source[material+12])
    need(program['index'] == 2, 'authored source compiled program differs')
    patches = uniforms[1:]+[(CODE, struct.pack('<'+'I'*len(words), *words)),
        (MANAGER, bytes(4)), (FIXUP, struct.pack('<2I', 0, (SOURCE-q.base+128) & 0xffffffff)),
        (ARRAY, struct.pack('<I', q.base+material-128)), (SOURCE, data),
        (PARAMS, struct.pack('<'+'I'*len(inputs), *(row['word'] for row in inputs))),
        (0x615e50, struct.pack('<I', pass_limit)), (0x6be810, bytes(4)),
        (0x70fbe4, struct.pack('<4I', 0, 0x4000, 0x100, 0x100)),
        (0x70fa70+program['index']*4, struct.pack('<I', program['address']))]
    return patches


def reference_job(executable, source, context, pass_limit):
    return encode_ee_job(CODE, {}, caller(executable, source, context, pass_limit))


def flatten_dma(ram):
    need(len(ram) == 0x2000000, 'authored draw RAM extent differs')
    end = struct.unpack_from('<I', ram, RESULT)[0]
    need(DMA <= end <= DMA_END and end % 16 == 0, 'authored draw DMA end differs')
    offset, stream, refs = DMA, bytearray(), []
    while offset < end:
        tag, pointer, _, _ = struct.unpack_from('<4I', ram, offset)
        count, kind = tag & 65535, tag >> 28 & 7
        need(kind in (1, 3), 'authored draw unsupported DMA kind')
        size = count*16
        at = offset+16 if kind == 1 else pointer
        need(0 <= at <= at+size <= len(ram), 'authored draw DMA source outside RAM')
        need(kind != 1 or at+size <= end, 'authored draw inline DMA exceeds end')
        stream += ram[offset+8:offset+16]+ram[at:at+size]
        refs.append({'kind': kind, 'address': at, 'bytes': size, 'sha256': sha(ram[at:at+size])})
        offset += 16+(size if kind == 1 else 0)
    return bytes(stream), {'dma_bytes': end-DMA, 'dma_sha256': sha(ram[DMA:end]), 'refs': refs}


def coupled_job(executable, ram):
    from mc3_vehicle_transfer_reference import encode_job
    from_executable(executable)
    stream, binding = flatten_dma(ram)
    # Exact original526d08 special descriptor order; these source streams
    # initialize GIF tag templates/constants, followed by the source normalbank.
    prefix = _read_elf(executable, 0x612010, 0x613fb0-0x612010)
    prefix += _read_elf(executable, 0x610a60, 0x612010-0x610a60)
    bank = _read_elf(executable, 0x5ec4f0, 13488)
    prefix += bank[8:]
    stream = prefix+stream+struct.pack('<4I', 0x10000000, 0, 0, 0)
    return encode_job(bytes(16384), bytes(16384), stream), binding


def execute_reference(executable, source, directory, ee_runner=None, coupled_runner=None):
    from mc3_reference_runtime import run_job
    from mc3_vehicle_transfer_reference import run_job as run_coupled
    ee_runner, coupled_runner = ee_runner or run_job, coupled_runner or run_coupled
    executable, source, directory = Path(executable), Path(source), Path(directory)
    original, raw = executable.read_bytes(), source.read_bytes()
    proof = from_executable(original)
    need(not directory.exists(), 'choose a fresh authored draw directory')
    directory.mkdir(parents=True)
    results = []
    for case in proof['cases']:
        job = reference_job(original, raw, case['context'], case['pass_limit'])
        need(sha(job) == case['ee_job_sha256'], 'authored draw EE inputs differ')
        folder = directory/case['name']
        folder.mkdir()
        path = folder/'input.job'
        path.write_bytes(job)
        ee = ee_runner(path, folder/'ee', mode='ee', executable=executable)
        ram = (folder/'ee/ee-ram.bin').read_bytes()
        need(sha(ram) == case['ee_ram_sha256'], 'authored draw original EE output differs')
        job, binding = coupled_job(original, ram)
        need(binding == case['dma'], 'authored draw original DMA differs')
        native = coupled_runner(job, folder/'coupled')
        need({key: value for key, value in native.items() if key != 'profile'} == case['coupled'],
             'authored draw original coupled output differs')
        results.append({'name': case['name'], 'ee': ee, 'coupled': native})
    (directory/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    return results
