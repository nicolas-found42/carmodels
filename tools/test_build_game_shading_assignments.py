"""The game-shading table copies the pass-source join's aligned rows and rejects changed sources or outputs."""
import json
import tempfile
import unittest
from pathlib import Path

from build_game_shading_assignments import OUTPUT, PREVIEW, PREVIEW_OUTPUT, RECEIPT, ROOT, build, derive


def fixture(root):
    """A temporary root holding the two committed sources the derivation reads."""
    receipt = root / 'research/evidence/vu-dispatch/pass-source-join.json'
    preview = root / 'research/evidence/vu-dispatch/pass4-retained-target.png'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(RECEIPT.read_bytes())
    preview.write_bytes(PREVIEW.read_bytes())
    return receipt, preview


class GameShadingAssignments(unittest.TestCase):
    def test_committed_table_is_current_and_carries_the_join(self):
        sources = {path: path.read_bytes() for path in (RECEIPT, PREVIEW, OUTPUT, PREVIEW_OUTPUT)}
        table = build(ROOT, OUTPUT, PREVIEW_OUTPUT, check=True)
        self.assertEqual(table['schema'], 'fr2-game-shading/v2')
        self.assertEqual(table['label'], 'candidate')
        self.assertEqual(table['source']['draws'], {'4': 37, '5': 63})
        self.assertEqual(table['pass4_texture']['identity'], 'view-render-target-0')
        self.assertEqual([car['code'] for car in table['cars']], ['COBRA'])
        headers = table['cars'][0]['headers']
        self.assertEqual(len(headers), 63)
        self.assertEqual(len({header['offset'] for header in headers}), 63)
        # A pass-5 draw joins the 37 pass-4 Headers and 26 more of its own.
        self.assertEqual(len([header for header in headers if 4 in header['passes']]), 37)
        self.assertEqual(len([header for header in headers if 5 in header['passes']]), 63)
        self.assertTrue(all(header['passes'] == sorted(set(header['passes'])) for header in headers))
        self.assertTrue(all(header['passes'] for header in headers), 'a listed Header carries no pass')
        self.assertTrue(all(header['flags'] & 0x10 for header in headers if 4 in header['passes']),
                        'a pass-4 Header lacks the pass-4 eligibility bit')
        self.assertTrue(all(header['flags'] & 0x08 for header in headers if 5 in header['passes']),
                        'a pass-5 Header lacks the pass-5 eligibility bit')
        self.assertIn('candidate', json.dumps(table['claim_limits']))
        # a check run never rewrites its inputs
        self.assertEqual({path: path.read_bytes() for path in sources}, sources)

    def test_changed_sources_and_stale_outputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, preview = fixture(root)
            output = root / 'dealership/public/game-shading.json'
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
            rows_for = lambda rows, pass_word: [row for row in rows if row.get('pass_word') == pass_word]
            def swap_a_pass_5_row(rows, texture):
                """Remove one pass-5 row and repeat another: the count guard alone cannot see this."""
                rows.remove(rows_for(rows, 5)[-1])
                rows.append(dict(rows_for(rows, 5)[0]))
            controls = [
                ('pass-4 draws', lambda rows, texture: rows.remove(rows_for(rows, 4)[0])),
                ('pass-5 draws', lambda rows, texture: rows.remove(rows_for(rows, 5)[-1])),
                ('pass-4 draws', lambda rows, texture: rows_for(rows, 4)[0].__setitem__('pass_word', 5)),
                ('unexpected pass word', lambda rows, texture: rows.append(dict(rows_for(rows, 5)[0], pass_word=6))),
                ('duplicate pass-5 draw', swap_a_pass_5_row),
                ('header offset', lambda rows, texture: rows_for(rows, 4)[0].__setitem__('header_offset', -1)),
                ('header index', lambda rows, texture: rows_for(rows, 5)[-1].__setitem__('header_index', -1)),
                # The same Header joins in both passes; a disagreement there is a derivation error.
                ('disagrees about its index or flags', lambda rows, texture: rows_for(rows, 5)[0].__setitem__('header_flags', 0)),
                ('row car', lambda rows, texture: rows_for(rows, 4)[0].__setitem__('car', 5)),
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
            self.assertEqual(len(table['cars'][0]['headers']), 63)


if __name__ == '__main__':
    unittest.main()
