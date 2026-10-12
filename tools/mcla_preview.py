"""Static stock LOD-0 MCLA previews, with source identity and explicit assembly readings.

No runtime config is executed. Part offsets, neutral paint and normalized wheel sizing
are readings, documented in research/midnight-club-los-angeles-previews.md.
"""
import hashlib
import json
import math
import re
from pathlib import Path

import mcla_lzx
import mcla_model
import mcla_texture
from gt4_glb import Builder, _face_normals, _normalize
from mcla_rpf import jenkins
from mc3_textures import encode_png

PROFILE = 'mcla-xbox360-static-stock-v1'
LIMITS = [
    'Static stock-slot LOD 0 assembly; XCC configurations, damage, lamps, animation and game shader execution are not reproduced.',
    'Part attachment names and model-space translations are assembly readings; widebody alternatives, occluders and deforming convertible tops are omitted.',
    'Native Y-up coordinates, facing -Z with +X right; no game-to-viewer rotation is applied.',
    'Diffuse textures use the half-resolution XTL pack where present, otherwise the source XTP. Neutral paint and simplified opaque materials do not reproduce runtime colour, reflection, glass or blending.',
    'Shared rims join by exact stock name/hash, not runtime configuration. Tire radius equals source axle height; rim radius uses the source tire bead/outer-radius ratio, brake radius is 0.55, and width 0.65 of tire radius. These are preview approximations, not decoded tire specifications.',
    'Ambient models keep their embedded wheels. Shared tire textures and unidentified stock brake packs are not substituted; tire material is neutral rubber.',
]
# Ordered aliases accommodate older skeleton vocabulary; no fuzzy match is applied.
SLOT_BONES = {
    'hood': ('hd', 'hood', 'hoods'), 'bumper_f': ('bumf', 'f_bumpers', 'bmpf_bone'), 'bumper_r': ('bumr', 'r_bumpers', 'bumr_bone'),
    'door_l': ('door_l_regular_anim', 'door_l_regular', 'door_left_regular_anim'), 'door_r': ('door_r_regular_anim', 'door_r_regular', 'door_right_regular_anim'),
    'door_l_int': ('door_l_regular_anim', 'door_l_regular', 'door_left_regular_anim'), 'door_r_int': ('door_r_regular_anim', 'door_r_regular', 'door_right_regular_anim'),
    'spoiler': ('splr', 'spoilers', 'spoiler', 'trunk_splr', 'splr_bone'), 'trunk_swap': ('tk', 'trunk', 'trunkbone'), 'taillight_b': ('trunk_tl', 'tk', 'trunk', 'trunkbone'),
    'steer_whl': ('steer', 'str', 'steerbone', 'steer_bone'), 'headlight': ('hl', 'headlights', 'hlights'), 'taillight': ('tl', 'taillights', 'tlights', 'tail_lights'),
    'skirts': ('ss', 'sideskirts', 'ss_bone', 'white_section'), 'seats_f': ('seats_driver', 'seats', 'seat_driver', 'seat_left', 'seats_d', 'seats_l'),
    'seats_p': ('seats_passenger', 'seats_pass', 'seat_passenger', 'seat_pass', 'seats_p', 'seat_passs_pass'), 'intercooler': ('intercoolers', 'intercooler'),
    'armfl': ('axl_0', 'axl_front'), 'armfr': ('axl_1',),
    'armrl': ('axl_2', 'axl_rear'), 'armrr': ('axl_3',),
    'axle': ('axl_2',), 'shockrl': ('axl_2',), 'shockrr': ('axl_3',),
    'guiderl': ('axl_2',), 'guiderr': ('axl_3',),
    'fenders': ('vroot',), 'interior': ('vroot',), 'subbumf': ('vroot',),
    'subbumr': ('vroot',), 'spoiler_b': ('vroot',),
    'bike_cowl': ('vroot',), 'bike_tail': ('vroot',), 'bike_tank': ('vroot',),
    'conv_topup': ('vroot',), 'conv_topdown': ('vroot',),
}
OMIT_SLOTS = {'widebody', 'hood_wide', 'door_l_wide', 'door_r_wide',
              'spoiler_wide', 'trunk_wide', 'conv_top'}
STOCK = re.compile(r'(.+?)0_lod_0\.xrsc\Z')


