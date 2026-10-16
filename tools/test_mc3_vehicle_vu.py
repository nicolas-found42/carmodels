"""Boundary and tamper controls for native vehicle arithmetic oracle jobs."""
import copy
import hashlib
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import mc3_vehicle_vu as vehicle
from mc3_reference_runtime import validate_job


class VehicleVUTests(unittest.TestCase):
    def test_source_receipt_tamper_controls(self):
        proof = vehicle.source_contract()
        for mutate in [lambda p: p['kernels']['carpaint_3pass_dc'].__setitem__('first_pc', 166),
                       lambda p: p['numerical_probes'][0]['register_words']['24'].__setitem__(0, 45),
                       lambda p: p['synthetic_probe_context']['memory_rows']['2'].__setitem__(0, 65)]:
            changed = copy.deepcopy(proof)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                vehicle.source_contract(receipt=changed)
        with self.assertRaisesRegex(ValueError, 'executable changed'):
            vehicle.source_contract(bytes(512))

    def test_measured_controls_distinguish_normal_and_material_behavior(self):
        probes = {p['name']: p for p in vehicle.source_contract()['numerical_probes']}
        self.assertEqual(probes['light_texgen_dc']['register_words']['22'], [44, 28, 28, 128])
        self.assertEqual(probes['raw-normal-double']['register_words']['22'], [76, 44, 44, 128])
        self.assertEqual(probes['raw-normal-adc-x']['register_words']['22'], [45, 28, 28, 128])
        self.assertEqual(probes['negative-coefficients']['register_words']['24'], [12, 12, 12, 128])
        self.assertEqual(probes['light-saturation']['register_words']['25'], [128]*4)
        self.assertEqual(probes['material-scale']['register_words']['22'], [22, 7, 3, 80])
        self.assertEqual(probes['fresnel-clip-w']['register_words']['14'], [128, 128, 128, 80])

    def test_isolated_kernel_preserves_original_pairs_and_raw_inputs(self):
        # Deliberately synthetic code: no private native microprogram fixture.
        pairs = {i: (vehicle.NOP[0], vehicle.NOP[1]) for i in range(8)}
        pairs[2] = (0x3C000000, 0x800002FF)  # LOI1/128.
        proof = {'kernels': {'synthetic': {'address': 0, 'bytes': 16,
                 'first_pc': 2, 'last_pc': 4, 'rgba_register': 1, 'kernel_sha256': 'synthetic'}},
                 'claim_limits': ['synthetic carrier test only']}
        vf = {i: [0]*4 for i in range(1, 32)}
        vf[3] = [0x80000000, 0xFFFFFFFF, 0x3F800000, 0]
        with patch.object(vehicle, 'source_contract', return_value=proof), \
                patch.object(vehicle, '_read_elf', return_value=bytes(16)), \
                patch.object(vehicle, 'unpack_microprogram', return_value=pairs):
            job, binding = vehicle.kernel_job(b'synthetic', 'synthetic', bytes(16384), vf)
            validate_job(job, 'vu')
            self.assertEqual(struct.unpack_from('<II', job, 8+2*8), pairs[2])
            self.assertEqual(struct.unpack_from('<II', job, 8+4*8), pairs[4])
            self.assertEqual(struct.unpack_from('<II', job, 8+5*8),
                             (vehicle.NOP[0], vehicle.NOP[1] | 0x40000000))
            self.assertEqual(binding['job_sha256'], hashlib.sha256(job).hexdigest())
            self.assertIn(struct.pack('<I4I', 3, *vf[3]), job)
            with self.assertRaisesRegex(ValueError, 'registers must be explicit'):
                vehicle.kernel_job(b'', 'synthetic', bytes(16384), {})
            with self.assertRaisesRegex(ValueError, 'invalid vehicle VU memory'):
                vehicle.kernel_job(b'', 'synthetic', bytes(16), vf)
            with self.assertRaisesRegex(ValueError, 'unsupported vehicle'):
                vehicle.kernel_job(b'', 'unknown', bytes(16384), vf)

    def test_register_output_extent_and_index_guards(self):
        raw = bytearray(1680)
        struct.pack_into('<4I', raw, 24*16, 44, 28, 28, 128)
        self.assertEqual(vehicle.read_register_words(bytes(raw), 24), [44, 28, 28, 128])
        for data, reg in [(bytes(1679), 24), (bytes(raw), -1), (bytes(raw), 32)]:
            with self.assertRaisesRegex(ValueError, 'register output'):
                vehicle.read_register_words(data, reg)

    def test_executed_probe_rejects_wrong_binding_or_numerical_word(self):
        probe = {'name': 'synthetic', 'job_sha256': 'job', 'runtime_binary_sha256': 'binary',
                 'adapter_sha256': 'adapter', 'register_words': {'1': [12, 13, 14, 128]}}
        proof = {'numerical_probes': [probe]}

        def runner(path, output):
            output.mkdir()
            raw = bytearray(1680)
            struct.pack_into('<4I', raw, 16, *probe['register_words']['1'])
            (output/'final-vuregs.bin').write_bytes(raw)
            return {'status': 'executed', 'job_sha256': 'job',
                    'runtime': {'binary_sha256': 'binary'}, 'adapter_sha256': 'adapter'}

        for mode in ['correct', 'binding', 'output']:
            with tempfile.TemporaryDirectory() as temp, \
                    patch.object(vehicle, 'source_contract', return_value=proof), \
                    patch.object(vehicle, 'probe_job', return_value=(b'synthetic', probe)):
                def altered(path, output):
                    receipt = runner(path, output)
                    if mode == 'binding':
                        receipt['adapter_sha256'] = 'other'
                    if mode == 'output':
                        raw = bytearray((output/'final-vuregs.bin').read_bytes())
                        raw[16] ^= 1
                        (output/'final-vuregs.bin').write_bytes(raw)
                    return receipt
                target = Path(temp)/'fresh'
                if mode == 'correct':
                    self.assertEqual(len(vehicle.execute_probes(b'', target, altered)), 1)
                    with self.assertRaisesRegex(ValueError, 'fresh'):
                        vehicle.execute_probes(b'', target, altered)
                else:
                    with self.assertRaisesRegex(ValueError, 'binding changed' if mode == 'binding'
                                                else 'numerical output changed'):
                        vehicle.execute_probes(b'', target, altered)


if __name__ == '__main__':
    unittest.main(verbosity=2)
