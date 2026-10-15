#!/usr/bin/env python3
"""Source catalogs keep game identity and reject changed or escaped models."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_model_catalog import model_catalog
from gt_metadata import load_database, model_metadata
from gt_model import build_glb

ROOT = Path(__file__).resolve().parents[1]


class ModelCatalogTests(unittest.TestCase):
    def test_verified_native_metadata_survives_catalog_and_rejects_detached_rows(self):
        native = ROOT / 'games/gran-turismo/cars'
        texture = (native / 'simulation/_afr7n/day/textures.tex').read_bytes()
        metadata = model_metadata(load_database(native / '_metadata'), '_afr7n',
                                  list(texture[16:16 + int.from_bytes(texture[14:16], 'little')]))
        payload, records = build_glb((native / 'simulation/_afr7n/day/model.car').read_bytes(),
                                     texture, 'simulation/_afr7n', metadata)
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            folder = public / 'gran-turismo'
            folder.mkdir()
            (folder / 'car.glb').write_bytes(payload)
            row = {'code': 'simulation/_afr7n', 'file': 'car.glb', 'bytes': len(payload),
                   'sha256': hashlib.sha256(payload).hexdigest(), 'records': records,
                   'display_name': metadata['identity']['name'], 'native_metadata': metadata}
            index = folder / 'index.json'
            index.write_text(json.dumps({'cars': [row]}))
            result = model_catalog(public)['cars'][0]
            self.assertEqual(result['native_metadata'], metadata)
            self.assertEqual(result['display_name'], 'RX-7 FC GT-X')
            row['display_name'] = 'Invented retail name'
            index.write_text(json.dumps({'cars': [row]}))
            with self.assertRaisesRegex(ValueError, 'display name differs'):
                model_catalog(public)
            row['display_name'] = metadata['identity']['name']
            row['code'] = 'simulation/_afr7r'
            index.write_text(json.dumps({'cars': [row]}))
            with self.assertRaisesRegex(ValueError, 'detached'):
                model_catalog(public)
            row['code'] = 'simulation/_afr7n'
            row['native_metadata']['specifications']['mass_kg'] = 1400
            index.write_text(json.dumps({'cars': [row]}))
            with self.assertRaisesRegex(ValueError, 'differs from model'):
                model_catalog(public)

    def test_aliases_are_namespaced_and_collisions_or_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            folder = public/'gran-turismo'
            folder.mkdir()
            data = b'canonical model'
            (folder/'car.glb').write_bytes(data)
            row = {'code':'simulation/test', 'file':'car.glb', 'bytes':len(data),
                   'sha256':hashlib.sha256(data).hexdigest(), 'records':[],
                   'aliases':['simulation/test/day', 'arcade/pair-0000']}
            index = folder/'index.json'
            index.write_text(json.dumps({'cars':[row]}))
            self.assertEqual(model_catalog(public)['cars'][0]['aliases'],
                             ['gran-turismo/simulation/test/day', 'gran-turismo/arcade/pair-0000'])
            for aliases in (['../escape'], ['simulation/test'], ['alias', 'alias'], 'bad'):
                row['aliases'] = aliases
                index.write_text(json.dumps({'cars':[row]}))
                with self.assertRaisesRegex(ValueError, 'alias'):
                    model_catalog(public)
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

    def test_native_packages_route_to_their_game_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            public=Path(directory)
            folder=public/'other-game'
            folder.mkdir()
            data=b'native bytes'
            (folder/'car.dat').write_bytes(data)
            entry={'code':'CAR','file':'car.dat','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                   'records':[],'asset_kind':'native-package','native_members':1}
            (folder/'index.json').write_text(json.dumps({'cars':[entry]}))
            with self.assertRaisesRegex(ValueError,'Unsupported native package game'):model_catalog(public)
            folder.rename(public/'gran-turismo-4')
            # GT4 publishes GLB rows; a native-package row there is not accepted.
            with self.assertRaisesRegex(ValueError,'Unsupported native package game'):model_catalog(public)
            (public/'gran-turismo-4/car.glb').write_bytes(data)
            entry.update(file='car.glb', native_package={'file': 'car.dat'})
            entry.pop('asset_kind'); entry.pop('native_members')
            (public/'gran-turismo-4/index.json').write_text(json.dumps({'cars':[entry]}))
            # A GT4 GLB row must also satisfy the GT4 row validator (preview and native package).
            with self.assertRaisesRegex(ValueError,'Invalid GT4 source package'):model_catalog(public)
            entry.pop('native_package')
            (public/'gran-turismo-4/index.json').write_text(json.dumps({'cars':[entry]}))
            with self.assertRaisesRegex(ValueError,'Invalid GT4 source package'):model_catalog(public)


if __name__=='__main__':
    unittest.main(verbosity=2)
