"""Game palette collection preserves game/provenance boundaries and detects stale carriers."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from build_game_paints import build, collect, glb_document


def glb(path, colors=None, game='game'):
    doc = {'asset': {'version': '2.0'}, 'extras': {'gamePaint': {
        'schema': 1, 'channels': [{'id': 'body', 'materials': [0]}],
        'colors': colors if colors is not None else [
            {'id': 'red', 'name': 'Native red', 'rgb': [.5, 0, 0], 'source': 'native/paint:0'}]}}}
    text = json.dumps(doc).encode()
    text += b' ' * (-len(text) % 4)
    data = struct.pack('<5I', 0x46546C67, 2, 20 + len(text), len(text), 0x4E4F534A) + text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return game, path.name, path


class PaintLibrary(unittest.TestCase):
    def test_output_cannot_replace_source_or_editable_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb(root / 'dealership/public/game/car.glb')
            glb(root / 'dealership/dealership/models/CAR.glb')
            (root / 'dealership/public/models.json').write_text(json.dumps({'cars': [
                {'game': 'game', 'file': 'game/car.glb'}]}))
            (root / 'dealership/dealership/catalog.json').write_text(json.dumps([{'game': 'game', 'code': 'CAR'}]))
            paths = [root / name for name in ('dealership/public/game/car.glb',
                     'dealership/public/models.json', 'dealership/public/game/index.json',
                     'dealership/dealership/catalog.json', 'dealership/dealership/models/CAR.glb',
                     'games/original-source.dat')]
            for path in paths:
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'protected source input')
            before = {path: path.read_bytes() for path in paths}
            for path in paths:
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'source or editable'):
                    build(root, path)
            self.assertEqual({path: path.read_bytes() for path in paths}, before)
            # The intended public artifact remains writable and checkable.
            output = root / 'dealership/public/game-paints.json'
            self.assertEqual(build(root, output), build(root, output, True))

    def test_union_is_source_and_game_specific(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = glb(root / 'one.glb')
            second = glb(root / 'two.glb')
            other = glb(root / 'foreign.glb', game='other')
            data = collect([second, other, first])
            self.assertEqual(len(data['colors']), 2)
            self.assertEqual([c['game'] for c in data['colors']], ['game', 'other'])
            self.assertEqual(len(data['assets']), 3)
            self.assertEqual(data, collect([other, first, second]))
            self.assertTrue(all(len(a['sha256']) == 64 for a in data['assets']))

    def test_conflicting_native_identity_and_invalid_vectors_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = glb(root / 'one.glb')
            color = glb_document(first[2])['extras']['gamePaint']['colors'][0]
            changed = copy.deepcopy(color)
            changed['rgb'] = [0, 1, 0]
            second = glb(root / 'two.glb', [changed])
            with self.assertRaisesRegex(ValueError, 'conflicting'):
                collect([first, second])
            for value in ([2, 0, 0], [True, 0, 0], [float('nan'), 0, 0], [0, 0]):
                changed['rgb'] = value
                bad = glb(root / 'bad.glb', [changed])
                with self.assertRaisesRegex(ValueError, 'invalid native paint colour'):
                    collect([bad])

    def test_container_bounds_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'truncated.glb'
            glb(path)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'header'):
                glb_document(path)

    def test_freshness_detects_current_model_and_palette_changes_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb(root / 'dealership/public/game/car.glb')
            glb(root / 'dealership/dealership/models/CAR.glb')
            (root / 'dealership/public/models.json').write_text(json.dumps({'cars': [
                {'game': 'game', 'file': 'game/car.glb'}]}))
            (root / 'dealership/dealership/catalog.json').write_text(json.dumps([{'game': 'game', 'code': 'CAR'}]))
            output = root / 'palette.json'
            build(root, output)
            previous = output.read_bytes()
            self.assertEqual(len(build(root, output, True)['colors']), 1)
            path = root / 'dealership/dealership/models/CAR.glb'
            doc = glb_document(path)
            colors = doc['extras']['gamePaint']['colors']
            colors[0]['source'] = 'native/another-paint:0'
            glb(path, colors)
            with self.assertRaisesRegex(ValueError, 'stale'):
                build(root, output, True)
            self.assertEqual(output.read_bytes(), previous)


if __name__ == '__main__':
    unittest.main(verbosity=2)
