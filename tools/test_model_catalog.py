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
            gran_turismo=public/'gran-turismo'
            gran_turismo.mkdir()
            payload=b'GT candidate model'
            (gran_turismo/'car.glb').write_bytes(payload)
            gt={'code':'simulation/_0logn/night','file':'car.glb','bytes':len(payload),
                'sha256':hashlib.sha256(payload).hexdigest(),'records':[],
                'display_name':'_0logn · night','source_profile':'gran-turismo-native-candidate',
                'source_variant':'night','claim_limits':['Retail display name unverified.']}
            (gran_turismo/'index.json').write_text(json.dumps({'cars':[gt]}))
            combined=model_catalog(public)
            imported=next(c for c in combined['cars'] if c['game']=='gran-turismo')
            self.assertEqual(imported['id'],'gran-turismo/simulation/_0logn/night')
            for key in ['display_name','source_profile','source_variant','claim_limits']:
                self.assertEqual(imported[key],gt[key])
            gt['claim_limits']='Malformed unsupported claims'
            (gran_turismo/'index.json').write_text(json.dumps({'cars':[gt]}))
            with self.assertRaisesRegex(ValueError,'claim limits'):model_catalog(public)
            gt['claim_limits']=['Retail display name unverified.']
            gt['source_variant']={'name':'night'}
            (gran_turismo/'index.json').write_text(json.dumps({'cars':[gt]}))
            with self.assertRaisesRegex(ValueError,'metadata'):model_catalog(public)
            gt['source_variant']='night'
            (gran_turismo/'index.json').write_text(json.dumps({'cars':[gt]}))
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