class PreviewError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise PreviewError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Sources:
    """Hash-check each consumed source against the extraction index before decoding."""
    def __init__(self, root, index=None):
        self.root = Path(root)
        self.index = index if index is not None else json.loads((self.root / 'index.json').read_text())
        self.rows = {r['file']: r for r in self.index['files']}
        need(len(self.rows) == len(self.index['files']), 'duplicate extraction path')
        self.used, self.models, self.packs = {}, {}, {}

    def read(self, path):
        need(path in self.rows, 'source missing from extraction index: ' + path)
        parts = Path(path).parts
        need(not Path(path).is_absolute() and '..' not in parts, 'unsafe source path')
        target = (self.root / path).resolve()
        need(target.is_relative_to(self.root.resolve()), 'source path escapes extraction')
        data = target.read_bytes()
        row = self.rows[path]
        need(len(data) == row['bytes'] and sha(data) == row['sha256'], 'source hash/size differs: ' + path)
        self.used[path] = {'file': path, 'bytes': len(data), 'sha256': sha(data), 'source': row.get('source', {})}
        return data

    def model(self, path):
        if path not in self.models:
            data, h = mcla_lzx.decompress(self.read(path))
            need(h['type'] == 63, 'model resource has wrong type')
            self.models[path] = mcla_model.decode(data, h['virtual'], h['physical'])
        return self.models[path]

    def pack(self, path):
        if path not in self.packs:
            data, h = mcla_lzx.decompress(self.read(path))
            self.packs[path] = mcla_texture.decode(data, h['virtual'], h['physical'], h['type'])
        return self.packs[path]

    def directory(self, prefix):
        return sorted(p for p in self.rows if p.startswith(prefix + '/') and '/' not in p[len(prefix) + 1:])


def select_parts(paths):
    """Select source LOD 0 and stock variant 0; exclude alternate body kits explicitly."""
    need(sum(Path(p).name == 'body_lod_0.xrsc' for p in paths) == 1, 'expected one LOD-0 body')
    chosen, omitted = [], []
    for path in sorted(paths):
        name = Path(path).name
        match = STOCK.fullmatch(name)
        if name == 'body_lod_0.xrsc':
            chosen.append(('body', path))
        elif match:
            slot = match[1]
            if slot in OMIT_SLOTS or slot.startswith('occluder'):
                omitted.append(path)
            else:
                chosen.append((slot, path))
    # Top-up and top-down represent alternatives. Prefer a raised rigid roof.
    if any(slot == 'conv_topup' for slot, _ in chosen):
        omitted.extend(path for slot, path in chosen if slot == 'conv_topdown')
        chosen = [(slot, path) for slot, path in chosen if slot != 'conv_topdown']
    return sorted(chosen, key=lambda item: (item[0] != 'body', item[0])), omitted


def attachment(slot, part, body):
    if slot == 'body':
        return 'vroot', (0., 0., 0.)
    root = part['skeleton'][0]['name'] if part['skeleton'] else None
    candidates = (root,) + SLOT_BONES.get(slot, ())
    for candidate in candidates:
        if candidate in body:
            return candidate, tuple(body[candidate]['model'])
    raise PreviewError('unmapped stock attachment: %s (%s)' % (slot, root))


def shared_directory(sources, category, name):
    for directory in (name, '0x%08x' % jenkins(name)):
        prefix = 'shared/resources/%s/%s' % (category, directory)
        if prefix + '/body_lod_0.xrsc' in sources.rows:
            return prefix
    return None


def stock_rim_name(vehicle):
    suffix = vehicle.split('_', 1)[1]
    if suffix.endswith('_dub'):
        suffix = suffix[:-4]
    if suffix == 'mbz_s600_07':
        suffix = 'mbz_s600'
    return ('whld_stk_' if vehicle.startswith('vpd_') else 'whl_stk_') + suffix


def pack_for(sources, prefix, preferred=None):
    candidates = [p for p in sources.directory(prefix) if p.endswith(('.xtl', '.xtp', '.rsc83'))]
    if preferred:
        wanted = prefix + '/' + preferred + '.xtl'
        if wanted in candidates:
            return wanted
    need(len(candidates) == 1, 'ambiguous/missing texture pack: ' + prefix)
    return candidates[0]


