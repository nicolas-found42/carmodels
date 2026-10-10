"""Reproduce every MC3 preview from pinned native members, not catalog assertions."""
import copy
import json
from pathlib import Path
import unittest

from bake_models import ROOT, bake_car, read_glb
from export_mc3_models import DEFAULT
from mc3_model import preview_vehicle, sha, native_executable
from mc3_pck import read_vehicle


class PreviewCorpusTests(unittest.TestCase):
    def test_complete_native_conversion_and_rest_frames(self):
        extraction = ROOT/'midnight-club-3-remix/cars'
        index = json.loads((extraction/'index.json').read_text())
        output = json.loads((DEFAULT/'index.json').read_text())
        rows = {r['code']: r for r in output['cars']}
        self.assertEqual(len(rows), 94)
        self.assertEqual(set(rows), {v['id'] for v in index['vehicles']})
        total, wheel_count, bikes = 0, 0, 0
        executable = native_executable()
        for vehicle in index['vehicles']:
            manifest = json.loads((extraction/vehicle['manifest']).read_text())
            data, evidence = preview_vehicle(extraction, manifest, index, executable)
            evidence = json.loads(json.dumps(evidence))
            row = rows[vehicle['id']]
            self.assertEqual(data, (DEFAULT/row['file']).read_bytes(), vehicle['id'])
            self.assertEqual(sha(data), row['sha256'])
            self.assertEqual(len(data), row['bytes'])
            for key, value in evidence.items():
                self.assertEqual(value, row[key], (vehicle['id'], key))
            self.assertTrue(all(not Path(s['file']).is_absolute() for s in evidence['native_resources']))
            self.assertEqual(evidence['omitted_stock_parts'], [], vehicle['id'])
            self.assertEqual(evidence['omitted_pose_parts'], [], vehicle['id'])
            slots = evidence['wheels']['slots']
            self.assertEqual(len(slots), 2 if evidence['wheels']['bike'] else 4)
            wheel_count += len(slots);bikes += int(evidence['wheels']['bike'])
            doc, _ = read_glb(data)
            formerly_omitted = {
                'vp_corvette_68': ['vroot_hood_mhd_stk_vet68_stock_hood.mesh'],
                'vp_d_corvette_63': ['vroot_hd_mhd_stk_vet63_mhd_stk_vet63_geo.mesh'],
                'vp_d_yukon_05': ['vroot_Suspension_Axle_Rear_axle_R.mesh'],
                'vp_murcielago_04': ['vroot_spoilers_popup_spoilers0_flap_0_LOD_sidevent_lh.mesh',
                                    'vroot_spoilers_popup_spoilers1_flap_1_LOD_sidevent_rh.mesh'],
            }
            for name in formerly_omitted.get(vehicle['id'], []):
                self.assertIn(name, {node['name'] for node in doc['nodes']})
            for slot in slots:
                nodes = [n for n in doc['nodes'] if n['extras'].get('nativeBone') == slot['bone']
                         and 'nativeWheelComponent' in n['extras']]
                self.assertEqual({n['extras']['nativeWheelComponent'] for n in nodes}, {'rim', 'tire'})
                for node in nodes:
                    self.assertEqual(node['translation'], slot['translation'])
                    self.assertEqual(node['scale'], slot['sizing'][node['extras']['nativeWheelComponent']+'_scale'])
            baked = bake_car('MC3_'+vehicle['id'].upper(), data, source_mode=False)
            self.assertEqual(baked['triangleCount'], row['triangle_count'])
            self.assertGreater(baked['triangleCount'], 0)
            total += baked['triangleCount']
            if vehicle['id'] == 'vp_350z_04':
                main = next(m for m in manifest['members'] if Path(m['file']).name == vehicle['id']+'.pck')
                bones = read_vehicle(extraction/main['file'])['skeleton']['bones']
                by_bone = {node['extras']['nativeBone']: node for node in doc['nodes']}
                # The stock hood mesh binds to child 41 of the hood joint 40.
                self.assertEqual(bones[41]['parent'], 40)
                for bone in (16, 41):
                    self.assertEqual(by_bone[bone]['translation'], list(bones[bone]['global_position']))
                # The body and the trunk/hood use different local origins.
                self.assertNotEqual(by_bone[16]['translation'], [0, 0, 0])
                self.assertNotEqual(by_bone[41]['translation'], [0, 0, 0])
        self.assertEqual((wheel_count, bikes), (346, 15))
        print(f'PASS canonical MC3 conversions: 94 source-derived GLBs, {total} triangles, 346 native wheel slots (79 cars/15 bikes); exact bytes, rest frames, sizing and resource pins')

    def test_source_hash_and_duplicate_identity_controls(self):
        extraction = ROOT/'midnight-club-3-remix/cars'
        vehicle = next(v for v in json.loads((extraction/'index.json').read_text())['vehicles'] if v['id'] == 'vp_350z_04')
        manifest = json.loads((extraction/vehicle['manifest']).read_text())
        changed = copy.deepcopy(manifest)
        next(m for m in changed['members'] if m['file'].endswith('.pck'))['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash/size'):
            preview_vehicle(extraction, changed)
        changed = copy.deepcopy(manifest)
        main = next(m for m in changed['members'] if Path(m['file']).name == vehicle['id']+'.pck')
        changed['members'].append(copy.deepcopy(main))
        with self.assertRaisesRegex(ValueError, 'main native model.*ambiguous'):
            preview_vehicle(extraction, changed)
        index = json.loads((extraction/'index.json').read_text())
        changed = copy.deepcopy(index)
        for row in changed['files']:
            if Path(row['file']).name == 'rim.ppf':
                row['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'wheel source differs'):
            preview_vehicle(extraction, manifest, changed)


if __name__ == '__main__':
    unittest.main()
