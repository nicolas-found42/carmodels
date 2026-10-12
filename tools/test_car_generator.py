"""Generator public-interface regressions; judgments are injected, never live."""
import json
from pathlib import Path
import tempfile
import unittest

from car_generator import Generator

ROOT = Path(__file__).resolve().parents[1]


class FakeJudge:
    def classify_template(self):
        from generator_judge import TEMPLATE_REGIONS
        return [{**r, 'category': 'glass' if 'glass' in r['name'] else 'lights', 'probability': 1} for r in TEMPLATE_REGIONS]

    def classify(self, entries):
        return {e['code']: {'car_probability': .95, 'bodyStyle': {'value': 'coupe', 'probability': .9},
                           'era': {'value': '1970s', 'probability': .9}} for e in entries}


class Tests(unittest.TestCase):
    def test_cancel_stops_every_stage_and_unsupported_parts_require_confirmation(self):
        import threading
        from car_generator import STAGES
        class RequestJudge(FakeJudge):
            def interpret(self, request):
                return {'constraints': {'bodyStyle': {'value': 'coupe', 'probability': .5, 'applied': False}},
                        'unsupported': ['six wheels']}
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            generator.judge = RequestJudge()
            generator.prepare()
            generator.train(epochs=1, device='cpu')
            for stage in STAGES:
                cancel = threading.Event()
                events = []
                def emit(event):
                    events.append(event)
                    if event['stage'] == stage and event['state'] == 'running':
                        cancel.set()
                with self.assertRaises(InterruptedError):
                    generator.generate(seed=35, emit=emit, cancel=cancel)
                self.assertEqual(events[-1]['state'], 'failed')
            events = []
            with self.assertRaises(InterruptedError):
                generator.generate(request='six wheels', confirm=lambda parts: False, emit=events.append)
            self.assertFalse(any(e['stage'] == 'sample shape' for e in events))
            accepted = generator.generate(request='six wheels', confirm=lambda parts: parts == ['six wheels'])
            self.assertTrue(accepted['validation']['passed'])
            without_era = generator.generate(constraints={'era': {'value': '1930s', 'probability': 1}},
                                             confirm=lambda parts: True)
            self.assertFalse(without_era['recipe']['constraints']['era']['applied'])
            self.assertEqual(generator.generate(**without_era['recipe'])['glb'], without_era['glb'])

    def fixture(self, folder):
        source = ROOT / 'dealership/dealership'
        codes = ['GRAN_TORINO', 'GT_SIMULATION__A_A7R_DAY',
                 'REDLINE_BASE_500GT_5BB660DF8232_CD2320C0A42673C7', 'MC3_VP_350Z_04']
        work = Path(folder) / 'dealership'
        (work / 'models').mkdir(parents=True)
        entries = [e for e in json.loads((source / 'catalog.json').read_text()) if e['code'] in codes]
        (work / 'catalog.json').write_bytes(json.dumps(entries).encode())
        for entry in entries:
            (work / 'models' / (entry['code'] + '.glb')).write_bytes(
                (source / 'models' / (entry['code'] + '.glb')).read_bytes())
            if 'nativePackage' in entry:
                package = work / entry['nativePackage']['file']
                package.parent.mkdir(parents=True, exist_ok=True)
                package.write_bytes((source / entry['nativePackage']['file']).read_bytes())
        return Generator(work, Path(folder) / 'generator', judge=FakeJudge())

    def test_both_learned_methods_generate_static_models_and_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            generator.prepare()
            generator.train(epochs=20, device='cpu')
            for cached in generator.cache.glob('*.npy'):
                cached.unlink()
            for method in ['shape space', 'network']:
                events = []
                result = generator.generate(method=method, seed=35, novelty=.25, emit=events.append)
                self.assertEqual([e['stage'] for e in events if e['state'] == 'done'],
                                 ['interpret request', 'pick neighbour cars', 'sample shape', 'rebuild mesh',
                                  'place wheels', 'fit template', 'bake texture', 'validate', 'ready'])
                self.assertTrue(result['validation']['passed'])
                self.assertTrue(result['validation']['watertight_after_uv_weld'])
                self.assertTrue(result['validation']['consistent_winding'])
                placement = next(e['decisions'] for e in events if e['stage'] == 'place wheels' and e['state'] == 'done')
                self.assertEqual(placement['placement_model'], 'learned ' + method)
                self.assertTrue(8000 <= result['body_vertices'] <= 12000)
                replay = generator.generate(**result['recipe'])
                self.assertEqual(result['glb'], replay['glb'])
            donor = generator.dealership / 'models' / (result['wheel_source'] + '.glb')
            donor.write_bytes(donor.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'Replay requires'):
                generator.generate(**result['recipe'])

    def test_prepare_deduplicates_body_geometry_across_unrelated_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            catalog_path = generator.dealership / 'catalog.json'
            catalog = json.loads(catalog_path.read_text())
            source = next(e for e in catalog if e.get('game') == 'redline')
            catalog.append({**source, 'code': 'REDLINE_Z_DUPLICATE', 'name': 'Another paint of the same body'})
            catalog_path.write_text(json.dumps(catalog))
            (generator.dealership / 'models/REDLINE_Z_DUPLICATE.glb').write_bytes(
                (generator.dealership / 'models' / (source['code'] + '.glb')).read_bytes())
            manifest = generator.prepare()
            self.assertEqual(len(manifest['entries']), 4)
            excluded = next(e for e in manifest['excluded'] if e['code'] == 'REDLINE_Z_DUPLICATE')
            self.assertEqual(excluded['reason'], 'duplicate shape')
            self.assertEqual(excluded['duplicate_of'], source['code'])
            self.assertEqual(len({e['shape_sha256'] for e in manifest['entries']}), 4)

    def test_save_is_add_only_and_rebuilds_editable_dealership(self):
        from build_dealership import check
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            generator.prepare()
            generator.train(epochs=1, device='cpu')
            result = generator.generate(seed=35, constraints={'bodyStyle': {'value': 'coupe', 'probability': 1}})
            result['request'] = 'A previous request, retained only for reference'
            before = {p.name: p.read_bytes() for p in (generator.dealership / 'models').iterdir()}
            output = Path(folder) / 'display/cars.json'
            entry = generator.save(result, name='Test Generated coupe', output=output)
            self.assertEqual(entry['honestyLabel'], 'Generated model')
            self.assertEqual(entry['bodyStyleSource'], 'requested')
            self.assertIsNone(entry['bhp'])
            self.assertIsNone(entry['kg'])
            self.assertIsNone(entry['topSpeed'])
            self.assertEqual(entry['generator']['request'], result['request'])
            self.assertEqual(generator.generate(**entry['generator']['recipe'])['glb'], result['glb'])
            check(generator.dealership, output)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                generator.save(result, output=output)
            self.assertEqual({p.name: p.read_bytes() for p in (generator.dealership / 'models').iterdir()
                              if p.name in before}, before)
            empty = Path(folder) / 'empty'
            (empty / 'models').mkdir(parents=True)
            (empty / 'catalog.json').write_text('[]\n')
            Generator(empty, generator.assets).save(result, output=Path(folder) / 'empty-display/cars.json')
            self.assertEqual(len(json.loads((empty / 'catalog.json').read_text())), 1)

    def test_asymmetric_and_floating_controls_cannot_be_saved(self):
        import hashlib
        import struct
        from bake_models import read_glb
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            generator.prepare()
            generator.train(epochs=1, device='cpu')
            result = generator.generate(seed=35)
            before = (generator.dealership / 'catalog.json').read_bytes()
            for control in ['asymmetric', 'floating', 'open body']:
                doc, binary = read_glb(result['glb'])
                for node in doc['nodes']:
                    if control == 'asymmetric' and node['name'] == 'Generated body':
                        node['translation'] = [.2, 0, 0]
                    if control == 'floating' and node['name'].startswith('WHEEL_'):
                        node['translation'] = [0, .2, 0]
                    if control == 'open body' and node['name'] == 'Generated body':
                        primitive = doc['meshes'][node['mesh']]['primitives'][0]
                        doc['accessors'][primitive['indices']]['count'] -= 3
                text = json.dumps(doc).encode()
                text += b' ' * (-len(text) % 4)
                glb = struct.pack('<5I', 0x46546C67, 2, 28 + len(text) + len(binary), len(text), 0x4E4F534A)
                glb += text + struct.pack('<2I', len(binary), 0x004E4942) + binary
                mutated = {**result, 'glb': glb, 'code': 'GEN_' + hashlib.sha256(glb).hexdigest()[:16].upper()}
                with self.assertRaisesRegex(ValueError, 'save validation'):
                    generator.save(mutated, output=Path(folder) / 'display/cars.json')
                self.assertEqual((generator.dealership / 'catalog.json').read_bytes(), before)
                self.assertFalse((generator.dealership / 'models' / (mutated['code'] + '.glb')).exists())

    def test_uncertain_non_car_stays_in_review_and_reversed_body_is_excluded(self):
        from bake_models import read_glb
        import struct
        class Uncertain(FakeJudge):
            def classify(self, entries):
                result = super().classify(entries)
                for row in result.values():
                    row['car_probability'] = .5
                return result
        with tempfile.TemporaryDirectory() as folder:
            generator = self.fixture(folder)
            generator.judge = Uncertain()
            model = generator.dealership / 'models/GT_SIMULATION__A_A7R_DAY.glb'
            doc, binary = read_glb(model.read_bytes())
            root = doc['scenes'][doc['scene']]['nodes'][0]
            doc['nodes'][root]['scale'] = [1, 1, -1]
            text = json.dumps(doc).encode()
            text += b' ' * (-len(text) % 4)
            data = struct.pack('<5I', 0x46546C67, 2, 28 + len(text) + len(binary), len(text), 0x4E4F534A)
            model.write_bytes(data + text + struct.pack('<2I', len(binary), 0x004E4942) + binary)
            result = generator.prepare()
            self.assertEqual(result['entries'], [])
            self.assertEqual(len(result['review']), 3)
            self.assertIn('front/back-reversed transform', [e['reason'] for e in result['excluded']])

    def test_prepare_distinct_real_shapes_without_changing_catalog(self):
        source = ROOT / 'dealership/dealership'
        catalog = json.loads((source / 'catalog.json').read_text())
        codes = ['GRAN_TORINO', 'GT_SIMULATION__A_A7R_DAY', 'GT_SIMULATION__A_A7R_NIGHT',
                 'REDLINE_BASE_500GT_5BB660DF8232_CD2320C0A42673C7', 'MC3_VP_350Z_04']
        entries = [e for e in catalog if e['code'] in codes]
        self.assertEqual(len(entries), 5)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / 'dealership'
            (work / 'models').mkdir(parents=True)
            entries.append({'code': 'GEN_FAKE', 'name': 'Previously generated'})
            original = json.dumps(entries).encode()
            (work / 'catalog.json').write_bytes(original)
            for entry in entries[:-1]:
                (work / 'models' / (entry['code'] + '.glb')).write_bytes(
                    (source / 'models' / (entry['code'] + '.glb')).read_bytes())
            result = Generator(work, Path(folder) / 'generator', judge=FakeJudge()).prepare()
            self.assertEqual(len(result['entries']), 4)
            self.assertEqual({e['game'] for e in result['entries']},
                             {'ford-racing-2', 'gran-turismo', 'redline', 'midnight-club-3-remix'})
            for entry in result['entries']:
                self.assertEqual(entry['wheel_count'], 4)
                self.assertEqual(entry['wheel_coverage'], 1.)
                self.assertGreater(entry['wheelbase'], 0)
                self.assertEqual(len(entry['glb_sha256']), 64)
                self.assertEqual(entry['grid_shape'], [64, 64, 64])
            self.assertEqual((work / 'catalog.json').read_bytes(), original)
            self.assertEqual({e['reason'] for e in result['excluded']}, {'duplicate shape', 'generated model'})


