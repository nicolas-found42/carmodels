"""Native tire template and serializer proof controls; no ISO required."""
import copy
import json
import struct
import unittest

from mc3_tire_alpha import (TireAlphaError, active_ps2_lines, decode_gs_alpha, decode_state_commands,
                            native_renderer_passes, tire_alpha_policy, tire_alpha_translation)
import verify_mc3_tire_alpha as verifier


class TireAlphaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shader = (verifier.AREA / 'tire.shadert').read_bytes()

    def test_committed_source_receipt_reproduces(self):
        actual = json.dumps(verifier.receipt(self.shader), indent=1) + '\n'
        self.assertEqual(actual, (verifier.AREA / 'native-alpha.json').read_text())

    def test_active_native_policy_ignores_old_pass(self):
        policy = tire_alpha_policy(self.shader)
        self.assertEqual(policy['alpha_test'], 'always')
        self.assertEqual(policy['base_pass_rgb_equation'], '(0 - 0) * As + Cs = Cs')
        self.assertEqual(policy['active_pass_declarations'], 1)
        self.assertEqual(policy['base_color'], [127, 127, 127, 255])
        # A false comparison in a semicolon comment must not affect the active policy.
        appended = self.shader.replace(b'; Old version for reference.', b'; alphafunc never')
        self.assertEqual(tire_alpha_policy(appended), policy)

    def test_commented_fake_always_cannot_supply_active_alpha(self):
        mutated = self.shader.replace(b'alphafunc always', b';alphafunc always', 1)
        with self.assertRaisesRegex(TireAlphaError, 'missing or duplicate alphafunc'):
            tire_alpha_policy(mutated)

    def test_inline_comment_and_real_line_endings(self):
        text = self.shader.replace(b'\\r\\n', b'\r\n')
        text = text.replace(b'colorwrite rgba', b'colorwrite rgba ; alphafunc never', 1)
        self.assertEqual(tire_alpha_policy(text), tire_alpha_policy(self.shader))

    def test_else_is_not_active_ps2(self):
        data = b'inputs\n0 TEXTURE color\n1 TEXTURE lightMap\nendinputs\n#if PS2\nalpha active\n#else\nalpha fake\n#endif\n'
        self.assertEqual(active_ps2_lines(data), ['alpha active'])

    def test_malformed_preprocessor_is_rejected(self):
        for old, new, reason in [
            (b'#if PS2', b'#if PC', 'unsupported shader conditional'),
            (b'#if PS2', b'#if PS2\\r\\n#if PS2', 'duplicate or nested PS2'),
            (b'#else', b'#else\\r\\n#else', 'unexpected or duplicate else'),
            (b'#endif', b';#endif', 'missing or unfinished PS2'),
        ]:
            with self.subTest(reason=reason), self.assertRaisesRegex(TireAlphaError, reason):
                active_ps2_lines(self.shader.replace(old, new, 1))

    def test_native_compact_and_wide_stream_values(self):
        rows = decode_state_commands(verifier.STATE)
        self.assertEqual([(r['command'], r['width'], r['value']) for r in rows],
                         [(1, 1, 1), (3, 4, 65546), (9, 1, 15), (4, 1, 1), (8, 4, 0x807F7F7F)])
        self.assertEqual(decode_state_commands(b'\xff'), [])
        self.assertEqual(decode_state_commands(bytes.fromhex('c000010000ff'))[0]['value'], 256)

    def test_mutations_fail_for_intended_reasons(self):
        expected = {
            'alpha compare changed': 'changed alphafunc', 'blend changed': 'changed ps2blend',
            'alpha write changed': 'changed colorwrite', 'missing alpha': 'missing or duplicate alphafunc',
            'duplicate alpha': 'missing or duplicate alphafunc', 'wrong branch': 'unsupported shader conditional',
            'unknown alpha directive': 'unknown, reordered or changed active tire directive',
            'unknown state flags': 'unproven state width flags', 'unknown state command': 'unknown state command',
            'truncated state argument': 'truncated state argument', 'duplicate state command': 'duplicate state command',
            'noncanonical wide state': 'noncanonical wide state argument',
            'native renderer proof tamper': 'native encoding proof identity mismatch',
            'native encoding proof tamper': 'native encoding proof identity mismatch',
            'missing state terminator': 'missing state terminator', 'trailing state bytes': 'trailing state bytes',
        }
        for label, mutate in verifier.controls():
            inputs = {'shader': self.shader, 'state': verifier.STATE, 'proofs': verifier.load_proofs()}
            mutate(inputs)
            with self.subTest(label=label), self.assertRaisesRegex(TireAlphaError, expected[label]):
                verifier.derive(inputs)

    def test_native_renderer_uses_base_and_destination_alpha_reflection(self):
        passes = native_renderer_passes(verifier.load_proofs())
        self.assertEqual(passes['register'], 0x42)
        self.assertEqual(passes['base']['register_value'], 0x0A)
        self.assertEqual(passes['reflection']['register_value'], 0x58)
        self.assertEqual(passes['base']['rgb_equation_normalized_alpha'], '(0 - 0) * As + Cs')
        self.assertEqual(passes['reflection']['rgb_equation_normalized_alpha'], '(Cs - 0) * Ad + Cd')
        self.assertEqual(passes['reflection']['integer_alpha_divisor'], 128)
        translation = tire_alpha_translation()
        self.assertEqual(translation['policy'], 'native-ps2-tire-reflection-v2')
        self.assertEqual(translation['reflection_pass_rgb_equation'], '(Cs - 0) * Ad + Cd')
        self.assertEqual(translation['source']['shader_sha256'], verifier.SHADER_SHA)
        self.assertTrue(any('not emulated' in item for item in translation['claim_limits']))
        self.assertEqual(translation['base_rgbaq_alpha'], 128)
        self.assertEqual(translation['reflection_rgbaq'], [127, 127, 127, 0])
        self.assertEqual(translation['native_normal_attribute'], '_MC3_NATIVE_NORMAL')

    def test_reserved_gs_alpha_fields_rejected(self):
        for value, reason in [(3, 'reserved GS ALPHA selector'),
                              (0x30, 'reserved GS ALPHA selector'),
                              (1 << 8, 'unknown GS ALPHA bits'),
                              (True, 'unknown GS ALPHA bits')]:
            with self.subTest(value=value), self.assertRaisesRegex(TireAlphaError, reason):
                decode_gs_alpha(value)
        self.assertEqual(decode_gs_alpha(0x8000000020)['FIX'], 128)

    def test_proof_fixture_tamper_rejected(self):
        proofs = verifier.load_proofs()
        verifier.validate_proofs(proofs)
        mutated = copy.deepcopy(proofs)
        mutated['state-writer'] = mutated['state-writer'].replace(b'sltiu', b'XXXXX', 1)
        with self.assertRaisesRegex(TireAlphaError, 'native encoding proof identity mismatch'):
            verifier.validate_proofs(mutated)
        del proofs['state-finalizer']
        with self.assertRaisesRegex(TireAlphaError, 'missing or extra encoding proof'):
            verifier.validate_proofs(proofs)

    def test_elf_segment_mapping_not_raw_file_offset(self):
        elf = bytearray(0x200)
        elf[:7] = b'\x7fELF\x01\x01\x01'
        struct.pack_into('<I', elf, 28, 52)
        struct.pack_into('<HH', elf, 42, 32, 1)
        struct.pack_into('<IIIII', elf, 52, 1, 0x100, 0x2B0500, 0x2B0500, 0x80)
        elf[0x104:0x108] = b'code'
        self.assertEqual(verifier.elf_slice(elf, 0x2B0504, 0x2B0508), b'code')
        with self.assertRaisesRegex(TireAlphaError, 'missing or ambiguous native code interval'):
            verifier.elf_slice(elf, 0x2B04FC, 0x2B0504)
        struct.pack_into('<I', elf, 52 + 16, 0x200)
        with self.assertRaisesRegex(TireAlphaError, 'truncated ELF load segment'):
            verifier.elf_slice(elf, 0x2B0504, 0x2B0508)


if __name__ == '__main__':
    unittest.main(verbosity=2)
