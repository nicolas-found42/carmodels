"""Recover the authored San Diego midnight garage inputs for native specular capture.

The browser translates the recovered draw/sampling pipeline. This producer retains
all selected prop triangles, so the rasterizer can reject newly visible materials.
"""
import argparse
import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from mc3_archive import CookedDisc, DaveArchive, file_digest
from mc3_environment_sky import decode_sky
from mc3_garage import decode_garage, decode_native_shared_tex, read_mesh
from mc3_model import rotated_point
from mc3_pck import Pck, strip_indices
from static_inputs import mc3_disc

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dealership/public/midnight-club-3-remix/environment/native-garage.json'
ISO_SHA = 'de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9'
NATIVE_CAPTURE = ROOT / 'research/evidence/midnight-club-3-remix/previews/environment/native-gs-executed.json'
NATIVE_CAPTURE_SHA = '4d379597b40050d3d27c6e1801eac273468b06d72b7338470efd221aabaf228e'


def flatten(rows):
    return [value for row in rows for value in row]


def capture_input_sha256(pack):
    """Bind emitted native packets to lossless inputs, excluding host geometry.

    The legacy normalized positions are deliberately outside this boundary:
    the native execution consumes the retained VIF bytes and source transforms.
    Image hashes bind the independently decoded native texture inputs.
    """
    inputs = {key: pack[key] for key in
              ('source', 'camera', 'car_heading', 'native_input_schema', 'native_packets')}
    inputs['draws'] = [{key: draw[key] for key in ('material_index', 'native')}
                       for draw in pack['draws']]
    inputs['sky'] = {'draws': [{key: draw[key] for key in ('image', 'native')}
                              for draw in pack['sky']['draws']],
                     'native_initial_state': pack['sky']['native_initial_state']}
    inputs['images'] = {key: value['rgba_sha256'] for key, value in pack['images'].items()}
    inputs['sky']['images'] = {key: value['rgba_sha256']
                               for key, value in pack['sky']['images'].items()}
    raw = json.dumps(inputs, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def normalize_capture_fixture(result):
    """Keep deterministic execution evidence, excluding host paths/image IDs."""
    executions = []
    reference = None
    for item in result['executions']:
        receipt = item['receipt']
        current = {key: receipt['runtime'][key]
                   for key in ('binary_sha256', 'appimage_sha256', 'gs_simd_profile')}
        if reference is not None and reference != current:
            raise ValueError('native capture reference profile changed between jobs')
        reference = current
        executions.append({'name': item['name'], **{key: receipt[key] for key in
                           ('mode', 'job_sha256', 'original_mc3_executable_sha256',
                            'adapter_sha256', 'outputs')}})
    return {key: result[key] for key in ('schema', 'capture_input_sha256', 'native_gs',
                                       'visibility_controls', 'base_cull0_control', 'matrices')} | {
        'reference': reference, 'executions': executions,
        'claim_limits': [
            'Original MC3 EE helpers and VU programs executed in pinned official PCSX2 interpreters.',
            'Fixed original San Diego garage, 640x448 display-origin profile and unanimated source inputs.',
            'Hidden material shading is not reconstructed; both conservative geometry controls must cover no GS pixels.',
            'Software-reference evidence, not physical PS2 or complete booted-game frame equivalence.']}


def load_native_capture(pack, proof=None):
    """Join the executed GIF fixture only to its complete original input set."""
    from mc3_environment_raster import source_contract
    source_contract()
    proof = json.loads(NATIVE_CAPTURE.read_text()) if proof is None else proof
    encoded = json.dumps(proof, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != NATIVE_CAPTURE_SHA:
        raise ValueError('executed native capture fixture changed')
    if proof['schema'] != 1 or proof['capture_input_sha256'] != capture_input_sha256(pack):
        raise ValueError('executed native capture input binding differs')
    native = copy.deepcopy(proof['native_gs'])
    if native['context'] != {'xy_offset': [27648, 29184], 'scissor': [0, 0, 256, 256],
                              'depth_format': 'PSMZ16S'}:
        raise ValueError('executed native capture context differs')

    def identity(draw):
        source = draw['native']
        return pack['native_packets'][source['packet']]['sha256'], source['batch_offset']

    expected = [(8, index, *identity(draw), None) for index in (0, 1)
                for draw in pack['draws'] if draw['material_index'] == 8]
    expected += [(-1, 0, *identity(draw), draw['image']) for draw in pack['sky']['draws']]
    actual = [(row['material_index'], row['pass_index'], row['source_packet_sha256'],
               row['batch_offset'], row.get('image')) for row in native['passes']]
    if actual != expected:
        raise ValueError('executed native capture source batch coverage differs')
    hidden = [(index, draw['material_index'], *identity(draw))
              for index, draw in enumerate(pack['draws']) if draw['material_index'] != 8]
    if set(proof['visibility_controls']) != {'0', '192'}:
        raise ValueError('native hidden geometry controls are incomplete')
    for records in proof['visibility_controls'].values():
        actual = [(row['draw_index'], row['material_index'], row['source_packet_sha256'],
                   row['batch_offset']) for row in records]
        if actual != hidden:
            raise ValueError('native hidden geometry source coverage differs')
    for row in [*native['passes'], *[r for records in proof['visibility_controls'].values() for r in records]]:
        for chunk in row['gif_chunks']:
            if len(base64.b64decode(chunk, validate=True)) % 16:
                raise ValueError('invalid executed native GIF chunk extent')
    for row in native['passes']:
        row['stage'] = 'sky' if row['material_index'] == -1 else 'model'
        if row['stage'] == 'model':
            row['image'] = 'floorLightmap' if row['pass_index'] else 'floorBase'
    native['visibility_controls'] = copy.deepcopy(proof['visibility_controls'])
    return native


def native_batch(source, draw, batch, data, packets, *, translation, euler):
    """Retain the original VIF carrier and local lanes before host transformation.

    In particular UV.X includes a native ADC bit: it must not be rounded,
    cleared or reconstructed from normalized normals during VU reproduction.
    This is source retention, not a claim to have executed the VU program.
    """
    start, length = draw['packet_offset'], draw['packet_bytes']
    if not 0 <= start < start + length <= len(data):
        raise ValueError('native environment packet outside source')
    relative = batch['packet_offset'] - start
    if not 0 <= relative < length:
        raise ValueError('native environment batch outside packet')
    key = source + ':' + str(start)
    raw = data[start:start + length]
    record = {'source': source, 'offset': start, 'bytes': length,
              'sha256': hashlib.sha256(raw).hexdigest(),
              'data_base64': base64.b64encode(raw).decode()}
    if key in packets and packets[key] != record:
        raise ValueError('native environment packet identity collision')
    packets[key] = record
    return {'packet': key, 'batch_offset': relative,
            'header_words': batch['header_words'], 'position_scale': batch['scale'],
            'position_integers': batch['position_integers'],
            'uv_integers': batch['uv_integers'],
            'normal_integers': batch['normal_integers'],
            'color_integers': batch['color_integers'], 'adc': batch['adc'],
            'world_layout': batch['world_layout'],
            'instance_translation': translation, 'instance_euler': euler}


def build_pack(city, props, panorama, settings):
    """Derive portable input data; no synthetic pixels or guessed material colors."""
    garage, sky = decode_garage(props), decode_sky(city)
    text = settings.decode('ascii')
    number = r'([-+\d.eE]+)(?=\s|$)'
    spot = re.search(r'\bCarSpotsd\s+' + r'\s+'.join([number]*3), text)
    angle = re.search(r'\bCarAnglesd\s+' + number, text)
    if not spot or not angle:
        raise ValueError('original garage car transform missing')
    position = [float(x) for x in spot.groups()]
    heading = float(angle.group(1))
    if not all(math.isfinite(x) for x in (*position, heading)):
        raise ValueError('nonfinite garage car transform')
    position = [struct.unpack('<f', struct.pack('<f', x))[0] for x in position]
    heading = struct.unpack('<f', struct.pack('<f', heading))[0]
    eye = [position[0], position[1] + 1, position[2]]
    draws, packets = [], {}
    for instance in garage['instances']:
        if not instance.get('reflection_masks') or not instance.get('mesh'):
            continue
        frame = instance['native_frame']
        for draw in instance['mesh']['draws']:
            if not garage['materials'][str(draw['material'])]['reflection_phase_selected']:
                continue
            for batch in draw['batches']:
                points = [[x + offset for x, offset in zip(
                    rotated_point(frame['rotation'], point), frame['translation'])]
                          for point in batch['positions']]
                draws.append({'material_index': draw['material'],
                              'positions': flatten(points), 'uv0': flatten(batch['uvs']),
                              'uv1': flatten(batch['lightmap_uvs']),
                              'indices': strip_indices(batch),
                              'native': native_batch('props', draw, batch, props, packets,
                                                     translation=instance['position_raw'],
                                                     euler=instance['rotation_raw'])})
    floor = garage['materials']['8']
    if floor['template'] != 'garage_lightmap_subtract_reflectingground' or len(floor['passes']) != 2:
        raise ValueError('native garage floor pass profile changed')
    bindings = [p['textures'][0] for p in floor['passes']]
    if [b['name'] for b in bindings] != ['s_gar_floor_01', 'floor']:
        raise ValueError('native garage floor texture ownership changed')
    sky_state = sky['native_initial_state']
    if sky_state != {'rotation_degrees': 0.0, 'translation_offset': (0.0, 0.0, 0.0), 'invert_y': True}:
        raise ValueError('unhandled animated sky initial transform')
    sky_draws = []
    sky_mesh = read_mesh(Pck(city), sky['mesh_offset'])
    original_sky_batches = [(draw, batch) for draw in sky_mesh['draws'] for batch in draw['batches']]
    if len(original_sky_batches) != len(sky['primitives']):
        raise ValueError('native sky source batch ownership differs')
    for primitive, (draw, batch) in zip(sky['primitives'], original_sky_batches):
        if batch['packet_offset'] != primitive['source_packet_offset']:
            raise ValueError('native sky source packet ownership differs')
        if any(list(color) != [110, 110, 110, 255] for color in primitive['colors_native']):
            raise ValueError('native sky constant vertex modulation changed')
        points = [[eye[0] + x, eye[1] - y, eye[2] + z]
                  for x, y, z in primitive['positions']]
        sky_draws.append({'image': str(primitive['texture']), 'positions': flatten(points),
                          'uv0': flatten(primitive['uvs']), 'indices': primitive['indices'],
                          'native': native_batch('city', draw, batch, city, packets,
                                                 translation=eye, euler=[0, 0, 0])})
    pack = {'schema': 1, 'environment': 'Original MC3 San Diego midnight clear garage',
            'source': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                       for name, data in [('city', city), ('props', props),
                                          ('panorama', panorama), ('garageShared', settings)]},
            'camera': {'eye': eye, 'right': [1, 0, 0], 'up': [0, 0, -1],
                       'backward': [0, 1, 0], 'fov': 100, 'near': .25, 'far': 1000},
            'car_heading': heading,
            'native_input_schema': 1, 'native_packets': packets,
            'draws': draws,
            'images': {'floorBase': garage['images'][bindings[0]['image']],
                       'floorLightmap': garage['images'][bindings[1]['image']],
                       'panorama': decode_native_shared_tex(panorama)},
            'sky': {'draws': sky_draws, 'images': sky['textures'],
                    'native_initial_state': sky_state},
            'claim_limits': [
                'Original static garage inputs; no active vehicle/headlight reflection FX actors.',
                'Original EE/VU execution supplies emitted vertices; raster precision targets pinned official PCSX2 v2.8.2 AVX2/FMA software GS.',
                'Capture is fixed at the authored SD garage car position; unsupported visible materials fail explicitly.',
                'Physical PS2 output and a complete booted-game runtime frame are not asserted.']}
    pack['native_gs'] = load_native_capture(pack)
    return pack


def from_archive(archive):
    names = ['resources/city/sd_midnight_clear.pck',
             'resources/prop/sd_midnight_clear_garage_props.pck',
             'texture/fx_static_envmap_garage.tex', 'tune/garage/garage.garageshared']
    inputs = []
    for name in names:
        rows = [row for row in archive.records if row['name'] == name]
        if len(rows) != 1:
            raise ValueError('missing or ambiguous native environment input: ' + name)
        inputs.append(archive.payload(rows[0]))
    return build_pack(*inputs)


def encode(pack):
    return (json.dumps(pack, separators=(',', ':'), allow_nan=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    source = mc3_disc()
    if file_digest(source) != ISO_SHA:
        raise ValueError('original MC3 disc identity mismatch')
    disc = CookedDisc(source)
    try:
        rows = [row for row in disc.entries if row['path'] == 'ASSETS.DAT;1']
        if len(rows) != 1:
            raise ValueError('missing native MC3 ASSETS archive')
        data = encode(from_archive(DaveArchive(disc.region(rows[0]), rows[0]['size'])))
        if args.verify:
            if not OUTPUT.is_file() or OUTPUT.read_bytes() != data:
                raise ValueError('native garage pack differs from original disc derivation')
        else:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_bytes(data)
        print('PASS native MC3 garage inputs: ' + hashlib.sha256(data).hexdigest())
    finally:
        disc.close()


if __name__ == '__main__':
    main()