if __name__ == '__main__':
    import sys
    if '--committed-weights' in sys.argv:
        from generator_runtime import freshness
        freshness()
        generator = Generator()
        preview_files = tempfile.TemporaryDirectory(prefix='generator-preview-')
        for method in ['shape space', 'network']:
            scores = []
            for novelty in [0, .35, 1]:
                result = generator.generate(method=method, seed=35, novelty=novelty)
                assert result['validation']['passed']
                assert 8000 <= result['body_vertices'] <= 12000
                scores.append(result['novelty_score'])
            assert scores == sorted(scores), (method, scores)
            assert scores[0] < scores[-1], (method, scores)
            assert generator.generate(method=method, seed=1006, novelty=0)['validation']['passed']
            from bake_models import read_glb, accessor
            import math
            for sample in [result, generator.generate(method=method, seed=1002, novelty=0)]:
                doc, binary = read_glb(sample['glb'])
                for mesh in doc['meshes']:
                    for primitive in mesh['primitives']:
                        normals = accessor(doc, binary, primitive['attributes']['NORMAL'], 3, 5126)
                        assert all(math.sqrt(sum(v*v for v in n)) > 1e-8 for n in normals)
            replay = generator.generate(**result['recipe'])
            assert replay['glb'] == result['glb']
            for i, seed in enumerate([35, 1002, 1006]):
                output = generator.generate(method=method, seed=seed, novelty=.35)
                (Path(preview_files.name) / (method.replace(' ', '-') + str(i) + '.glb')).write_bytes(output['glb'])
            print('PASS committed fixed-seed generation:', method, scores)
        import subprocess
        subprocess.run(['node', str(ROOT / 'tools/test_generator_preview.mjs'), preview_files.name], check=True)
        preview_files.cleanup()
    else:
        unittest.main()