def material(builder, shaders, reader, namespace, index, rubber=False):
    need(isinstance(index, int) and 0 <= index < len(shaders), 'geometry shader outside source pack')
    key = '%s/shader%d' % (namespace, index)
    if key in builder.materials:
        return builder.materials[key]
    shader = shaders[index]
    colour = [0.8, 0.8, 0.8, 1.]
    if rubber:
        colour = [0.025, 0.025, 0.025, 1.]
    else:
        for p in shader['params']:
            if p['hash'] == 0x1468B111 and p.get('value'):
                rgb = p['value'][0][:3]
                if all(math.isfinite(v) and 0 <= v <= 1 for v in rgb):
                    colour[:3] = rgb
    m = builder.material(key, colour)
    entry = builder.doc['materials'][m]
    entry['extras'] = {'sourceShader': shader['name'], 'sourceDrawBucket': shader['draw_bucket']}
    diffuse = next((p.get('texture') for p in shader['params'] if p['hash'] == mcla_texture.DIFFUSE), None)
    if diffuse is not None and not rubber:
        tkey = '%s/%s/%d' % (namespace, diffuse['name'], diffuse['offset'])
        if tkey not in builder.textures:
            rgba = mcla_texture.pixels(reader, diffuse)
            # Shader alpha carries effects as well as opacity. Static materials stay opaque.
            rgba = bytes(v if i % 4 != 3 else 255 for i, v in enumerate(rgba))
            view = builder.view(encode_png(diffuse['width'], diffuse['height'], rgba))
            builder.doc.setdefault('images', []).append({'bufferView': view, 'mimeType': 'image/png', 'name': tkey})
            builder.doc.setdefault('textures', []).append({'source': len(builder.doc['images']) - 1, 'sampler': 1})
            builder.textures[tkey] = len(builder.doc['textures']) - 1
        entry['pbrMetallicRoughness']['baseColorTexture'] = {'index': builder.textures[tkey]}
    return m


def mesh(builder, part, pack, reader, namespace, rubber=False):
    primitives, vertices, triangles = [], 0, 0
    shaders = pack['shader_group']['shaders']
    for model in part['models']:
        need(not model['skinned'], 'selected model requires skinning: ' + namespace)
        for g in model['geometries']:
            points = g['position']
            need(points and g['indices'] and len(g['indices']) % 3 == 0, 'empty/non-triangular geometry')
            need(all(0 <= i < len(points) for i in g['indices']), 'index outside preview geometry')
            attrs = {'POSITION': builder.accessor(points, 'position')}
            normals = g.get('normal') or _face_normals(points, list(zip(*[iter(g['indices'])] * 3)))
            attrs['NORMAL'] = builder.accessor([_normalize(n) for n in normals], 'normal')
            if g.get('texcoord0'):
                attrs['TEXCOORD_0'] = builder.accessor(g['texcoord0'], 'uv')
            mat = material(builder, shaders, reader, namespace, g['shader'], rubber)
            primitives.append({'attributes': attrs, 'indices': builder.accessor(g['indices'], 'index'), 'material': mat, 'mode': 4})
            vertices += len(points)
            triangles += len(g['indices']) // 3
    builder.doc['meshes'].append({'name': namespace, 'primitives': primitives})
    return len(builder.doc['meshes']) - 1, vertices, triangles


def tire_bead_ratio(part):
    """Radial inner/outer extent of the normalized shared tire, for a joined rim seam."""
    radii = [math.hypot(y, z) for model in part['models']
             for g in model['geometries'] for _, y, z in g['position']]
    need(radii and all(math.isfinite(v) and v > 0 for v in radii), 'invalid tire radial extent')
    inner, outer = min(radii), max(radii)
    need(inner < outer, 'tire has no radial thickness')
    return inner / outer


