#!/usr/bin/env python3
"""Mutation controls for the native MC3 tire VU alpha contract."""
import copy
import json
import struct
from pathlib import Path
import unittest

import mc3_tire_vu as tire


class TireVUTests(unittest.TestCase):
    def setUp(self):
        self.parts = tire.source_parts()

    def change_word(self, key, address, value):
        if key == 'microprogram':
            rows = json.loads(tire.FIXTURE.read_text())['source_intervals'][key]['selected_instruction_proof']
            for row in rows:
                if row['address'] <= address <= row['address'] + 4:
                    pair = list(self.parts[key][row['pc']])
                    pair[(address - row['address']) // 4] = value
                    self.parts[key][row['pc']] = tuple(pair)
                    return
            raise AssertionError('mutation address outside selected VU proof')
        raw = bytearray(self.parts[key])
        struct.pack_into('<I', raw, address - tire.INTERVALS[key][0], value)
        self.parts[key] = bytes(raw)

    def test_original_native_contract(self):
        result = tire.derive(self.parts)
        self.assertEqual(result['program_pairs'], 1081)
        self.assertEqual(result['light_rgba_w'], [0, 0, 0, 1])
        self.assertEqual(result['base_rgbaq_alpha'], 128)
        self.assertEqual(result['reflection_rgbaq'], [127, 127, 127, 0])
        self.assertEqual(result['culling']['selector_table'], [0, 128, 192])

    def synthetic_packet(self, overlap=False):
        payload = bytearray()
        for start, count in [(0, 256), (255 if overlap else 256, 256), (512, 256), (768, 256), (1024, 57)]:
            payload += struct.pack('<II', 0, 0x4A000000 | ((count & 255) << 16) | start)
            payload += struct.pack('<II', 0x8000033C, 0x000002FF) * count
        payload += bytes(-len(payload) % 16)
        return struct.pack('<4I', 0x60000000 | (len(payload) // 16), 0, 0, 0) + payload

    def test_five_synthetic_mpg_uploads_reconstruct_contiguous_program(self):
        pairs = tire.unpack_microprogram(self.synthetic_packet())
        self.assertEqual(set(pairs), set(range(1081)))
        self.assertEqual(pairs[1080], (0x8000033C, 0x000002FF))

    def test_changed_dma_size_rejected(self):
        raw = bytearray(self.synthetic_packet())
        struct.pack_into('<I', raw, 0, 0x6000021E)
        with self.assertRaisesRegex(ValueError, 'QWC mismatch'):
            tire.unpack_microprogram(bytes(raw))

    def test_unexpected_vif_command_rejected(self):
        raw = bytearray(self.synthetic_packet())
        struct.pack_into('<I', raw, 20, 0x4B000000)
        with self.assertRaisesRegex(ValueError, 'unexpected VIF command'):
            tire.unpack_microprogram(bytes(raw))

    def test_overlapping_mpg_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overlapping MPG'):
            tire.unpack_microprogram(self.synthetic_packet(overlap=True))

    def test_changed_light_alpha_rejected(self):
        self.change_word('light_upload', 0x2AE304, 0xAC83000C)
        with self.assertRaisesRegex(ValueError, 'light alpha upload'):
            tire.derive(self.parts)

    def test_changed_base_alpha_math_rejected(self):
        self.change_word('microprogram', 0x5FE5C4, 0x01F2BD28)
        with self.assertRaisesRegex(ValueError, 'base alpha arithmetic'):
            tire.derive(self.parts)

    def test_changed_reflection_alpha_rejected(self):
        self.change_word('microprogram', 0x5FFE64, 0x00201083)
        with self.assertRaisesRegex(ValueError, 'reflection RGBA arithmetic'):
            tire.derive(self.parts)

    def test_changed_reflection_constant_rejected(self):
        self.change_word('reflection_constants', 0x3BED50, 0x3C014300)
        with self.assertRaisesRegex(ValueError, 'reflection RGBA constants'):
            tire.derive(self.parts)

    def test_changed_cull_selector_rejected(self):
        self.parts['cull_table'] = bytes([0, 0, 192])
        with self.assertRaisesRegex(ValueError, 'cull selector table'):
            tire.derive(self.parts)

    def test_changed_program_pointer_rejected(self):
        self.change_word('registration', 0x3B59B8, 0x24A5E020)
        with self.assertRaisesRegex(ValueError, 'program registration'):
            tire.derive(self.parts)

    def test_other_native_instruction_change_rejected(self):
        raw = bytearray(self.parts['light_upload'])
        raw[2] ^= 1
        self.parts['light_upload'] = bytes(raw)
        with self.assertRaisesRegex(ValueError, 'source interval identity mismatch'):
            tire.derive(self.parts)

    def test_missing_interval_rejected(self):
        self.parts.pop('program_name')
        with self.assertRaisesRegex(ValueError, 'missing VU source interval'):
            tire.derive(self.parts)

    def test_invalid_executable_rejected(self):
        with self.assertRaisesRegex(ValueError, 'executable identity mismatch'):
            tire.from_executable(b'not the source ELF')

    def test_changed_generated_uv_rejected(self):
        self.change_word('microprogram', 0x5FE584, 0x01808E58)
        with self.assertRaisesRegex(ValueError, 'generated UV arithmetic'):
            tire.derive(self.parts)

    def test_changed_prmodecont_rejected(self):
        self.change_word('gs_common_packet', 0x61C3D0, 1)
        with self.assertRaisesRegex(ValueError, 'PRMODECONT'):
            tire.derive(self.parts)

    def test_changed_texa_rejected(self):
        self.change_word('gs_common_packet', 0x61C3F4, 0)
        with self.assertRaisesRegex(ValueError, 'TEXA'):
            tire.derive(self.parts)

    def ppf(self):
        return (Path(__file__).resolve().parents[1] /
                'games/midnight-club-3-remix/cars/shared/assets/06483/resources/vehicle/tire.ppf').read_bytes()

    def test_all_native_tire_pages_have_same_uv_alpha_contract(self):
        result = tire.from_tire_ppf(self.ppf())
        self.assertEqual(result['pages'], 98)
        self.assertEqual(result['texture_slots'], 294)
        self.assertEqual(result['native_palette_alpha_max'], 84)
        self.assertEqual(result['cached_uv_transform'], tire.CACHED_TRANSFORM)
        self.assertEqual(result['TEX0'], {'PSM': 19, 'TCC': 1, 'TFX': 0, 'CPSM': 0})

    def test_changed_native_ppf_page_count_rejected(self):
        raw = bytearray(self.ppf())
        struct.pack_into('<I', raw, 4, 97)
        with self.assertRaisesRegex(ValueError, 'tire page count'):
            tire.from_tire_ppf(bytes(raw))

    def test_changed_native_cached_transform_rejected(self):
        raw = bytearray(self.ppf())
        struct.pack_into('<f', raw, 0x42A00, .75)
        with self.assertRaisesRegex(ValueError, 'cached UV transform'):
            tire.from_tire_ppf(bytes(raw))

    def test_changed_native_tex0_tcc_rejected(self):
        raw = bytearray(self.ppf())
        value = struct.unpack_from('<Q', raw, 0x42870)[0]
        struct.pack_into('<Q', raw, 0x42870, value ^ (1 << 34))
        with self.assertRaisesRegex(ValueError, 'TEX0 alpha mode'):
            tire.from_tire_ppf(bytes(raw))

    def test_changed_native_cached_q_rejected(self):
        raw = bytearray(self.ppf())
        struct.pack_into('<f', raw, 0x42A28, 0)
        with self.assertRaisesRegex(ValueError, 'cached UV transform'):
            tire.from_tire_ppf(bytes(raw))

    def test_changed_native_fov_scale_rejected(self):
        self.change_word('tire_scale_update', 0x3B5FCC, 0x3C014210)
        with self.assertRaisesRegex(ValueError, 'FOV scale arithmetic'):
            tire.derive(self.parts)

    def test_changed_native_fov_field_rejected(self):
        self.change_word('fov_projection_prefix', 0x531248, 0xE61501A0)
        with self.assertRaisesRegex(ValueError, 'FOV projection prefix'):
            tire.derive(self.parts)

    def test_four_wheel_program_cull_proofs(self):
        proof = tire.wheel_culling_proof()
        self.assertEqual(len(proof['programs']), 4)
        self.assertEqual(proof['caller_selector'], 2)
        self.assertEqual(proof['rim_ppf']['material_states'], 750)

    def test_changed_builtin_cull_gate_rejected(self):
        proof = copy.deepcopy(tire.wheel_culling_proof())
        proof['programs'][0]['selected_instruction_proof'][1]['lower'] ^= 1
        with self.assertRaisesRegex(ValueError, 'native cull gate'):
            tire.wheel_culling_proof(proof)

    def test_changed_rim_adc_write_rejected(self):
        proof = copy.deepcopy(tire.wheel_culling_proof())
        proof['programs'][2]['selected_instruction_proof'][-1]['lower'] = 0x8000033C
        with self.assertRaisesRegex(ValueError, 'ADC write'):
            tire.wheel_culling_proof(proof)

    def test_changed_default_binding_pin_rejected(self):
        proof = copy.deepcopy(tire.wheel_culling_proof())
        proof['native_intervals']['builtin_binding']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'interval pin mismatch'):
            tire.wheel_culling_proof(proof)

    def rim_ppf(self):
        return (Path(__file__).resolve().parents[1] /
                'games/midnight-club-3-remix/cars/shared/assets/06479/resources/vehicle/rim.ppf').read_bytes()

    def test_all_selected_rim_pages_inherit_culling(self):
        report = tire.from_rim_ppf(self.rim_ppf())
        expected = tire.wheel_culling_proof()['rim_ppf']
        self.assertEqual(report, expected)
        self.assertEqual(len(report['selected_pages']), 91)

    def test_changed_rim_page_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, 'selected page coverage'):
            tire.from_rim_ppf(self.rim_ppf(), tire.RIM_PAGES[:-1])

    def test_rim_cull_override_rejected(self):
        from mc3_wheels import ppf_page, read_page_model
        data = bytearray(self.rim_ppf())
        model = read_page_model(bytes(data), ppf_page(bytes(data), tire.RIM_PAGES[0]))
        offset = model['materials'][0]['ppf_file_offset']
        state = struct.unpack_from('<I', data, offset + 8)[0] + model['model_file_offset'] - model['serialized_base']
        self.assertEqual(data[state], 1)
        data[state] = 0
        with self.assertRaisesRegex(ValueError, 'rim cull override'):
            tire.from_rim_ppf(bytes(data))

    def test_unproven_rim_microprogram_rejected(self):
        from mc3_wheels import ppf_page, read_page_model
        data = bytearray(self.rim_ppf())
        model = read_page_model(bytes(data), ppf_page(bytes(data), tire.RIM_PAGES[0]))
        offset = model['materials'][0]['ppf_file_offset']
        data[offset + 12] = 7
        with self.assertRaisesRegex(ValueError, 'unproven native rim microprogram'):
            tire.from_rim_ppf(bytes(data))

    def test_fixture_is_not_modified(self):
        before = copy.deepcopy(self.parts)
        tire.derive(self.parts)
        self.assertEqual(self.parts, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
