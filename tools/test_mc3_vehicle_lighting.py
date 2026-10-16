"""Source/frame/job controls for the original vehicle garage lighting binder."""
import copy
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import mc3_vehicle_lighting as light
from mc3_reference_runtime import BINARY_SHA, contract, validate_job


class VehicleLightingTests(unittest.TestCase):
    def test_receipt_and_original_settings_controls(self):
        proof = light.source_contract()
        for change in [lambda r: r['reference_light_words'].__setitem__(1, 0),
                       lambda r: r['default_second_point_words'].__setitem__(1, 0),
                       lambda r: r['setting_fields']['Light Color'].__setitem__('offset', 0x90)]:
            bad = copy.deepcopy(proof)
            change(bad)
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                light.source_contract(receipt=bad)
        settings = proof['source_settings_ascii'].encode('ascii')
        self.assertEqual(light.source_settings(settings), {'AmbientColor': 1040522668,
                         'LightIntensity': 1148827633, 'LightColor': 1059996503})
        with self.assertRaisesRegex(ValueError, 'garage settings changed'):
            light.source_settings(settings.replace(b'0.129996', b'0.229996'))
        with self.assertRaisesRegex(ValueError, 'executable changed'):
            light.source_contract(bytes(1024))

    def test_reference_job_preserves_explicit_native_frames(self):
        proof = light.source_contract()
        settings = proof['source_settings_ascii'].encode('ascii')
        job = light.lighting_job(settings, **proof['reference_context'])
        validate_job(job, 'ee')
        self.assertEqual(hashlib.sha256(job).hexdigest(), proof['reference_job_sha256'])
        moved = light.lighting_job(settings, car_position_words=[0x3f800000, 0, 0],
                                   selected_offset_words=[0x40000000, 0, 0])
        self.assertNotEqual(job, moved)
        for bad in [None, [0, 0], [0, 0, True], [0, 0, 0x7f800000]]:
            with self.assertRaisesRegex(ValueError, 'finite native frame'):
                light.lighting_job(settings, car_position_words=bad, selected_offset_words=[0, 0, 0])

    def test_execution_binding_extent_and_changed_word_controls(self):
        proof = light.source_contract()
        settings = proof['source_settings_ascii'].encode('ascii')
        for mode in ['correct', 'runtime', 'word', 'extent']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                executable = Path(temp)/'original'
                executable.write_bytes(b'synthetic source-contract boundary')

                def runner(job, output, **kwargs):
                    output.mkdir()
                    ram = bytearray(32*1024*1024)
                    struct.pack_into('<34I', ram, 0x1003000, *proof['reference_light_words'])
                    if mode == 'word':
                        ram[0x1003000] ^= 1
                    (output/'ee-ram.bin').write_bytes(ram[:-1] if mode == 'extent' else ram)
                    return {'status': 'executed', 'job_sha256': proof['reference_job_sha256'],
                            'original_mc3_executable_sha256': light.EXECUTABLE_SHA,
                            'runtime': {'binary_sha256': 'other' if mode == 'runtime' else BINARY_SHA},
                            'adapter_sha256': contract()['adapter_source_sha256']}

                original = light.source_contract
                with patch.object(light, 'source_contract', side_effect=lambda *a, **k: original()):
                    if mode == 'correct':
                        result = light.execute_reference(executable, settings, Path(temp)/'fresh', runner)
                        self.assertEqual(result['light_words'], proof['reference_light_words'])
                    else:
                        with self.assertRaisesRegex(ValueError, {'runtime': 'binding changed',
                                                    'word': 'output changed', 'extent': 'extent changed'}[mode]):
                            light.execute_reference(executable, settings, Path(temp)/'fresh', runner)


if __name__ == '__main__':
    unittest.main(verbosity=2)
