"""The pass-4 shading table copies the pass-source join's rows and rejects changed sources or outputs."""
import json
import tempfile
import unittest
from pathlib import Path

from build_pass4_assignments import OUTPUT, PREVIEW, PREVIEW_OUTPUT, RECEIPT, ROOT, build, derive


def fixture(root):
    """A temporary root holding the two committed sources the derivation reads."""
    receipt = root / 'research/evidence/vu-dispatch/pass-source-join.json'
    preview = root / 'research/evidence/vu-dispatch/pass4-retained-target.png'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(RECEIPT.read_bytes())
    preview.write_bytes(PREVIEW.read_bytes())
    return receipt, preview


class Pass4Assignments(unittest.TestCase):
    def test_committed_table_is_current_and_carries_the_join(self):
        sources = {path: path.read_bytes() for path in (RECEIPT, PREVIEW, OUTPUT, PREVIEW_OUTPUT)}
        table = build(ROOT, OUTPUT, PREVIEW_OUTPUT, check=True)
        self.assertEqual(table['schema'], 'fr2-game-shading-pass4/v1')
        self.assertEqual(table['label'], 'candidate')
        self.assertEqual(table['source']['pass4_draws'], 37)
        self.assertEqual(table['texture']['identity'], 'view-render-target-0')
        self.assertEqual([car['code'] for car in table['cars']], ['COBRA'])
        headers = table['cars'][0]['headers']
        self.assertEqual(len(headers), 37)
        self.assertEqual(len({header['offset'] for header in headers}), 37)
        self.assertTrue(all(header['flags'] & 0x10 for header in headers), 'a listed Header lacks the pass-4 eligibility bit')
        self.assertIn('candidate', json.dumps(table['claim_limits']))
        # a check run never rewrites its inputs
        self.assertEqual({path: path.read_bytes() for path in sources}, sources)

    def test_changed_sources_and_stale_outputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, preview = fixture(root)
            output = root / 'dealership/public/game-shading-pass4.json'
            copied = root / 'dealership/public/pass4-retained-target.png'
            build(root, output, copied)
            self.assertEqual(build(root, output, copied, check=True)['cars'][0]['code'], 'COBRA')
            table = json.loads(output.read_text())
            table['cars'][0]['headers'][0]['offset'] += 16
            output.write_text(json.dumps(table, indent=1) + '\n')
            with self.assertRaisesRegex(ValueError, 'stale'):
                build(root, output, copied, check=True)
            build(root, output, copied)
            copied.write_bytes(preview.read_bytes() + b'x')
            with self.assertRaisesRegex(ValueError, 'stale'):
                build(root, output, copied, check=True)
            build(root, output, copied)
            pass4 = lambda rows: [row for row in rows if row.get('pass_word') == 4]
            controls = [
                ('pass-4 draws', lambda rows, texture: rows.remove(pass4(rows)[0])),
                ('pass-4 draws', lambda rows, texture: pass4(rows)[0].__setitem__('pass_word', 5)),
                ('header offset', lambda rows, texture: pass4(rows)[0].__setitem__('header_offset', -1)),
                ('duplicate Header offset', lambda rows, texture: pass4(rows)[1].__setitem__('header_offset', pass4(rows)[0]['header_offset'])),
                ('row car', lambda rows, texture: pass4(rows)[0].__setitem__('car', 5)),
                ('identity', lambda rows, texture: texture.__setitem__('identity', 'car-texture-3')),
            ]
            for message, mutate in controls:
                original = json.loads(RECEIPT.read_text())
                mutate(original['rows'], original['pass4_texture'])
                receipt.write_text(json.dumps(original))
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    build(root, output, copied)
            original = json.loads(RECEIPT.read_text())
            original['schema'] = 'fr2-pass-source-join/v2'
            receipt.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, 'schema'):
                build(root, output, copied)
            receipt.write_bytes(RECEIPT.read_bytes())
            preview.write_bytes(PREVIEW.read_bytes()[:-1] + bytes([PREVIEW.read_bytes()[-1] ^ 1]))
            with self.assertRaisesRegex(ValueError, 'pin'):
                build(root, output, copied)
            # the derivation is a pure function of its two inputs
            table, image = derive(RECEIPT.read_bytes(), PREVIEW.read_bytes())
            self.assertEqual(image, PREVIEW.read_bytes())
            self.assertEqual(len(table['cars'][0]['headers']), 37)


if __name__ == '__main__':
    unittest.main()
