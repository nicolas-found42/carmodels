"""Regenerate bounded original EE material-binder reference jobs.

The wrapper only calls the unchanged original entry and copies scratch RGBA to
RAM. Numerical instructions remain original. Empty texture/stage state isolates
binder arithmetic; this is not a complete vehicle draw.
"""
import hashlib
import json
from pathlib import Path
import struct


EVIDENCE = Path(__file__).resolve().parents[1] / 'research/evidence/midnight-club-3-remix/previews/vehicle-bindings-native.json'
PROOF_SHA = 'a92510044101166c4ef89e4648d425b65c36660c081793f12e8a68222524ad1b'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    digest = hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    need(digest == PROOF_SHA, 'vehicle binder receipt changed')
    return proof


def from_executable(executable):
    from mc3_environment_raster import _read_elf
    proof = source_contract()
    need(hashlib.sha256(executable).hexdigest() == proof['source_executable_sha256'],
         'vehicle binder executable identity changed')
    for row in proof['intervals'].values():
        data = _read_elf(executable, row['start'], row['end'] - row['start'])
        need(hashlib.sha256(data).hexdigest() == row['sha256'], 'vehicle binder source interval changed')
    for address, words in proof['globals'].items():
        need(_read_elf(executable, int(address), len(words) * 4) == struct.pack('<' + str(len(words)) + 'I', *words),
             'vehicle binder source global changed')
    need(_read_elf(executable, 0x616313, 1)[0] == proof['paint_control_byte'],
         'vehicle paint source control byte changed')
    return proof


def reference_jobs(executable, pck):
    """Bind original code/source fields and reproduce the five executed jobs."""
    proof = from_executable(executable)
    need(len(pck) == proof['source_pck_bytes'] and hashlib.sha256(pck).hexdigest() == proof['source_pck_sha256'],
         'vehicle binder PCK identity changed')
    jobs = []
    for probe in proof['executed_probes']:
        offset = probe['source_node_offset']
        source = pck[offset:offset + 128]
        need(hashlib.sha256(source).hexdigest() == probe['source_node_sha256'],
             'vehicle binder source material changed')
        material = bytearray(source)
        material[8:48] = bytes(40)
        parameters = bytes.fromhex(probe['material_parameters_hex'])
        need(len(parameters) == 80, 'vehicle binder parameter carrier changed')
        material[48:] = parameters
        words = probe['input_words']
        spad = bytearray(16384)
        struct.pack_into('<2I', spad, 0x5AC, 0x1006000, 0x1009000)
        wrapper = 0x100A000
        code = struct.pack('<10I', 0x0C000000 | (probe['entry'] >> 2), 0, 0x3C087000,
                           0x8D020080, 0x3C090100, 0xAD222000, 0x3C1F0001, 0x03E00008, 0, 0)
        patches = [(wrapper, code), (0x1000000, bytes(material)),
                   (0x1001000, struct.pack('<' + str(len(words)) + 'I', *words)),
                   (0x70000000, bytes(spad)), (0x6BE570, struct.pack('<3f', .2, .3, .4))]
        data = bytearray(b'MC3EE001') + struct.pack('<5I', wrapper, 100000, 4, 0, len(patches))
        for register, value in {4: 0x1000000, 5: 0x1001000, 6: 0, 7: 0}.items():
            data += struct.pack('<I4I', register, value, 0, 0, 0)
        for address, raw in patches:
            data += struct.pack('<2I', address, len(raw)) + raw
        need(hashlib.sha256(data).hexdigest() == probe['job_sha256'], 'vehicle binder reference job changed')
        jobs.append({'name': probe['name'], 'job': bytes(data), 'probe': probe})
    return jobs


def decode_reference_output(ram):
    need(type(ram) is bytes and 0x1008000 <= len(ram) <= 32 * 1024 * 1024,
         'vehicle binder output RAM extent changed')
    uniforms = {}
    for offset in range(0x1006000, 0x1008000, 16):
        tag = struct.unpack_from('<4I', ram, offset)
        if (tag[0] & 0xFFFF0000 == 0x10000000 and tag[1] == 0 and
                tag[2] in (0, 0x11000000) and tag[3] >> 24 == 0x6C):
            count, address = (tag[3] >> 16) & 255, tag[3] & 1023
            need(offset + 16 + count * 16 <= len(ram), 'vehicle binder VIF output outside RAM')
            for index in range(count):
                if address + index in (31, 40, 52, 53):
                    uniforms[str(address + index)] = list(struct.unpack_from('<4I', ram, offset + 16 + index * 16))
    return {'rgba': list(ram[0x1002000:0x1002004]), 'uniform_words': uniforms}


def verify_reference_output(ram, probe):
    actual = decode_reference_output(ram)
    need(actual['rgba'] == probe['rgba'], 'vehicle binder native RGBA differs')
    need(actual['uniform_words'] == probe['uniform_words'], 'vehicle binder native uniforms differ')
    return actual
