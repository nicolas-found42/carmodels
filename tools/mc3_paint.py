"""Preserve source-pinned MC3 paint settings without inventing a preset palette.

``default.mccarcustom`` and ``CarCfg`` are distinct shipped formats. Their
runtime precedence is unresolved: explicit RGB vectors are labelled native
customization choices, never asserted as the currently active factory default.
"""
import copy
import hashlib
import math
from pathlib import Path
import re

from import_mc3_catalogs import regular

PROFILE = 'mc3-native-customization-paint-v1'
CONFIG_FIELDS = r'Paint|ColorShift|Vinyl|UseDefaultVinyl|UseChromeDecal|ChromeDecal|NormalDecal|Decal|Logos'
CUSTOM_FIELDS = r'm_(?:paint|color|startPos|numGradients|mShift|metallicPaint|hightlight|decal|logoIdx)'
LIMITS = [
    'Explicit native customization RGB vectors are selectable static translations; '
    'their runtime precedence over CarCfg paint presets is unresolved.',
    'CarCfg paint preset indices and palette coordinates are retained, but the '
    'preset-to-RGB conversion and current factory default are not established.',
    'Native RGB channels are carried unscaled; game colour space, finish, '
    'gradients, metal flake and runtime vinyl/decal compositing are not emulated.',
    'Only direct carpaint and carpaint_novinyl materials receive paint variants; '
    'composite wrapper shader selection remains unresolved.',
    'Wheel, caliper, window, neon and separate secondary-paint channel bindings are '
    'not recovered. Native finish names are retained without invented PBR finish controls.',
]


def _source(root, row):
    name = row['file']
    if (not isinstance(name, str) or not name or '\\' in name or '\0' in name
            or Path(name).is_absolute() or '..' in name.split('/')
            or Path(name).as_posix() != name):
        raise ValueError('paint source path must be canonical and relative')
    path = root/name
    regular(path)
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('paint source outside extraction or missing')
    if not 0 < path.stat().st_size <= 1024 * 1024:
        raise ValueError('paint source size outside bound')
    data = path.read_bytes()
    if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('paint source hash/size differs from extraction index')
    return data


def _fields(data, kind):
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('paint settings must be ASCII') from error
    match = re.fullmatch(r'type:\s*a\s+' + kind + r'\s*\{([^{}]*)\}\s*', text, re.DOTALL)
    if match is None:
        raise ValueError('unsupported native paint settings grammar')
    result = {}
    for line in match[1].splitlines():
        if not line.strip():
            continue
        field = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)\s+([^{}]+?)\s*', line)
        if field is None:
            raise ValueError('malformed or duplicate native paint field')
        if not re.match(CONFIG_FIELDS if kind == 'CarCfg' else CUSTOM_FIELDS, field[1]):
            continue
        value = ' '.join(field[2].split())
        if field[1] in result:
            raise ValueError('conflicting duplicate native paint field')
        result[field[1]] = value
    return result


def _rgb(value):
    try:
        channels = [float(v) for v in value.split()]
    except ValueError as error:
        raise ValueError('invalid native paint RGB vector') from error
    if len(channels) != 3 or not all(math.isfinite(v) and 0 <= v <= 1 for v in channels):
        raise ValueError('invalid native paint RGB vector')
    return channels


def read_native_appearance(root, index, code):
    """Read exact vehicle namespaces and hash-check every duplicate occurrence."""
    root = Path(root)
    if not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code):
        raise ValueError('invalid native paint vehicle identity')
    prefix = r'shared/assets/\d+/tune/vehicle/customdata/'
    groups = {}
    for row in index['files']:
        name = row['file']
        match = re.fullmatch(prefix + re.escape(code) + r'/([a-z0-9_]+)\.mccarcustom', name)
        key = ('custom', match[1]) if match else None
        if re.fullmatch(prefix + re.escape(code) + r'\.carcfg', name):
            key = ('config', code)
        if key is not None:
            groups.setdefault(key, []).append(row)
    configs, customs, choices = [], [], []
    for (kind, name), rows in sorted(groups.items()):
        payloads = [_source(root, row) for row in rows]
        if len(set(payloads)) != 1:
            raise ValueError('conflicting native paint source copies')
        sources = [{key: row[key] for key in ('file', 'bytes', 'sha256')}
                   for row in sorted(rows, key=lambda row: row['file'])]
        fields = _fields(payloads[0], 'CarCfg' if kind == 'config' else 'mcCarCustom')
        if kind == 'config':
            configs.append({'sources': sources, 'fields': fields})
        else:
            record = {'name': name, 'sources': sources, 'fields': fields}
            customs.append(record)
            if 'm_paintColor1' in fields:
                choices.append({'name': 'Native customization: '+name,
                                'rgb': _rgb(fields['m_paintColor1']), 'source': record})
    preset_rows = [row for row in index['files'] if re.fullmatch(
        prefix + r'paintjobs/paintjoblist\.txt', row['file'])]
    presets = None
    if preset_rows:
        payloads = [_source(root, row) for row in preset_rows]
        if len(set(payloads)) != 1:
            raise ValueError('conflicting native paint preset lists')
        text = payloads[0].decode('ascii')
        groups, end = [], 0
        for match in re.finditer(r'([A-Za-z]+)\s+(\d+)\s*\{([^{}]*)\}', text):
            names = match[3].split()
            if (text[end:match.start()].strip() or len(names) != int(match[2])
                    or any(not re.fullmatch(r'[a-z0-9_]+', name) for name in names)):
                raise ValueError('invalid native paint preset list')
            groups.append({'category': match[1], 'names': names})
            end = match.end()
        if not groups or text[end:].strip():
            raise ValueError('invalid native paint preset list')
        presets = {'sources': [{key: row[key] for key in ('file', 'bytes', 'sha256')}
                              for row in sorted(preset_rows, key=lambda row: row['file'])],
                   'groups': groups, 'index_base_established': False}
    return {'profile': PROFILE, 'factory_default_established': False,
            'configs': configs, 'customizations': customs, 'choices': choices,
            'preset_list': presets,
            'claim_limits': list(LIMITS)}


