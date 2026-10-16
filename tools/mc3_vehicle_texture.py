"""Source-bound native texture inputs, separate from inspection PNG conversion."""

import hashlib
import json
from pathlib import Path
import struct

from mc3_textures import SLOT_CLASS


EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/vehicle-texture-native.json')
PROOF_SHA = '68e08c1a0114af973dbe0c56350a664ead1ae66ed61b08ba3fe16277dc4a92cd'
FRAGMENT_SHA = 'ccd688571ff859f6cbcdf39311d68c415689cb3d8e0cd891131779bd319aadec'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    encoded = json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()
    need(hashlib.sha256(encoded).hexdigest() == PROOF_SHA, 'vehicle texture receipt changed')
    return proof


def fragment_fixture():
    raw = EVIDENCE.with_name('vehicle-texture-fragments.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest() == FRAGMENT_SHA, 'vehicle texture fragments changed')
    return json.loads(raw)


def verify_fragment_source(data):
    fixture = fragment_fixture()['window']
    need(len(data) == fixture['source_bytes'] and hashlib.sha256(data).hexdigest() == fixture['sha256'],
         'inline window source identity changed')
    for span in fixture['fragments']:
        raw = bytes.fromhex(span['hex'])
        need(data[span['offset']:span['offset'] + len(raw)] == raw, 'inline window source fragment changed')
    decoded = native_pck4_window(data, fixture['slot'])
    need(hashlib.sha256(decoded['levels'][0]['rgba']).hexdigest() == fixture['expected_rgba_sha256'],
         'inline window source decoded pixels changed')
    return {'source_fragments': len(fixture['fragments']), 'native_rgba_pixels': 64}


def from_executable(executable):
    """Rebind the format dispatch, alpha conversion and GS upload proof."""
    from mc3_environment_raster import _read_elf
    proof = source_contract()
    need(hashlib.sha256(executable).hexdigest() == proof['source_executable_sha256'],
         'vehicle texture executable identity changed')
    for pin in proof['intervals'].values():
        actual = _read_elf(executable, pin['start'], pin['end'] - pin['start'])
        need(hashlib.sha256(actual).hexdigest() == pin['sha256'], 'vehicle texture source interval changed')
    for address, value in proof['selected_words'].items():
        actual = struct.unpack('<I', _read_elf(executable, int(address, 16), 4))[0]
        need(actual == value, 'vehicle texture source instruction changed')
    need(_read_elf(executable, 0x61C28C, 2) == b'\x01\x01'
         and _read_elf(executable, 0x61C294, 1) == b'\x80', 'vehicle texture loader defaults changed')
    return proof['contract']


def native_shared_format(kind):
    """Original boot/default indexed .tex loader profile, not its fallback modes."""
    formats = source_contract()['contract']['shared_formats']
    need(type(kind) is int and str(kind) in formats, 'unsupported native shared texture format')
    return {**formats[str(kind)], 'palette_order': 'BGRA', 'alpha_conversion': 'floor(A*128/255)',
            'tcc': 1, 'cpsm': 0}


def palette_reference_job(palette):
    """Run original524878 with an original buffered-stream object, without stubs.

    The explicit stream has all bytes buffered, so native399658/3993a8 read
    them without opening a file or invoking an external backend callback.
    Native arithmetic and source byte-reading instructions remain unmodified.
    """
    from mc3_environment_raster import encode_ee_job
    need(isinstance(palette, bytes) and 0 < len(palette) <= 1024 and len(palette) % 4 == 0,
         'invalid reference palette extent')
    file_pointer, source_pointer, output_pointer = 0x1000000, 0x1001000, 0x1002000
    stream = struct.pack('<8I', 0, 0, source_pointer, 0, 0, len(palette), len(palette), 0)
    return encode_ee_job(0x524878, {4: file_pointer, 5: output_pointer, 6: len(palette) // 4},
                         [(file_pointer, stream), (source_pointer, palette)])


def native_pck4_window(data, slot, profile_delta=0, to_offset=None):
    """Decode the measured one-level 8x8 PSMT4/CLUT32 inline-window profile.

    These are already native GS upload bytes. Palette alpha is copied exactly;
    .tex file-loader alpha conversion and PNG display scaling do not apply.
    Other PPF/image layouts remain outside this intentionally bounded decoder.
    """
    source_contract()
    need(isinstance(data, bytes) and len(data) >= 128, 'invalid inline window carrier')
    base = struct.unpack_from('<I', data)[0]
    pointer = to_offset or (lambda value: value - base + 128)

    def bounds(offset, size):
        need(type(offset) is int and 0 <= offset <= offset + size <= len(data),
             'inline window read outside carrier')
        return offset

    def word(offset):
        return struct.unpack_from('<I', data, bounds(offset, 4))[0]

    bounds(slot, 0xA0)
    need(word(slot) == SLOT_CLASS + profile_delta, 'unknown inline window class')
    tex0 = struct.unpack_from('<Q', data, slot + 0x10)[0]
    need((tex0 >> 20) & 63 == 20 and (tex0 >> 51) & 15 == 0
         and (tex0 >> 55) & 1 == 0 and (tex0 >> 56) & 31 == 0
         and (tex0 >> 34) & 1 == 1 and (tex0 >> 35) & 3 == 0,
         'unsupported inline window TEX0 profile')
    width, height = 1 << ((tex0 >> 26) & 15), 1 << ((tex0 >> 30) & 15)
    need((width, height) == (8, 8) and data[slot + 0x86] == 1,
         'unsupported inline window dimensions or mip count')
    palette_offset = struct.unpack_from('<H', data, slot + 0x80)[0] * 16
    need(palette_offset == 32 and struct.unpack_from('<HH', data, slot + 12) == (1, 2),
         'inline window upload extent changed')
    descriptor = bounds(pointer(word(slot + 0x48)), 0x90)
    need(data[descriptor + 0x1C:descriptor + 0x90] == b'\xCD' * 0x74,
         'unsupported inline window upload descriptor')
    start = bounds(descriptor + 0x90, 112)
    need(data[start + 96:start + 112] == b'\xCD' * 16, 'inline window payload extent changed')
    packed = data[start:start + 32]
    palette = data[start + 32:start + 96]
    indices = bytes(index for value in packed for index in (value & 15, value >> 4))
    rgba = b''.join(palette[index * 4:index * 4 + 4] for index in indices)
    tex1 = struct.unpack_from('<Q', data, slot + 0x88)[0]
    clamp = data[slot + 0x85]
    need((tex1 >> 5) & 1 == 1 and (tex1 >> 6) & 7 == 4 and clamp in (0, 5),
         'unsupported inline window sampler')
    return {'decode_status': 'decoded', 'levels': [
                {'width': 8, 'height': 8, 'rgba': rgba, 'source_indices': packed, 'source_offset': start}],
            'source_palette': palette, 'source_slot': data[slot:slot + 0xA0],
            'source_descriptor': data[descriptor:descriptor + 0x90],
            'palette_order': 'RGBA', 'alpha_conversion': 'original palette byte',
            'source_slot_offset': slot, 'tex0': f'0x{tex0:016x}', 'tex1': f'0x{tex1:016x}', 'clamp': clamp,
            'claim_limits': ['One measured 8x8 PSMT4/CLUT32 mip profile; no alternate upload layout is inferred.']}