def build_car(extraction, vehicle, index=None):
    """Return (GLB bytes, provenance/assembly record), without writing generated output."""
    need(re.fullmatch(r'(?:va|vp|vpd)_[a-z0-9_]+', vehicle) is not None, 'unsafe/unknown vehicle code')
    sources = Sources(extraction, index)
    prefix = vehicle + '/resources/vehicle/' + vehicle
    chosen, omitted = select_parts(sources.directory(prefix))
    body_part = sources.model(prefix + '/body_lod_0.xrsc')
    bones = {b['name']: b for b in body_part['skeleton']}
    pack_path = pack_for(sources, prefix, vehicle)
    pack, reader = sources.pack(pack_path)
    builder = Builder()
    builder.doc['asset']['generator'] = PROFILE
    builder.doc['scenes'] = [{'nodes': []}]
    parts, wheels, meshes = [], [], {}
    total_vertices = total_triangles = 0

    def node(part, pack, reader, label, offset, scale=(1., 1., 1.), rotation=None, rubber=False):
        nonlocal total_vertices, total_triangles
        key = (label.split('@', 1)[0], rubber)
        if key not in meshes:
            meshes[key] = mesh(builder, part, pack, reader, key[0], rubber)
        mi, vc, tc = meshes[key]
        entry = {'name': label, 'mesh': mi, 'translation': list(offset), 'scale': list(scale)}
        if rotation:
            entry['rotation'] = rotation
        builder.doc['nodes'].append(entry)
        builder.doc['scenes'][0]['nodes'].append(len(builder.doc['nodes']) - 1)
        total_vertices += vc
        total_triangles += tc
        return vc, tc

    for slot, path in chosen:
        part = body_part if slot == 'body' else sources.model(path)
        if slot == 'exh_pipe':
            # Exhaust anchors belong to the selected rear bumper, not the category origin.
            rear = next((sources.model(p) for s, p in chosen if s == 'bumper_r'), None)
            if rear is None:
                omitted.append(path)
                continue
            _, base = attachment('bumper_r', rear, bones)
            anchors = [b for b in rear['skeleton'] if b['name'].lower().startswith(('exstprimary', 'exstsecondary', 'ext_primary', 'ext_secondary'))]
            if not anchors:
                omitted.append(path)
                continue
            placements = [(b['name'], tuple(a + q for a, q in zip(base, b['model']))) for b in anchors]
        else:
            placements = [attachment(slot, part, bones)]
        for anchor, offset in placements:
            vc, tc = node(part, pack, reader, path + '@' + anchor, offset)
            parts.append({'slot': slot, 'file': path, 'bone': anchor, 'translation': list(offset), 'vertices': vc, 'triangles': tc})

    if not vehicle.startswith('va_') and vehicle != 'vp_citybus_07':
        axle_names = {name for name in bones if name.startswith('axl_')}
        car_axes = ('axl_0', 'axl_1', 'axl_2', 'axl_3')
        bike_axes = ('axl_front', 'axl_rear')
        need(axle_names in (set(car_axes), set(bike_axes)),
             'player wheel axle set incomplete, mixed or unsupported: ' + ','.join(sorted(axle_names)))
        axes = [bones[n] for n in (bike_axes if axle_names == set(bike_axes) else car_axes)]
        rim_name = stock_rim_name(vehicle)
        rim_dir = shared_directory(sources, 'rims', rim_name)
        need(rim_dir is not None, 'stock rim missing: ' + rim_name)
        bike = any(b['name'] == 'axl_front' for b in axes)
        tire_dir = 'shared/resources/tires/models/' + ('tir_bike' if bike else 'tir_car')
        brake_suffix = vehicle.split('_', 1)[1].removesuffix('_dub')
        brake_dir = shared_directory(sources, 'brakes', ('brkd_stk_' if vehicle.startswith('vpd_') else 'brk_stk_') + brake_suffix)
        bead_ratio = tire_bead_ratio(sources.model(tire_dir + '/body_lod_0.xrsc'))
        shared = [(rim_dir, False, bead_ratio), (tire_dir, True, 1.)]
        if brake_dir:
            shared.append((brake_dir, False, 0.55))
        for axle in axes:
            x, height, z = axle['model']
            need(math.isfinite(height) and 0.05 <= height <= 1.5, 'invalid axle height for wheel scaling')
            for directory, rubber, fraction in shared:
                part = sources.model(directory + '/body_lod_0.xrsc')
                spath = pack_for(sources, directory)
                spack, sr = sources.pack(spath)
                # All shared wheel assets are normalized to radial radius 0.5.
                scale = (2 * height * (0.35 if bike else 0.65), 2 * height * fraction, 2 * height * fraction)
                rot = [0., 1., 0., 0.] if x < 0 else None
                label = directory + '@' + axle['name']
                vc, tc = node(part, spack, sr, label, (x, height, z), scale, rot, rubber)
                wheels.append({'file': directory + '/body_lod_0.xrsc', 'pack': spath, 'bone': axle['name'],
                               'translation': [x, height, z], 'scale': list(scale), 'rotation': rot,
                               'sizing': {'tire_radius': height, 'radius_fraction': fraction,
                                          'width': height * (0.35 if bike else 0.65),
                                          'method': 'axle-height-and-native-tire-bead'},
                               'vertices': vc, 'triangles': tc})
    record = {'vehicle': vehicle, 'profile': PROFILE, 'variant': 'stock', 'lod': 0,
              'vertices': total_vertices, 'triangles': total_triangles, 'parts': parts, 'wheels': wheels,
              'omitted': sorted(omitted), 'texture_pack': pack_path,
              'sources': [sources.used[p] for p in sorted(sources.used)], 'claim_limits': LIMITS}
    builder.doc['extras'] = dict(record, car=vehicle, source_profile=PROFILE)
    glb = builder.finish()
    record = dict(record, glb_bytes=len(glb), glb_sha256=sha(glb))
    return glb, record
