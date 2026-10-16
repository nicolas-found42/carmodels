"""Exporter boundary controls on temporary copies of exact native 350Z members."""
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

from bake_models import ROOT, read_glb
from export_mc3_models import export, refresh_tire_materials
from mc3_model import NATIVE_DISC, sha

needs_disc = unittest.skipUnless(NATIVE_DISC.is_file(), 'supplied game disc source input unavailable')


class TireMaterialRefreshTests(unittest.TestCase):
    def fixture(self, base):
        canonical = ROOT/'games/midnight-club-3-remix/recovered-models'
        index = json.loads((canonical/'index.json').read_text())
        row = copy.deepcopy(next(r for r in index['cars'] if r['code'] == 'vp_350z_04'))
        reference = base/'reference'
        reference.mkdir()
        data = (canonical/row['file']).read_bytes()
        (reference/row['file']).write_bytes(data)
        (reference/'index.json').write_text(json.dumps({**index, 'cars': [row]}))
        return reference, row, data

    def rewrite(self, reference, row, doc, binary):
        payload = json.dumps(doc, separators=(',', ':')).encode()
        payload += b' ' * (-len(payload) % 4)
        data = (struct.pack('<4sII', b'glTF', 2, 28+len(payload)+len(binary))
                + struct.pack('<I4s', len(payload), b'JSON')+payload
                + struct.pack('<I4s', len(binary), b'BIN\0')+binary)
        (reference/row['file']).write_bytes(data)
        index = json.loads((reference/'index.json').read_text())
        index['cars'][0].update(bytes=len(data), sha256=sha(data))
        (reference/'index.json').write_text(json.dumps(index))

    def test_pinned_refresh_preserves_everything_except_tire_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            reference, row, data = self.fixture(base)
            doc, binary = read_glb(data)
            self.assertIn('gamePaint', doc['extras'], 'fixture must include the current published paint edition')
            doc['extras'].pop('tireAlphaTranslation', None)
            for material in doc['materials']:
                if material.get('extras', {}).get('shader_template') == 'tire':
                    material['alphaMode'], material['alphaCutoff'] = 'MASK', 0.5
                    material['extras']['alpha_mode'] = 'MASK'
            # A valid edited node proves the metadata refresh retains geometry edits.
            doc['nodes'][0]['translation'] = [1, 2, 3]
            self.rewrite(reference, row, doc, binary)
            before = {p.name: p.read_bytes() for p in reference.iterdir()}
            self.assertEqual(refresh_tire_materials(reference, base/'output'), 1)
            updated, updated_binary = read_glb((base/'output'/row['file']).read_bytes())
            self.assertEqual(updated_binary, binary)
            self.assertEqual(updated['extras']['tireAlphaTranslation']['policy'], 'native-ps2-tire-reflection-v2')
            self.assertEqual(updated['extras']['tireAlphaTranslation']['alpha_test'], 'always')
            refreshed = json.loads((base/'output'/'index.json').read_text())['cars'][0]
            self.assertFalse(any('native tire.shadert alpha semantics remain unresolved' in v
                                 for v in refreshed['claim_limits']))
            extras = copy.deepcopy(updated['extras'])
            extras.pop('tireAlphaTranslation')
            self.assertEqual(extras, doc['extras'], 'all native appearance and source metadata survive')
            for key in ('nodes', 'meshes', 'accessors', 'bufferViews', 'buffers', 'images', 'textures', 'samplers', 'extensions'):
                self.assertEqual(updated.get(key), doc.get(key), key)
            for old, new in zip(doc['materials'], updated['materials'], strict=True):
                if old.get('extras', {}).get('shader_template') == 'tire':
                    self.assertEqual(new['alphaMode'], 'OPAQUE')
                    self.assertFalse(new['doubleSided'])
                    self.assertNotIn('alphaCutoff', new)
                    self.assertEqual(new['pbrMetallicRoughness'], old['pbrMetallicRoughness'])
                    self.assertIn('alpha test is ALWAYS', new['extras']['texture_policy_note'])
                else:
                    self.assertEqual(old, new)
            self.assertEqual(before, {p.name: p.read_bytes() for p in reference.iterdir()})
            with self.assertRaisesRegex(ValueError, 'must not exist'):
                refresh_tire_materials(reference, base/'output')
            with self.assertRaisesRegex(ValueError, 'separate'):
                refresh_tire_materials(reference, reference/'nested')

    def test_bad_pins_and_forged_tire_ownership_never_publish(self):
        for mutation in ('pin', 'identity', 'ownership'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                base = Path(temp).resolve()
                reference, row, data = self.fixture(base)
                doc, binary = read_glb(data)
                if mutation == 'pin':
                    (reference/row['file']).write_bytes(data+b'changed')
                    reason = 'hash/size'
                else:
                    if mutation == 'identity':
                        doc['extras']['car'] = 'vp_wrong'
                        reason = 'identity/records'
                    else:
                        tire = next(m for m in doc['materials'] if m.get('extras', {}).get('shader_template') == 'tire')
                        tire['extras']['shader_template'] = 'lit_textured'
                        reason = 'ownership'
                    self.rewrite(reference, row, doc, binary)
                with self.assertRaisesRegex(ValueError, reason):
                    refresh_tire_materials(reference, base/'output')
                self.assertFalse((base/'output').exists())

    def test_missing_native_normals_or_shared_body_material_never_publish(self):
        for mutation in ('normals', 'sharing'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                base = Path(temp).resolve()
                reference, row, data = self.fixture(base)
                doc, binary = read_glb(data)
                if mutation == 'normals':
                    tire = next(n for n in doc['nodes'] if n.get('extras', {}).get('nativeWheelComponent') == 'tire')
                    doc['meshes'][tire['mesh']]['primitives'][0]['attributes'].pop('_MC3_NATIVE_NORMAL')
                    reason = 'normals missing'
                else:
                    rim = next(n for n in doc['nodes'] if n.get('extras', {}).get('nativeWheelComponent') == 'rim')
                    body = next(n for n in doc['nodes'] if 'mesh' in n and 'nativeWheelComponent' not in n.get('extras', {}))
                    doc['meshes'][body['mesh']]['primitives'][0]['material'] = doc['meshes'][rim['mesh']]['primitives'][0]['material']
                    reason = 'wheel/body material sharing'
                self.rewrite(reference, row, doc, binary)
                with self.assertRaisesRegex(ValueError, reason):
                    refresh_tire_materials(reference, base/'output')
                self.assertFalse((base/'output').exists())


class ExportBoundaryTests(unittest.TestCase):
    def fixture(self, base):
        native = ROOT / 'games/midnight-club-3-remix/cars'
        index = json.loads((native / 'index.json').read_text())
        vehicle = next(v for v in index['vehicles'] if v['id'] == 'vp_350z_04')
        manifest = json.loads((native / vehicle['manifest']).read_text())
        source = base / 'source'
        (source / 'members').mkdir(parents=True)
        members = []
        for row in manifest['members']:
            if row['file'].endswith('.pck'):
                target = source / 'members' / Path(row['file']).name
                shutil.copyfile(native / row['file'], target)
                members.append({**row, 'file': target.relative_to(source).as_posix()})
        manifest = {**manifest, 'members': members}
        wheel_sources = {vehicle['id'] + '.carcfg', 'decal.pck', 'rim.ppf', 'tire.ppf', 'vehicle.lst'}
        shared = [row for row in index['files'] if row['file'].startswith('shared/')
                  and Path(row['file']).name in wheel_sources]
        self.assertEqual({Path(row['file']).name for row in shared}, wheel_sources)
        for row in shared:
            target = source / row['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(native / row['file'], target)
        index = {**index, 'vehicles': [{**vehicle, 'manifest': vehicle['id'] + '/manifest.json'}], 'files': shared}
        self.write_fixture(source, index, manifest)
        return source, index, manifest

    def write_fixture(self, source, index, manifest):
        manifest_path = source / 'vp_350z_04/manifest.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest))
        (source / 'index.json').write_text(json.dumps(index))

    def reject(self, source, output, reason):
        with self.assertRaisesRegex(ValueError, reason):
            export(source, output)
        self.assertFalse(output.exists(), 'rejected export must not publish output')

    @needs_disc
    def test_parent_and_absolute_member_paths_reject_before_output(self):
        for absolute in (False, True):
            with self.subTest(absolute=absolute), tempfile.TemporaryDirectory() as temp:
                base = Path(temp).resolve()
                source, index, manifest = self.fixture(base)
                payload = base / 'payload'
                shutil.copytree(source / 'members', payload)
                for row in manifest['members']:
                    name = Path(row['file']).name
                    row['file'] = str(payload / name) if absolute else '../payload/' + name
                self.write_fixture(source, index, manifest)
                self.reject(source, base / 'output', 'path|relative|outside|boundary')

    @needs_disc
    def test_symlink_member_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, _, manifest = self.fixture(base)
            member = source / manifest['members'][0]['file']
            outside = base / member.name
            member.rename(outside)
            member.symlink_to(outside)
            self.reject(source, base / 'output', 'symlink|path|outside|boundary')

    @needs_disc
    def test_hardlinked_member_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, _, manifest = self.fixture(base)
            member = source / manifest['members'][0]['file']
            os.link(member, base / 'linked-member.pck')
            self.reject(source, base / 'output', 'independent file')

    def test_duplicate_vehicle_identity_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, index, manifest = self.fixture(base)
            index['vehicles'].append(copy.deepcopy(index['vehicles'][0]))
            self.write_fixture(source, index, manifest)
            self.reject(source, base / 'output', 'duplicat|identity|ambiguous')

    def test_manifest_parent_path_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, index, manifest = self.fixture(base)
            (base / 'manifest.json').write_text(json.dumps(manifest))
            index['vehicles'][0]['manifest'] = '../manifest.json'
            self.write_fixture(source, index, manifest)
            self.reject(source, base / 'output', 'identity')

    @needs_disc
    def test_missing_indexed_wheel_occurrence_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, index, _ = self.fixture(base)
            copies = [row for row in index['files'] if Path(row['file']).name == 'rim.ppf']
            self.assertEqual(len(copies), 2)
            (source / copies[-1]['file']).unlink()
            self.reject(source, base / 'output', 'occurrence|coverage|missing')

    @needs_disc
    def test_undeclared_wheel_occurrence_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, index, _ = self.fixture(base)
            row = next(row for row in index['files'] if Path(row['file']).name == 'rim.ppf')
            extra = source / 'shared/undeclared/rim.ppf'
            extra.parent.mkdir()
            shutil.copyfile(source / row['file'], extra)
            self.reject(source, base / 'output', 'occurrence|coverage|wheel source differs')

    @needs_disc
    def test_valid_export_repeats_and_preserves_changed_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            source, _, _ = self.fixture(base)
            output = base / 'output'
            self.assertEqual(export(source, output), 1)
            row = json.loads((output / 'index.json').read_text())['cars'][0]
            self.assertFalse(row['wheels']['bike'])
            self.assertEqual(len(row['wheels']['slots']), 4)
            document, _ = read_glb((output / row['file']).read_bytes())
            for slot in row['wheels']['slots']:
                nodes = [node for node in document['nodes']
                         if node['extras'].get('nativeBone') == slot['bone']
                         and 'nativeWheelComponent' in node['extras']]
                self.assertEqual({node['extras']['nativeWheelComponent'] for node in nodes}, {'rim', 'tire'})
            self.assertEqual(export(source, output), 0)
            model = output / 'vp_350z_04.glb'
            model.write_bytes(model.read_bytes() + b'user edit')
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(ValueError, 'differs; nothing overwritten'):
                export(source, output)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
