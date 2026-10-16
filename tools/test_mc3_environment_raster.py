"""Original VIF lane retention and independent-runtime job boundaries."""

import copy
import base64
import hashlib
import json
from pathlib import Path
import struct
import unittest

from mc3_environment_raster import (
    EVIDENCE, batch_patches, decode_transport, encode_ee_job, encode_job, geometry_patches,
    source_contract, source_packet,
)


class NativeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.pack = json.loads((root / 'dealership/public/midnight-club-3-remix/environment/'
                              'native-garage.json').read_text())
        cls.floor = [x for x in cls.pack['draws'] if x['material_index'] == 8]

    def test_contract_guardband_depth_and_transport(self):
        value = source_contract()
        self.assertEqual(value['guardband_xy_scale'], .25)
        self.assertEqual(value['viewport_xy_scale_multiplier'], 4)
        self.assertEqual(value['display_depth_bits'], 16)
        self.assertEqual(value['zbuf_psm'], 'PSMZ16S')
        self.assertEqual(value['packed_registers'], ['ST', 'RGBAQ', 'XYZF2'])
        self.assertEqual(value['packed_register_list'], 0x412)

    def test_source_proof_tamper_rejected_before_use(self):
        proof = json.loads(EVIDENCE.read_text())
        for mutate in ('z', 'clip', 'word', 'interval'):
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(proof)
                if mutate == 'z':
                    changed['contract']['display_depth_bits'] = 32
                elif mutate == 'clip':
                    changed['contract']['guardband_xy_scale'] = 1
                elif mutate == 'word':
                    changed['selected_vu_instructions'][0]['upper'] ^= 1
                else:
                    del changed['source_intervals']['matrix_upload']
                with self.assertRaisesRegex(ValueError, 'source receipt changed'):
                    source_contract(receipt=changed)

    def test_original_batch_lane_bits_and_itop(self):
        self.assertEqual(len(self.floor), 4)
        for i, draw in enumerate(self.floor):
            origin, patches = batch_patches(self.pack, draw['native'])
            self.assertEqual(origin, (0x9E, 0x1C5)[i % 2])
            self.assertEqual(struct.unpack_from('<4I', patches[0][1]),
                             (draw['native']['header_words'][0],) * 4)
            # The low ADC bit remains in UV.X, including signed native values.
            self.assertEqual(struct.unpack_from('<i', patches[2][1])[0],
                             draw['native']['uv_integers'][0][0])
            self.assertEqual(struct.unpack_from('<i', patches[3][1], 12)[0], -1)

    def test_packet_tamper_and_model_written_lane_tamper(self):
        native = self.floor[0]['native']
        pack = copy.deepcopy(self.pack)
        pack['native_packets'][native['packet']]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'packet identity mismatch'):
            source_packet(pack, native)
        altered = copy.deepcopy(native)
        altered['uv_integers'][0][0] &= ~1
        with self.assertRaisesRegex(ValueError, 'source lanes changed'):
            batch_patches(self.pack, altered)

    def test_normal_w_mask_change_fails_even_if_packet_hash_is_updated(self):
        pack = copy.deepcopy(self.pack)
        native = self.floor[0]['native']
        record = pack['native_packets'][native['packet']]
        raw = bytearray(base64.b64decode(record['data_base64']))
        pattern = struct.pack('<7I', 0x20000000, 0x40404040, 0x30000000, 0, 0, 0, 0xFFFFFFFF)
        at = raw.index(pattern)
        struct.pack_into('<I', raw, at + 24, 0)
        record['data_base64'] = base64.b64encode(raw).decode()
        record['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'normal W mask changed'):
            batch_patches(pack, native)

    def test_all_source_geometry_including_delta_and_fill_planes(self):
        for draw in self.pack['draws'] + self.pack['sky']['draws']:
            origin, patches = geometry_patches(self.pack, draw['native'])
            self.assertIn(origin, (0x98, 0x9E, 0x1C5))
            self.assertTrue(patches)
        # This retained source batch mixes signed delta bytes and absolute
        # thirty-two-bit escapes; treating unsigned escape words as new floats
        # would change the original geometry.
        native = self.pack['draws'][223]['native']
        self.assertLess(native['position_integers'][40][0], 0)
        self.assertEqual(len(native['position_integers']), 45)

    def test_runtime_job_keeps_raw_float_words(self):
        mem = bytearray(16384)
        struct.pack_into('<I', mem, 64, 0x80000000)  # Preserve signed zero.
        patch = struct.pack('<I', 0xBF000001)
        job = encode_job(bytes(16384), mem, [{'pc': 6, 'top': 0, 'itop': 158,
                                            'patches': [(1600, patch)]}])
        self.assertEqual(job[:8], b'MC3VU001')
        self.assertEqual(job[8 + 16384 + 64:8 + 16384 + 68], b'\0\0\0\x80')
        self.assertEqual(job[-4:], patch)
        self.assertNotEqual(hashlib.sha256(job).digest(), hashlib.sha256(job[:-1] + b'\0').digest())

    def test_runtime_job_rejects_out_of_range_context(self):
        for call in [{'pc': 2048, 'top': 0, 'itop': 0},
                     {'pc': 6, 'top': 0, 'itop': 1024},
                     {'pc': 6, 'top': 0, 'itop': 0, 'patches': [(16383, b'ab')]}]:
            with self.subTest(call=call), self.assertRaises(ValueError):
                encode_job(bytes(16384), bytes(16384), [call])

    def test_ee_job_uses_literal_fpr_bits_and_ram_boundaries(self):
        job = encode_ee_job(0x240090, {4: 0x1000000}, [(0x1000100, b'abcd')], {12: 0x80000000})
        self.assertEqual(job[:8], b'MC3EE001')
        self.assertEqual(struct.unpack_from('<II', job, 48), (12, 0x80000000))
        with self.assertRaisesRegex(ValueError, 'outside RAM'):
            encode_ee_job(0x240090, {}, [(32 * 1024 * 1024 - 1, b'ab')])

    def test_transport_preserves_chunks_and_rejects_truncation(self):
        original = bytes(range(16))
        self.assertEqual(decode_transport(struct.pack('<I', 16) + original), [original])
        for data in [b'', b'\0', struct.pack('<I', 15) + original,
                     struct.pack('<I', 32) + original, struct.pack('<I', 0)]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_transport(data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
