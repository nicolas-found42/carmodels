#!/usr/bin/env python3
"""Prove dealership edits/rebuilds are independent of the recovered source corpus."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from bake_models import ROOT, VERTEX, bake_car, read_glb
import base64
import math
from build_dealership import DEALERSHIP, build, check, load_all
from seed_dealership import seed


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_glb(path, doc, binary):
    text = json.dumps(doc).encode()
    text += b' ' * (-len(text) % 4)
    result = struct.pack('<3I', 0x46546C67, 2, 28 + len(text) + len(binary))
    result += struct.pack('<2I', len(text), 0x4E4F534A) + text
    result += struct.pack('<2I', len(binary), 0x004E4942) + binary
    path.write_bytes(result)


class DealershipBuildTests(unittest.TestCase):
    def test_static_edited_export_without_recovery_metadata(self):
        # A replacement static mesh need not retain source extras or material names.
        positions = [(0, 0, 0), (1, 0, 0), (0, 1, 1)]
        binary = b''.join(struct.pack('<3f', *p) for p in positions)
        binary += struct.pack('<9f', *([0, -2**-0.5, 2**-0.5] * 3))
        binary += struct.pack('<3H', 0, 1, 2) + b'\0\0'
        doc = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
               'nodes': [{'mesh': 0, 'scale': [2, 3, -4], 'rotation': [0, 0, 2**-0.5, 2**-0.5]}],
               'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1}, 'indices': 2}]}],
               'buffers': [{'byteLength': len(binary)}],
               'bufferViews': [{'buffer': 0, 'byteOffset': offset, 'byteLength': length}
                               for offset, length in [(0, 36), (36, 36), (72, 6)]],
               'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
                             {'bufferView': 1, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
                             {'bufferView': 2, 'componentType': 5123, 'count': 3, 'type': 'SCALAR'}]}
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp) / 'edited.glb'
            write_glb(model, doc, binary)
            baked = bake_car('CUSTOM', model.read_bytes(), source_mode=False)
            self.assertEqual(baked['triangleCount'], 1)
            self.assertEqual(baked['parts'][0]['kind'], 'body')
            self.assertEqual(baked['wheelHubs'], [])
            vertices = list(VERTEX.iter_unpack(base64.b64decode(baked['parts'][0]['vertices'])))
            self.assertEqual(struct.unpack('<3H', base64.b64decode(baked['parts'][0]['indices'])), (0, 2, 1))
            for vertex in vertices:
                self.assertAlmostEqual(math.sqrt(sum(v*v for v in vertex[3:6])), 1, places=6)
            # Independent inverse-transpose result after rotation, scale and axis conversion.
            self.assertAlmostEqual(vertices[0][3], -0.6, places=6)
            self.assertAlmostEqual(vertices[0][4], 0, places=6)
            self.assertAlmostEqual(vertices[0][5], -0.8, places=6)
            # The equivalent column-major affine matrix must give identical geometry.
            doc['nodes'][0] = {'mesh': 0, 'matrix': [0, 2, 0, 0, -3, 0, 0, 0, 0, 0, -4, 0, 0, 0, 0, 1]}
            write_glb(model, doc, binary)
            equivalent = bake_car('CUSTOM', model.read_bytes(), source_mode=False)
            for actual, expected in zip(equivalent['bounds'], baked['bounds']):
                self.assertAlmostEqual(actual, expected, places=6)
            doc['nodes'][0]['matrix'][0:4] = [0, 0, 0, 0]
            write_glb(model, doc, binary)
            with self.assertRaisesRegex(ValueError, 'singular transform'):
                bake_car('CUSTOM', model.read_bytes(), source_mode=False)

    def test_all_editable_copies_are_independent_files(self):
        catalog = json.loads((DEALERSHIP / 'catalog.json').read_text())
        self.assertEqual(len([c for c in catalog if c.get('game', 'ford-racing-2') == 'ford-racing-2']), 35)
        for entry in catalog:
            code = entry['code']
            copy = DEALERSHIP / 'models' / f'{code}.glb'
            source = ROOT / (f"dealership/public/{entry['game']}/{entry['sourceCode']}.glb" if entry.get('game') in ('gran-turismo', 'redline') else f'dealership/public/ford-racing-2/{code}.glb')
            self.assertFalse(copy.is_symlink())
            self.assertEqual(copy.stat().st_nlink, 1)
            self.assertFalse(os.path.samefile(copy, source))
        # Copies are intentionally editable: equality with source is not an invariant.

    def test_edit_compile_and_repeat_preserve_working_models_and_sources(self):
        source_hashes = {p: sha(p) for p in (ROOT / 'dealership/public/ford-racing-2').glob('*.glb')}
        code = 'GRAN_TORINO'
        entry = next(c for c in json.loads((DEALERSHIP / 'catalog.json').read_text()) if c['code'] == code)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work, output = base / 'editable', base / 'compiled/cars.json'
            (work / 'models').mkdir(parents=True)
            model = work / 'models' / f'{code}.glb'
            shutil.copyfile(ROOT / f'dealership/public/ford-racing-2/{code}.glb', model)
            (work / 'catalog.json').write_text(json.dumps([entry]))
            before = build(work, output)[0]
            check(work, output)
            output_hash = sha(output)
            doc, binary = read_glb(model.read_bytes())
            root = doc['scenes'][doc['scene']]['nodes'][0]
            doc['nodes'][root]['scale'] = [1, 1, 1.2]  # Change body length in the editable GLB.
            write_glb(model, doc, binary)
            with self.assertRaisesRegex(ValueError, 'stale'):
                check(work, output)  # Geometry edit alone invalidates compiled data.
            entry['name'] = 'Custom Gran Torino'
            (work / 'catalog.json').write_text(json.dumps([entry]))
            edited_hash = sha(model)
            with self.assertRaisesRegex(ValueError, 'stale'):
                check(work, output)
            self.assertEqual(sha(output), output_hash, 'freshness check is read-only')
            # Normal builds must not use any source seeding/metadata function.
            with patch('seed_dealership.load_source_metadata', side_effect=AssertionError('source metadata accessed')), patch('bake_models.load_source_model', side_effect=AssertionError('source GLB accessed')):
                after = build(work, output)[0]
                compiled_hash = sha(output)
                repeat = build(work, output)[0]
            length = lambda car: car['model']['bounds'][3] - car['model']['bounds'][0]
            self.assertAlmostEqual(length(after), length(before) * 1.2, places=5)
            self.assertEqual(after['name'], 'Custom Gran Torino')
            self.assertEqual(after, repeat)
            self.assertEqual(sha(output), compiled_hash)
            self.assertEqual(sha(model), edited_hash)
            self.assertEqual(after['model']['source']['sha256'], edited_hash)
            check(work, output)
            entry['name'] = 'Another custom name'
            (work / 'catalog.json').write_text(json.dumps([entry]))
            with self.assertRaisesRegex(ValueError, 'stale'):
                check(work, output)
            entry['name'] = 'Custom Gran Torino'
            (work / 'catalog.json').write_text(json.dumps([entry]))
            with patch('seed_dealership.load_source_metadata', side_effect=AssertionError('source metadata accessed')):
                self.assertFalse(seed(work))
            self.assertEqual(sha(model), edited_hash)
            self.assertEqual(json.loads((work / 'catalog.json').read_text())[0]['name'], 'Custom Gran Torino')
            for forbidden in [work / 'models' / 'GRAN_TORINO.glb', ROOT / 'dealership/public/ford-racing-2/GRAN_TORINO.glb', ROOT / 'ford-racing-2/unwanted.json', ROOT / 'gran-turismo/unwanted.json', ROOT / 'redline/unwanted.json', ROOT / 'dealership/public/models.json']:
                with self.assertRaisesRegex(ValueError, 'must not replace source or editable'):
                    build(work, forbidden)
        self.assertEqual({p: sha(p) for p in source_hashes}, source_hashes)

    def test_link_and_invalid_catalog_controls(self):
        entry = json.loads((DEALERSHIP / 'catalog.json').read_text())[0]
        code = entry['code']
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / 'models').mkdir()
            catalog = work / 'catalog.json'
            catalog.write_text(json.dumps([entry]))
            model = work / 'models' / f'{code}.glb'
            model.symlink_to(DEALERSHIP / 'models' / f'{code}.glb')
            with self.assertRaisesRegex(ValueError, 'independent file'):
                load_all(work)
            model.unlink()
            # A hard link is just as unsafe as a symlink for editing.
            os.link(DEALERSHIP / 'models' / f'{code}.glb', model)
            try:
                with self.assertRaisesRegex(ValueError, 'independent file'):
                    load_all(work)
            finally:
                model.unlink()
            shutil.copyfile(DEALERSHIP / 'models' / f'{code}.glb', model)
            for bad in [[], {}, [entry, entry], [{**entry, 'code': '../OTHER'}], [{**entry, 'model': {}}]]:
                catalog.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_all(work)


if __name__ == '__main__':
    unittest.main()
