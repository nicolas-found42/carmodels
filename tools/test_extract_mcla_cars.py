"""Extraction controls derive expectations from a synthetic disc, never from its index."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import extract_mcla_cars
from extract_mcla_cars import Named, Output, check_extraction, dictionary, owner, write_extraction
from mcla_rpf import RSC5, Rpf3Archive, jenkins
from test_mcla_rpf import rpf_fixture
from test_xdvdfs import disc_fixture
from test_xex2 import pe_image, xex_fixture

KEY = bytes(range(100, 132))
PIN = hashlib.sha256(KEY).hexdigest()
NAMES = (b'shared_utility blur.mesh resources vehicle vp_test_car_01 vp_test_car_01_dub body_lod_0 configs ambients resources/ui/textures/garage '
         b'sh_vp_test_car_01_dub other rims whl_stk_x city tune handling.xml names.xml common.xcc '
         b'gh_01_vp_test_car_01_dub mr_vp_hidden_02 ped_fa_001_set amb')


def resource(kind, label):
    return ('resource', kind, RSC5 + b'\0\0\0' + bytes([kind]) + label)


def tree(extra_vehicle=None):
    vehicles = {
        'vp_test_car_01': {'body_lod_0.xrsc': resource(63, b'car body'), 'vp_test_car_01.xct': resource(50, b'tune'),
                           'unnamedpart.xrsc': resource(63, b'hidden part')},
        'vp_test_car_01_dub': {'body_lod_0.xrsc': resource(63, b'dub body')},
        'vp_hidden_02': {'body_lod_0.xrsc': resource(63, b'hidden car')},
        'secretdir': {'body_lod_0.xrsc': resource(63, b'unknown car')},
        'configs': {'vp_test_car_01.xcc': ('deflate', b'config one' * 30),
                    'gh_01_vp_test_car_01_dub.xcc': ('deflate', b'config dub' * 30),
                    'common.xcc': ('loose', b'shared config')}}
    vehicles.update(extra_vehicle or {})
    return {'resources': {
        'vehicle': vehicles,
        'ambients': {'vp_test_car_01': {'amb.xaph': resource(51, b'ambient')},
                     'secretdir': {'amb.xaph': resource(51, b'unresolved ambient')},
                     'ped_fa_001_set': {'amb.xaph': resource(51, b'pedestrian')}},
        'ui': {'textures': {'garage': {'sh_vp_test_car_01_dub.xtd': resource(9, b'showroom'),
                                       'other.xtd': resource(9, b'not a car')}}},
        'rims': {'whl_stk_x': {'whl_stk_x.xtp': resource(83, b'rim')}},
        'city': {'sc.xct': resource(50, b'city')}},
        'vehicle': {'shared_utility': {'blur.mesh': ('deflate', b'blur mesh')}},
        'preload': {'nested.rpf': ('deflate', rpf_fixture({'secretdir.xml': ('loose', b'secretdir unnamedpart')}))},
        'tune': {'vehicle': {'handling.xml': ('loose', b'<handling/>')}, 'names.xml': ('deflate', NAMES)}}


def fixture(path, extra_vehicle=None, archive_tree=None, with_xex=True):
    files = [('xarchive_cache.rpf', rpf_fixture(archive_tree or tree(extra_vehicle), KEY))]
    if with_xex:
        files.insert(0, ('default.xex', xex_fixture(pe_image(KEY))))
    path.write_bytes(disc_fixture(files))
    return path


class NameTests(unittest.TestCase):
    def test_plausibility_ambiguity_and_borrowed_extensions(self):
        image = rpf_fixture({'vehicle': {'part.xrsc': resource(63, b'a'), 'other.xrsc': resource(63, b'b'),
                                         'notes.xml': ('loose', b'n'), 'twin.xrsc': resource(63, b'c')}})
        archive = Rpf3Archive(lambda o, s: image[o:o + s], len(image))
        names = dictionary({'vehicle', 'part', 'notes.xml'}, {e['hash'] for e in archive.entries})
        by_hash = {e['hash']: e for e in archive.entries}
        names[jenkins('vehicle')].append('noise.xtd')        # a dotted collision for a directory
        names[jenkins('notes.xml')].append('noise.xrsc')     # a resource extension for a loose file
        names[jenkins('twin.xrsc')] = ['twin.xrsc', 'twin_b.xrsc']  # two plausible candidates
        names[jenkins('part.xrsc')].append('fake/dir.xrsc')  # a harvested path colliding with an entry
        named = Named(archive, names)
        self.assertEqual(named.name(by_hash[jenkins('vehicle')]), ('vehicle', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('notes.xml')]), ('notes.xml', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('part.xrsc')]), ('part.xrsc', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('twin.xrsc')]), ('0x%08x.xrsc' % jenkins('twin.xrsc'), 'unresolved'))
        self.assertEqual(named.name(by_hash[jenkins('other.xrsc')])[1], 'unresolved')
        rows = {row['path']: row for row in named.inventory()}
        self.assertEqual(rows['vehicle/']['rejected_candidates'], ['noise.xtd'])
        self.assertEqual(rows['vehicle/part.xrsc']['rejected_candidates'], ['fake/dir.xrsc'])
        self.assertEqual(rows['vehicle/0x%08x.xrsc' % jenkins('twin.xrsc')]['name_candidates'], ['twin.xrsc', 'twin_b.xrsc'])

    def test_colliding_paths_are_rejected(self):
        image = rpf_fixture({'a.xml': ('loose', b'a'), 'b.xml': ('loose', b'b')})
        archive = Rpf3Archive(lambda o, s: image[o:o + s], len(image))
        with self.assertRaisesRegex(ValueError, '(?i)duplicate archive path: same.xml'):
            Named(archive, {jenkins('a.xml'): ['same.xml'], jenkins('b.xml'): ['SAME.xml']})
        out = Output(lambda path, data: None)
        out.put('car/a.bin', b'1')
        with self.assertRaisesRegex(ValueError, 'duplicate output path'):
            out.put('CAR/A.bin', b'2')
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            out.put('../escape.bin', b'3')

    def test_embedded_codes_and_longest_owner(self):
        names = dictionary({'mr_vp_nsn_gtr_08'}, {jenkins('vp_nsn_gtr_08'), jenkins('vp_nsn_gtr_08.xct')})
        self.assertEqual(names, {jenkins('vp_nsn_gtr_08'): ['vp_nsn_gtr_08'],
                                 jenkins('vp_nsn_gtr_08.xct'): ['vp_nsn_gtr_08.xct']})
        codes = ['vp_lam_murcielago_06', 'vp_lam_murcielago_06_dub']
        self.assertEqual(owner('ui/sh_vp_lam_murcielago_06_dub.xtd', codes), 'vp_lam_murcielago_06_dub')
        self.assertEqual(owner('ui/sh_vp_lam_murcielago_06.xtd', codes), 'vp_lam_murcielago_06')
        self.assertIsNone(owner('ui/gh_vp_lam_murcielago_06a.xcc', codes))


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        pin = patch.object(extract_mcla_cars, 'KEY_SHA256', PIN)
        pin.start()
        self.addCleanup(pin.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def test_per_car_shared_and_provenance_layout(self):
        iso = fixture(self.root / 'source.iso')
        original = iso.read_bytes()
        index, files = write_extraction(iso, self.root / 'cars')
        hidden = 'unresolved_%08x' % jenkins('secretdir')
        self.assertEqual([v['id'] for v in index['vehicles']],
                         sorted([hidden, 'vp_hidden_02', 'vp_test_car_01', 'vp_test_car_01_dub']))
        names = {row['file'] for row in files}
        car = 'vp_test_car_01/resources/'
        unresolved = '0x%08x.xrsc' % jenkins('unnamedpart.xrsc')
        self.assertTrue({car + 'vehicle/vp_test_car_01/body_lod_0.xrsc', car + 'vehicle/vp_test_car_01/vp_test_car_01.xct',
                         car + 'vehicle/vp_test_car_01/' + unresolved, car + 'vehicle/configs/vp_test_car_01.xcc',
                         car + 'ambients/vp_test_car_01/amb.xaph',
                         'vp_test_car_01_dub/resources/vehicle/configs/gh_01_vp_test_car_01_dub.xcc',
                         'vp_test_car_01_dub/resources/ui/textures/garage/sh_vp_test_car_01_dub.xtd',
                         'vp_hidden_02/resources/vehicle/vp_hidden_02/body_lod_0.xrsc',
                         hidden + '/resources/vehicle/0x%08x/body_lod_0.xrsc' % jenkins('secretdir'),
                         hidden + '/resources/ambients/0x%08x/amb.xaph' % jenkins('secretdir'),
                         'shared/resources/vehicle/configs/common.xcc', 'shared/resources/rims/whl_stk_x/whl_stk_x.xtp',
                         'shared/tune/vehicle/handling.xml', 'shared/vehicle/shared_utility/blur.mesh',
                         'provenance/disc.inventory.json',
                         'provenance/xarchive_cache.rpf.inventory.json', 'provenance/archive-key.json',
                         'index.json'} <= names)
        self.assertFalse(any(n.endswith(('other.xtd', 'sc.xct', 'names.xml')) or 'ped_fa' in n or 'preload' in n
                             for n in names))
        # Strings inside a nested archive are not harvested, so 'secretdir' stays a hash name.
        self.assertIn(hidden, [v['id'] for v in index['vehicles']])
        self.assertEqual((self.root / 'cars' / car / 'vehicle/configs/vp_test_car_01.xcc').read_bytes(), b'config one' * 30)
        manifest = json.loads((self.root / 'cars/vp_test_car_01/manifest.json').read_text())
        sources = {row['source']['archive_path']: row['source'] for row in manifest['files']}
        self.assertEqual(sources['resources/vehicle/vp_test_car_01/' + unresolved]['name_source'], 'unresolved')
        self.assertTrue(sources['resources/vehicle/configs/vp_test_car_01.xcc']['compressed'])
        self.assertEqual(sources['resources/vehicle/vp_test_car_01/body_lod_0.xrsc']['resource_type'], 63)
        key_record = json.loads((self.root / 'cars/provenance/archive-key.json').read_text())
        self.assertEqual(key_record['key_sha256'], PIN)
        self.assertNotIn(KEY.hex(), (self.root / 'cars/provenance/archive-key.json').read_text())
        self.assertEqual(index['source']['sha1'], hashlib.sha1(original).hexdigest())
        repeated, checked = check_extraction(iso, self.root / 'cars')
        self.assertEqual(index, repeated)
        self.assertEqual(files, checked)
        self.assertEqual(iso.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, 'absent or empty'):
            write_extraction(iso, self.root / 'cars')

    def test_rewritten_index_cannot_mask_payload_tampering(self):
        iso = fixture(self.root / 'source.iso')
        output = self.root / 'cars'
        index, _ = write_extraction(iso, output)
        (output / 'vp_test_car_01/resources/vehicle/vp_test_car_01/body_lod_0.xrsc').write_bytes(b'tamper')
        index['files'] = []
        (output / 'index.json').write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, 'byte mismatch'):
            check_extraction(iso, output)

    def test_check_rejects_extra_and_linked_output(self):
        iso = fixture(self.root / 'source.iso')
        output = self.root / 'cars'
        write_extraction(iso, output)
        (output / 'shared/extra.bin').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            check_extraction(iso, output)
        (output / 'shared/extra.bin').unlink()
        (output / 'link').symlink_to(output / 'index.json')
        with self.assertRaisesRegex(ValueError, 'linked'):
            check_extraction(iso, output)

    def test_car_without_package_and_changed_disc_are_rejected(self):
        empty = fixture(self.root / 'empty.iso', {'vp_empty_car_01': {'parts': {}}})
        with self.assertRaisesRegex(ValueError, 'car without a vehicle package: unresolved_%08x' % jenkins('vp_empty_car_01')):
            write_extraction(empty, self.root / 'empty')
        iso = fixture(self.root / 'source.iso')
        digests = iter([('a' * 64, 'b' * 40), ('c' * 64, 'b' * 40)])
        with patch.object(extract_mcla_cars, 'source_digests', lambda path: next(digests)), \
                self.assertRaisesRegex(ValueError, 'disc changed during extraction'):
            write_extraction(iso, self.root / 'changed')
        self.assertFalse((self.root / 'changed').exists())

    def test_missing_disc_members_and_vehicle_tree(self):
        cases = [(fixture(self.root / 'noxex.iso', with_xex=False), 'default.xex or xarchive_cache.rpf missing'),
                 (fixture(self.root / 'novehicle.iso', archive_tree={'tune': {'names.xml': ('deflate', NAMES)}}),
                  'resources/vehicle missing'),
                 (fixture(self.root / 'nocars.iso', archive_tree={
                     'resources': {'vehicle': {'configs': {'common.xcc': ('loose', b'c')}}},
                     'tune': {'names.xml': ('deflate', NAMES)}}), 'no vehicle directories found')]
        for iso, message in cases:
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                write_extraction(iso, self.root / ('out-' + iso.stem))

    def test_destination_rules(self):
        iso = fixture(self.root / 'source.iso')
        with self.assertRaisesRegex(ValueError, 'missing or linked extraction destination'):
            check_extraction(iso, self.root / 'absent')
        (self.root / 'real').mkdir()
        (self.root / 'alias').symlink_to(self.root / 'real')
        with self.assertRaisesRegex(ValueError, 'linked extraction destination'):
            write_extraction(iso, self.root / 'alias' / 'cars')
        holder = self.root / 'holder'
        holder.mkdir()
        (holder / 'source.iso').write_bytes(iso.read_bytes())
        with self.assertRaisesRegex(ValueError, 'absent or empty'):
            write_extraction(holder / 'source.iso', holder)  # holds the input
        empty = self.root / 'empty'
        empty.mkdir()
        index, _ = write_extraction(iso, empty)  # an existing empty directory is replaced by the staged output
        self.assertTrue((empty / 'index.json').is_file())
        (empty / 'vp_test_car_01/manifest.json').unlink()
        with self.assertRaisesRegex(ValueError, 'coverage mismatch: missing vp_test_car_01/manifest.json'):
            check_extraction(iso, empty)

    def test_fresh_clone_destination_with_committed_files(self):
        iso = fixture(self.root / 'source.iso')
        reference = self.root / 'reference'
        index, files = write_extraction(iso, reference)
        clone = self.root / 'clone'
        committed = [row['file'] for row in files if row['file'] == 'index.json' or row['file'].startswith('provenance/')]
        for relative in committed:
            (clone / relative).parent.mkdir(parents=True, exist_ok=True)
            (clone / relative).write_bytes((reference / relative).read_bytes())
        repeated, _ = write_extraction(iso, clone)
        self.assertEqual(repeated, index)
        check_extraction(iso, clone)
        stale = self.root / 'stale'
        (stale / 'provenance').mkdir(parents=True)
        (stale / 'index.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'committed file differs from the derivation: index.json'):
            write_extraction(iso, stale)
        self.assertEqual(sorted(p.name for p in stale.iterdir()), ['index.json', 'provenance'], 'nothing installed')
        (stale / 'index.json').unlink()
        (stale / 'vp_test_car_01').mkdir()
        (stale / 'vp_test_car_01/manifest.json').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'absent or empty, or hold only the committed'):
            write_extraction(iso, stale)

    def test_key_pin_and_vehicle_names_are_enforced(self):
        iso = fixture(self.root / 'source.iso')
        with patch.object(extract_mcla_cars, 'KEY_SHA256', '0' * 64), \
                self.assertRaisesRegex(ValueError, 'key not found'):
            write_extraction(iso, self.root / 'wrong-key')
        odd = fixture(self.root / 'odd.iso', {'garage': {'body_lod_0.xrsc': resource(63, b'x')}})
        with self.assertRaisesRegex(ValueError, 'unexpected vehicle directory: garage'):
            write_extraction(odd, self.root / 'odd')
        self.assertFalse((self.root / 'odd').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
