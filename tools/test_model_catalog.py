#!/usr/bin/env python3
"""Source catalogs keep game identity and reject changed or escaped models."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_model_catalog import model_catalog


class ModelCatalogTests(unittest.TestCase):
    def test_two_games_and_corruption_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            public=Path(directory)
            for game in ['first-game','second-game']:
                folder=public/game
                folder.mkdir()
                data=(game+' model').encode()
                (folder/'car.glb').write_bytes(data)
                entry={'code':'SHARED','file':'car.glb','bytes':len(data),
                       'sha256':hashlib.sha256(data).hexdigest(),'records':[]}
                (folder/'index.json').write_text(json.dumps({'cars':[entry]}))
            catalog=model_catalog(public)
            self.assertEqual([c['id'] for c in catalog['cars']],['first-game/SHARED','second-game/SHARED'])
            self.assertEqual(catalog['cars'][1]['file'],'second-game/car.glb')
            self.assertEqual(model_catalog(public),catalog)
            index=public/'second-game/index.json'
            entry=json.loads(index.read_text())['cars'][0]
            index.write_text(json.dumps({'cars':[entry,entry]}))
            with self.assertRaisesRegex(ValueError,'Duplicate'):model_catalog(public)
            entry['file']='../first-game/car.glb'
            index.write_text(json.dumps({'cars':[entry]}))
            with self.assertRaisesRegex(ValueError,'outside'):model_catalog(public)
            entry['file']='car.glb'
            index.write_text(json.dumps({'cars':[entry]}))
            (public/'second-game/car.glb').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash/size'):model_catalog(public)


if __name__=='__main__':
    unittest.main()