def add_paint_variants(doc, appearance):
    """Augment material choices only; retain the existing inspection default.

    A wrapper's first template happens to be paint on many cars. Its category
    remains a wrapper: using that first name as proof would repaint carbon kits.
    """
    if 'nativeAppearance' in doc.get('extras', {}) or 'KHR_materials_variants' in doc.get('extensions', {}):
        raise ValueError('native paint variants already applied')
    materials = doc['materials']
    used = {primitive['material'] for mesh in doc['meshes'] for primitive in mesh['primitives']}
    eligible, composites = [], []
    for index, material in enumerate(materials):
        native = material.get('extras', {})
        category = native.get('shader_category')
        if category == 'composite_material_wrapper' and any(
                t in ('carpaint', 'carpaint_novinyl') for t in native.get('composite_templates', [])):
            composites.append(index)
        if (index in used and category in ('carpaint', 'carpaint_novinyl')
                and native.get('shader_template') == category
                and material.get('alphaMode', 'OPAQUE') == 'OPAQUE'
                and 'baseColorTexture' not in material['pbrMetallicRoughness']):
            eligible.append(index)
    appearance = copy.deepcopy(appearance)
    appearance.update(paint_materials=eligible, unresolved_composite_materials=composites)
    doc.setdefault('extras', {})['nativeAppearance'] = appearance
    # These are complete-material bindings, never inferred per-texel paint masks.
    # Keep a channel even when this car lacks a recorded customization colour:
    # the viewer may transfer another source-pinned colour from the same game.
    colours = []
    for choice in appearance['choices']:
        source = choice['source']['sources'][0]
        identity = source['file'] + ':m_paintColor1'
        colours.append({'id': 'mc3-' + hashlib.sha256(identity.encode()).hexdigest()[:20],
                        'name': Path(source['file']).parent.name + ' / ' + choice['source']['name'],
                        'rgb': list(choice['rgb']),
                        'source': identity + ' (sha256 ' + source['sha256'] + ')'})
    doc['extras']['gamePaint'] = {
        'schema': 1,
        'channels': [{'id': 'body', 'name': 'Body paint', 'materials': eligible}] if eligible else [],
        'colors': colours, 'limits': list(LIMITS),
    }
    limits = doc['extras'].setdefault('claim_limits', [])
    limits.extend(limit for limit in LIMITS if limit not in limits)
    choices = appearance['choices']
    if not choices or not eligible:
        return
    variants, mapping = [], {}
    for variant, choice in enumerate(choices):
        variants.append({'name': choice['name'], 'extras': choice['source']})
        for base in eligible:
            material = copy.deepcopy(materials[base])
            material['name'] += ' / '+choice['name']
            material['pbrMetallicRoughness']['baseColorFactor'] = [*choice['rgb'], 1.0]
            material['extras'].update(native_paint_choice=choice,
                                     base_color=[*choice['rgb'], 1.0],
                                     display_factor_source='native-customization-rgb-static-translation')
            material['extras']['claim_limits'] = list(LIMITS)
            mapping.setdefault(base, []).append({'material': len(materials), 'variants': [variant]})
            materials.append(material)
    doc.setdefault('extensions', {})['KHR_materials_variants'] = {'variants': variants}
    used = doc.setdefault('extensionsUsed', [])
    if 'KHR_materials_variants' not in used:
        used.append('KHR_materials_variants')
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            if primitive['material'] in mapping:
                primitive.setdefault('extensions', {})['KHR_materials_variants'] = {
                    'mappings': copy.deepcopy(mapping[primitive['material']])}
