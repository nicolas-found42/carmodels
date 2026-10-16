"""Native garage pack assembly guards and original committed input coverage."""
import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from mc3_environment import (NATIVE_CAPTURE, OUTPUT, build_pack, capture_input_sha256,
                             encode, load_native_capture)
from mc3_garage import decode_batches
from mc3_pck import Pck, vif_planes


class PackTests(unittest.TestCase):
    def test_executed_fixture_refuses_tamper_and_different_source_inputs(self):
        pack = json.loads(OUTPUT.read_text())
        proof = json.loads(NATIVE_CAPTURE.read_text())
        self.assertEqual(load_native_capture(pack), pack['native_gs'])
        changed = copy.deepcopy(proof)
        changed['native_gs']['passes'][0]['gif_chunks'][0] = ''
        with self.assertRaisesRegex(ValueError, 'fixture changed'):
            load_native_capture(pack, changed)
        changed_pack = copy.deepcopy(pack)
        changed_pack['camera']['eye'][1] = 2
        with self.assertRaisesRegex(ValueError, 'input binding differs'):
            load_native_capture(changed_pack)
        for mutate, reason in [
                (lambda p: p['native_gs']['passes'].pop(), 'batch coverage'),
                (lambda p: p['visibility_controls']['0'].pop(), 'source coverage'),
                (lambda p: p['visibility_controls'].pop('192'), 'controls are incomplete')]:
            changed = copy.deepcopy(proof)
            mutate(changed)
            digest = hashlib.sha256(json.dumps(changed, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            with patch('mc3_environment.NATIVE_CAPTURE_SHA', digest):
                with self.assertRaisesRegex(ValueError, reason):
                    load_native_capture(pack, changed)

    def test_committed_native_pixels_and_complete_selected_geometry(self):
        pack = json.loads(OUTPUT.read_text())
        self.assertEqual(pack['source']['city']['sha256'], '35f432cb3134367bb1f12caf59fe1b2e7fac3e37c9a9433392915696f197c116')
        self.assertEqual(pack['source']['props']['sha256'], '243545f947d6de0a842d52a958d0d433cb8b405029d5c0064ccbf24140ccd425')
        self.assertGreater(len({d['material_index'] for d in pack['draws']}), 3)
        for image in [*pack['images'].values(), *pack['sky']['images'].values()]:
            data = base64.b64decode(image['rgba_base64'])
            self.assertEqual(len(data), image['width'] * image['height'] * 4)
            self.assertEqual(hashlib.sha256(data).hexdigest(), image['rgba_sha256'])
            self.assertLessEqual(max(data[3::4]), 128)
        self.assertEqual(pack['images']['panorama']['rgba_sha256'], 'c3d531f33e64bf1525711700feadd76f49ea2251d5ed1cf04654711975ed7c0e')
        self.assertEqual(encode(pack), OUTPUT.read_bytes())

    def test_native_packet_lanes_rederive_before_host_transform(self):
        pack = json.loads(OUTPUT.read_text())
        self.assertEqual(pack['native_input_schema'], 1)
        decoded = {}
        # VIF decoding only needs the bounded byte carrier, not PCK relocation.
        for key, record in pack['native_packets'].items():
            raw = base64.b64decode(record['data_base64'])
            self.assertEqual(len(raw), record['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), record['sha256'])
            carrier = object.__new__(Pck)
            carrier.data = bytes(128) + raw
            decoded[key] = decode_batches(vif_planes(carrier, 128, len(raw)))
        fields = ['header_words', 'position_integers', 'uv_integers',
                  'normal_integers', 'color_integers', 'adc', 'world_layout']
        for draw in [*pack['draws'], *pack['sky']['draws']]:
            native = draw['native']
            matches = [b for b in decoded[native['packet']]
                       if b['packet_offset'] - 128 == native['batch_offset']]
            self.assertEqual(len(matches), 1)
            for name in fields:
                self.assertEqual(json.loads(json.dumps(matches[0][name])), native[name])
            self.assertEqual(matches[0]['scale'], native['position_scale'])
        floor = [d['native'] for d in pack['draws'] if d['material_index'] == 8]
        self.assertEqual(sum(len(b['position_integers']) for b in floor), 192)
        self.assertTrue(any(row[0] & 1 for b in floor for row in b['uv_integers']),
                        'encoded UV.X ADC bits remain in the native source lanes')

    def test_refuse_missing_nonfinite_and_unsupported_source_state(self):
        # The source decoders have separate original-fragment controls. This seam
        # tests that the producer does not silently invent absent authored inputs.
        pack = json.loads(OUTPUT.read_text())
        garage = {'instances': [], 'materials': {'8': {'template': 'wrong', 'passes': []}}}
        sky = {'native_initial_state': {}, 'primitives': [], 'textures': {}}
        with patch('mc3_environment.decode_garage', return_value=garage), patch('mc3_environment.decode_sky', return_value=sky):
            for settings, reason in [(b'', 'transform missing'), (b'CarSpotsd 1 2 3 CarAnglesd 1e999', 'nonfinite')]:
                with self.assertRaisesRegex(ValueError, reason):
                    build_pack(b'city', b'props', b'panorama', settings)
            garage['materials']['8'] = {'template': 'garage_lightmap_subtract_reflectingground',
                                       'passes': [{'textures': [{'name': 'wrong'}]}]*2}
            with self.assertRaisesRegex(ValueError, 'texture ownership'):
                build_pack(b'', b'', b'', b'CarSpotsd 1 2 3 CarAnglesd 1')
        changed = copy.deepcopy(pack)
        changed['images']['panorama']['rgba_base64'] = ''
        self.assertNotEqual(encode(changed), OUTPUT.read_bytes())

    def test_native_execution_binding_tracks_inputs_and_ignores_host_projection(self):
        pack = json.loads(OUTPUT.read_text())
        digest = capture_input_sha256(pack)
        for mutate in [
                lambda p: p['camera']['eye'].__setitem__(1, 2),
                lambda p: p['draws'][0]['native']['uv_integers'][0].__setitem__(0, 99),
                lambda p: p['sky']['draws'][0]['native']['instance_translation'].__setitem__(0, 0),
                lambda p: p['images']['floorBase'].__setitem__('rgba_sha256', '0'*64),
                lambda p: next(iter(p['native_packets'].values())).__setitem__('data_base64', '')]:
            changed = copy.deepcopy(pack)
            mutate(changed)
            self.assertNotEqual(capture_input_sha256(changed), digest)
        changed = copy.deepcopy(pack)
        changed['draws'][0]['positions'][0] += 100
        changed['native_raster'] = {'untrusted': 'not part of its own input binding'}
        self.assertEqual(capture_input_sha256(changed), digest)


if __name__ == '__main__':
    unittest.main(verbosity=2)
