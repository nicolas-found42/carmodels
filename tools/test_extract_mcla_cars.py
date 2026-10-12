"""Extraction controls derive expectations from a synthetic disc, never from its index."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import extract_mcla_cars
from extract_mcla_cars import Named, check_extraction, dictionary, owner, write_extraction
from mcla_rpf import RSC5, Rpf3Archive, jenkins
from test_mcla_rpf import rpf_fixture
from test_xdvdfs import disc_fixture
from test_xex2 import pe_image, xex_fixture

KEY = bytes(range(100, 132))
PIN = hashlib.sha256(KEY).hexdigest()
NAMES = (b'resources vehicle vp_test_car_01 vp_test_car_01_dub body_lod_0 configs ambients resources/ui/textures/garage '
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
                     'ped_fa_001_set': {'amb.xaph': resource(51, b'pedestrian')}},
        'ui': {'textures': {'garage': {'sh_vp_test_car_01_dub.xtd': resource(9, b'showroom'),
                                       'other.xtd': resource(9, b'not a car')}}},
        'rims': {'whl_stk_x': {'whl_stk_x.xtp': resource(83, b'rim')}},
        'city': {'sc.xct': resource(50, b'city')}},
        'tune': {'vehicle': {'handling.xml': ('loose', b'<handling/>')}, 'names.xml': ('deflate', NAMES)}}


def fixture(path, extra_vehicle=None):
    image = pe_image(KEY)
    path.write_bytes(disc_fixture([('default.xex', xex_fixture(image)),
                                   ('xarchive_cache.rpf', rpf_fixture(tree(extra_vehicle), KEY))]))
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
        named = Named(archive, names)
        self.assertEqual(named.name(by_hash[jenkins('vehicle')]), ('vehicle', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('notes.xml')]), ('notes.xml', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('part.xrsc')]), ('part.xrsc', 'resolved'))
        self.assertEqual(named.name(by_hash[jenkins('twin.xrsc')]), ('0x%08x.xrsc' % jenkins('twin.xrsc'), 'unresolved'))
        self.assertEqual(named.name(by_hash[jenkins('other.xrsc')])[1], 'unresolved')
        rows = {row['path']: row for row in named.inventory()}
        self.assertEqual(rows['vehicle/']['rejected_candidates'], ['noise.xtd'])
        self.assertEqual(rows['vehicle/0x%08x.xrsc' % jenkins('twin.xrsc')]['name_candidates'], ['twin.xrsc', 'twin_b.xrsc'])

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
                         'shared/resources/vehicle/configs/common.xcc', 'shared/resources/rims/whl_stk_x/whl_stk_x.xtp',
                         'shared/tune/vehicle/handling.xml', 'provenance/disc.inventory.json',
                         'provenance/xarchive_cache.rpf.inventory.json', 'provenance/archive-key.json',
                         'index.json'} <= names)
        self.assertFalse(any(n.endswith(('other.xtd', 'sc.xct', 'names.xml')) or 'ped_fa' in n for n in names))
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
    unittest.main()
