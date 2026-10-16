"""False-pass guards for deterministic independent native vehicle probes."""
import copy
import json
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import mc3_vehicle_math_reference as reference


def transport(program, outputs):
    raw, calls = bytearray(), []
    register = dict(zip(reference.PROGRAMS, [24, 25, 22, 14]))[program]
    for index, output in enumerate(outputs):
        data = bytearray(struct.pack('<QQ', 31 | 1 << 15 | 1 << 60, 0xF)+bytes(31*16))
        def store(reg, values):
            struct.pack_into('<'+'I'*len(values), data, 16+(reg-1)*16, *values)
        store(register, output['rgba'])
        if program == 'carpaint_3pass_dc':
            store(22, [0, 0]+output['st_words'])
            store(21, output['second_stq_words'])
        elif program != 'carbon_fiber_dc':
            store(20 if program == 'light_texgen_dc' else 31, output['stq_words'])
        # A deliberately split transport exercises per-call chunk reassembly.
        raw += struct.pack('<I', 16)+data[:16]+struct.pack('<I', 496)+data[16:]
        calls.append({'index': index, 'pc': 0x700, 'top': 0, 'itop': 0,
                      'start_chunk': index*2, 'end_chunk': index*2+2})
    return bytes(raw), calls


class VehicleReferenceTests(unittest.TestCase):
    def test_contexts_are_deterministic_and_cover_projective_controls(self):
        proof = reference.reference_contract()
        self.assertEqual(reference.contexts(), proof['contexts'])
        self.assertEqual(reference.digest(reference.contexts()), proof['contexts_sha256'])
        self.assertEqual(len(reference.contexts()), 32)
        self.assertNotEqual(proof['contexts'][0]['mvp'][3][:3], [0]*3)
        self.assertNotEqual(proof['contexts'][31]['uvMatrix'][0][2], 0)
        for name in reference.PROGRAMS:
            self.assertEqual(len(proof['programs'][name]['outputs']), 32)

    def test_fixture_context_output_and_source_binding_tamper_controls(self):
        proof = reference.reference_contract()
        for mutate in [lambda p: p['contexts'][0]['normal'].__setitem__(0, 0),
                       lambda p: p['programs']['light_texgen_dc']['outputs'][0]['rgba'].__setitem__(0, 255),
                       lambda p: p['programs']['carpaint_3pass_dc']['binding'].__setitem__('source_last_pc', 220)]:
            altered = copy.deepcopy(proof)
            mutate(altered)
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                reference.reference_contract(altered)

    def test_raw_inputs_preserve_native_lanes_and_do_not_load_expected_words(self):
        context = reference.contexts()[0]
        memory, vf = reference.context_memory(context)
        self.assertEqual(struct.unpack_from('<4i', memory, 32), (*context['normal'], 0))
        self.assertEqual(list(struct.unpack_from('<4I', memory, 86*16)), reference.words(context['position']+[0]))
        self.assertEqual(vf[1], reference.words(context['mvp'][0]))
        self.assertEqual(set(vf), set(range(1, 32)))
        with self.assertRaisesRegex(ValueError, 'contexts changed'):
            reference.reference_job(b'', 'light_texgen_dc', [context])
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            reference.reference_job(b'', 'other')

    def test_observer_reassembles_original_transport_and_rejects_call_changes(self):
        proof = reference.reference_contract()
        for name in reference.PROGRAMS:
            expected = proof['programs'][name]['outputs']
            raw, calls = transport(name, expected)
            self.assertEqual(reference.observer_outputs(name, raw, calls), expected)
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                reference.observer_outputs(name, raw, calls[:-1])
            changed = copy.deepcopy(calls)
            changed[1]['start_chunk'] = 0
            with self.assertRaisesRegex(ValueError, 'call binding'):
                reference.observer_outputs(name, raw, changed)
            with self.assertRaisesRegex(ValueError, 'transport'):
                reference.observer_outputs(name, raw[:8]+bytes(8)+raw[16:], calls)

    def test_execution_checks_actual_output_and_runtime_bindings(self):
        proof = reference.reference_contract()
        for mode in ['correct', 'output', 'runtime']:
            with tempfile.TemporaryDirectory() as temp:
                def job(_source, program):
                    return b'synthetic transport test', proof['programs'][program]['binding']
                def runner(path, output):
                    name = path.stem
                    output.mkdir()
                    outputs = copy.deepcopy(proof['programs'][name]['outputs'])
                    if mode == 'output':
                        outputs[0]['rgba'][0] ^= 1
                    raw, calls = transport(name, outputs)
                    (output/'gif-chunks.bin').write_bytes(raw)
                    (output/'calls.json').write_text(json.dumps(calls))
                    return {'status': 'executed', 'job_sha256': proof['programs'][name]['binding']['job_sha256'],
                            'runtime': {'binary_sha256': 'wrong' if mode == 'runtime' else proof['reference_binary_sha256']},
                            'adapter_sha256': proof['adapter_sha256']}
                with patch.object(reference, 'reference_job', side_effect=job):
                    target = Path(temp)/'fresh'
                    if mode == 'correct':
                        self.assertEqual(len(reference.execute_reference(b'', target, runner)), 4)
                        with self.assertRaisesRegex(ValueError, 'fresh'):
                            reference.execute_reference(b'', target, runner)
                    else:
                        with self.assertRaisesRegex(ValueError, 'output changed' if mode == 'output'
                                                    else 'execution binding'):
                            reference.execute_reference(b'', target, runner)


if __name__ == '__main__':
    unittest.main(verbosity=2)
