"""Decoding verifier on a synthetic one-car extraction built from the reader tests' resources."""
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import mcla_model
import mcla_texture
from test_mcla_lzx import Encoder, resource
from test_mcla_model import build as build_model
from test_mcla_resource import Builder
from test_mcla_texture import build_dictionary, build_pack
from test_mcla_tuning import build as build_tuning
import verify_mcla_decoding
from verify_mcla_decoding import VerifyError, derive, main, tuning_layout

CAR = 'vp_a'
PACKAGE = CAR + '/resources/vehicle/' + CAR + '/'


def compress(data, kind):
    encoder = Encoder()
    encoder.stored(bytes(data))
    return resource(encoder.body(), len(data), kind=kind)


def model(shader=0):
    data, _, _, at = build_model()
    shaders = struct.unpack_from('>I', data, at['model'] + 0x10)[0] & 0x0FFFFFFF
    struct.pack_into('>HH', data, shaders, shader, shader)
    return data


def streaming_map():
    b = Builder()
    field = b.alloc(8)
    b.put(field, 'IHH', b.pointer(b.text('hood0_lod_0')), 11, 16)
    return b.segment()[0]


def files(xtl=None, shader=0, tuning=True):
    out = {PACKAGE + 'body_lod_0.xrsc': (63, model(shader)), PACKAGE + CAR + '.xtp': (83, build_pack()[0]),
           PACKAGE + CAR + '.xspm': (19, streaming_map()),
           CAR + '/resources/ui/textures/garage/mr_' + CAR + '.xtd': (9, build_dictionary()[0]),
           'shared/resources/rims/whl_x/body_lod_0.xrsc': (63, model())}
    if tuning:
        out[PACKAGE + CAR + '.xct'] = (50, build_tuning()[0])
    if xtl is not False:
        out[PACKAGE + CAR + '.xtl'] = (83, xtl if xtl is not None else build_pack()[0])
    return out


def extraction(root, content):
    rows = []
    for relative, (kind, data) in sorted(content.items()):
        stored = compress(data, kind)
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(stored)
        rows.append({'file': relative, 'bytes': len(stored), 'sha256': hashlib.sha256(stored).hexdigest(),
                     'source': {'resource_type': kind}})
    rows.append({'file': CAR + '/manifest.json', 'bytes': 2, 'sha256': '0' * 64})
    (root / 'index.json').write_text(json.dumps({'source': {'sha256': 'd' * 64}, 'vehicles': [{'id': CAR}], 'files': rows}))
    return root


class DecodingVerifier(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def use(self, content):
        cars = extraction(self.root / 'cars', content)
        for name, value in (('CARS', cars), ('RECEIPT', self.root / 'receipt.json'), ('ROOT', self.root)):
            p = patch.object(verify_mcla_decoding, name, value)
            p.start()
            self.addCleanup(p.stop)
        return cars

    def test_receipt_facts_joins_and_controls(self):
        self.use(files())
        receipt = derive(1)
        totals = receipt['totals']
        self.assertEqual(totals['model']['files'], 2)
        self.assertEqual((totals['model']['vertices'], totals['model']['triangles']), (14, 6))
        self.assertEqual((totals['texture-pack']['files'], totals['texture-pack']['textures']), (2, 6))
        self.assertEqual((totals['streaming-map']['strings'], totals['tuning']['files']), (1, 1))
        car, = receipt['cars']
        self.assertEqual((car['models'], car['vertices'], car['shader_count'], car['streaming_map_strings']), (1, 7, 1, 1))
        self.assertEqual(car['body']['bones'], 2)
        self.assertEqual(len(car['tuning_sections']), 17)
        self.assertEqual(receipt['tuning_layout'][6]['class'], 'vehSim')
        self.assertEqual(receipt['tuning_layout'][6]['field_types'], {'float': 2, 'int': 1, 'nan': 1, 'pointer': 1, 'zero': 1})
        self.assertEqual(len(receipt['controls']), 13)
        self.assertTrue(all(c['rejected'] for c in receipt['controls']))

    def test_main_writes_and_reproduces(self):
        self.use(files())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--write', '--processes=1']), 0)
            self.assertEqual(main(['--processes=2']), 0)
        self.assertEqual(main(['--available']), 0)

    def test_joins_and_pins(self):
        cases = [(files(xtl=False), 'missing .xtp or .xtl'), (files(shader=3), 'outside the .xtp shader group'),
                 (files(tuning=False), 'missing body model or tuning')]
        other = build_pack()[0]
        name = other.find(b'BumpSpec')
        other[name:name + 8] = b'BumpXpec'
        cases.append((files(xtl=other), 'shader lists differ'))
        for content, message in cases:
            with self.subTest(message):
                self.use(content)
                with self.assertRaisesRegex(VerifyError, message):
                    derive(1)
        cars = self.use(files())
        path = cars / (PACKAGE + 'body_lod_0.xrsc')
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(bytes(data))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(['--processes=1']), 1)
        self.assertIn('differs from the committed index', out.getvalue())

    def test_missing_extraction(self):
        with patch.object(verify_mcla_decoding, 'CARS', self.root / 'absent'):
            self.assertEqual(main(['--available']), 1)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main([]), 1)
        self.assertIn('MISSING INPUT', out.getvalue())

    def test_tuning_layout_must_agree(self):
        facts = {'sections': [[0, 'vehStuck', None, 56]], 'types': [[0, ['float']]]}
        other = {'sections': [[0, 'vehStuck', None, 60]], 'types': [[0, ['float']]]}
        self.assertEqual(tuning_layout([('a', 50, '', facts), ('b', 63, '', {})])[0]['field_types'], {'float': 1})
        with self.assertRaisesRegex(VerifyError, 'differs between cars'):
            tuning_layout([('a', 50, '', facts), ('b', 50, '', other)])

    def test_controls_must_fail_for_their_reason(self):
        self.use(files())
        results = verify_mcla_decoding.decode_all(verify_mcla_decoding.selected(
            json.loads((verify_mcla_decoding.CARS / 'index.json').read_text())), 1)
        with patch.object(mcla_model, 'decode', lambda *_: None):
            with self.assertRaisesRegex(VerifyError, 'escaped'):
                verify_mcla_decoding.run_controls(results)
        original = mcla_model.decode

        def wrong(data, virtual, physical):
            if bytes(data[:4]) != struct.pack('>I', mcla_model.MODEL_VFTS[0]) or data[-1:] == b'?':
                raise mcla_model.ModelError('unrelated')
            return original(bytes(data), virtual, physical)
        with patch.object(mcla_model, 'decode', wrong):
            with self.assertRaisesRegex(VerifyError, 'another reason'):
                verify_mcla_decoding.run_controls(results)
        with patch.object(mcla_texture, 'pixels', lambda *_: b''):
            with self.assertRaisesRegex(VerifyError, 'row-major untiling'):
                verify_mcla_decoding.run_controls(results)


if __name__ == '__main__':
    unittest.main(verbosity=2)
