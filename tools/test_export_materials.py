#!/usr/bin/env python3
"""Check material ownership against source header/selector contracts, not array order."""
import copy
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def check(doc, car, variants, headers):
    assert all(s['magFilter'] == 9729 and s['minFilter'] == 9729 for s in doc['samplers']), 'linear sampler differs'
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            selector = primitive['extras']['third']
            material = doc['materials'][primitive['material']]
            pbr = material['pbrMetallicRoughness']
            if selector == 65535:
                assert 'baseColorTexture' not in pbr, 'untextured header acquired a texture'
                source = headers[primitive['extras']['headerOffset']]
                assert material['name'] == 'Header untextured ' + source['base_color_word'], 'header colour ownership differs'
                rgba = source['base_color_rgba_unscaled']
                assert pbr['baseColorFactor'] == [c / 255 for c in rgba[:3]] + [min(1, rgba[3] / 128)], 'header colour or alpha differs'
                assert material.get('alphaMode', 'OPAQUE') == ('BLEND' if rgba[3] < 128 else 'OPAQUE'), 'header blend differs'
            else:
                assert 'baseColorTexture' in pbr, 'textured header lost its source texture'
                texture = doc['textures'][pbr['baseColorTexture']['index']]
                assert doc['images'][texture['source']]['name'] == car['textures'][selector]['name'], 'source texture binding differs'
            for mapping in primitive.get('extensions', {}).get('KHR_materials_variants', {}).get('mappings', []):
                for variant_index in mapping['variants']:
                    expected = variants['variants'][variant_index]['material_remap'][str(selector)]
                    target = doc['materials'][mapping['material']]['pbrMetallicRoughness']['baseColorTexture']['index']
                    assert target == expected, 'variant texture binding differs'


def main():
    census = json.loads((ROOT / 'research/evidence/original-recovery/car-asset-census.json').read_text())
    variants = json.loads((ROOT / 'research/evidence/continuation/source-refresh/texture-variant-contract.json').read_text())
    material_contract = json.loads((ROOT / 'research/evidence/continuation/source-refresh/material-header-contract.json').read_text())
    for car in census['cars']:
        headers = {h['offset']: h for h in next(c for c in material_contract['cars'] if c['car'] == car['code'])['headers']}
        raw = (ROOT / 'dealership/public/ford-racing-2' / (car['code'] + '.glb')).read_bytes()
        doc = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
        check(doc, car, next(c for c in variants['cars'] if c['car'] == car['code']), headers)
    # A legal in-range material index can still refer to the wrong source texture.
    tampered = copy.deepcopy(doc)
    primitive = next(p for m in tampered['meshes'] for p in m['primitives'] if p['extras']['third'] != 65535)
    original = primitive['material']
    primitive['material'] = next(i for i, m in enumerate(tampered['materials']) if 'baseColorTexture' not in m['pbrMetallicRoughness'])
    try:
        check(tampered, car, next(c for c in variants['cars'] if c['car'] == car['code']), headers)
    except AssertionError as error:
        assert str(error) == 'textured header lost its source texture'
    else:
        raise AssertionError('source-binding tamper control was accepted')
    # Preserve both colour and alpha controls with their intended rejection reason.
    for component in [0, 3]:
        changed = copy.deepcopy(doc)
        header_material = next(m for m in changed['materials'] if 'baseColorTexture' not in m['pbrMetallicRoughness'])
        factor = header_material['pbrMetallicRoughness']['baseColorFactor']
        factor[component] = .125 if factor[component] != .125 else .25
        try:
            check(changed, car, next(c for c in variants['cars'] if c['car'] == car['code']), headers)
        except AssertionError as error:
            assert str(error) == 'header colour or alpha differs'
        else:
            raise AssertionError('header colour/alpha tamper control was accepted')
    primitive['material'] = original
    print(f"PASS test_export_materials: {len(census['cars'])} cars, source texture and selector bindings, header colour/alpha/blend, linear samplers, three semantic mutations rejected")


if __name__ == '__main__':
    main()
