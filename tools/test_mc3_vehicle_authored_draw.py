"""Bounded authored-source execution receipt and negative carrier controls."""
import copy
import struct
import unittest

import mc3_vehicle_authored_draw as authored


class AuthoredDrawTests(unittest.TestCase):
    def test_source_receipt_binds_native_pipeline(self):
        proof = authored.source_contract()
        self.assertEqual(proof['source']['material_offset'], 25216)
        self.assertEqual(proof['source']['slot_offset'], 25344)
        altered = copy.deepcopy(proof)
        altered['source']['draw_index'] ^= 1
        with self.assertRaisesRegex(ValueError, 'receipt differs'):
            authored.source_contract(altered)

    def test_actual_positive_clipped_and_disabled_controls(self):
        cases = {row['name']: row for row in authored.source_contract()['cases']}
        self.assertEqual(set(cases), {'positive', 'clipped', 'disabled'})
        positive, clipped, disabled = (cases[key] for key in ('positive', 'clipped', 'disabled'))
        self.assertGreater(positive['coupled']['gif_bytes'], clipped['coupled']['gif_bytes'])
        self.assertGreater(clipped['coupled']['gif_bytes'], disabled['coupled']['gif_bytes'])
        self.assertEqual(positive['context']['frame_words'][:9],
                         [0x3f800000, 0, 0, 0, 0x3f800000, 0, 0, 0, 0x3f800000])
        self.assertEqual(positive['pass_limit'], 1)
        self.assertEqual(disabled['pass_limit'], 0)
        # Literal geometry must be referenced in positive/clipped executions;
        # disabled original compiled-pass control must not submit it.
        source = authored.source_contract()['source']
        packet = 152976
        self.assertEqual(source['mesh_offset'], 0x213f0)
        for case in (positive, clipped):
            self.assertIn({'kind': 3, 'address': authored.SOURCE+packet, 'bytes': 1200,
                           'sha256': 'ec4532269b5cce5f699fd76a9a7fd5566dff8972208949775cca44ecbbed812c'},
                          case['dma']['refs'])
        self.assertFalse(any(row['address'] == authored.SOURCE+packet for row in disabled['dma']['refs']))

    def test_dma_transport_keeps_tte_and_original_ref_data(self):
        ram = bytearray(0x2000000)
        struct.pack_into('<I', ram, authored.RESULT, authored.DMA+32)
        struct.pack_into('<4I', ram, authored.DMA, 0x30000001, 0x1000, 0x11000000, 0x50000001)
        struct.pack_into('<4I', ram, authored.DMA+16, 0x10000000, 0, 0, 0)
        ram[0x1000:0x1010] = bytes(range(16))
        stream, binding = authored.flatten_dma(bytes(ram))
        self.assertEqual(stream, struct.pack('<2I', 0x11000000, 0x50000001)+bytes(range(16))+bytes(8))
        self.assertEqual(binding['refs'][0]['sha256'], authored.sha(bytes(range(16))))
        struct.pack_into('<I', ram, authored.DMA, 0x70000001)
        with self.assertRaisesRegex(ValueError, 'unsupported DMA'):
            authored.flatten_dma(bytes(ram))

    def test_invalid_inputs_fail_before_native_execution(self):
        with self.assertRaisesRegex(ValueError, 'executable differs'):
            authored.from_executable(bytes(128))
        with self.assertRaisesRegex(ValueError, 'RAM extent'):
            authored.flatten_dma(bytes(128))
        with self.assertRaisesRegex(ValueError, 'DMA end'):
            authored.flatten_dma(bytes(0x2000000))


if __name__ == '__main__':
    unittest.main(verbosity=2)
