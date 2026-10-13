"""GT4 GLB assembly: structure, handedness, wheel layout and display-baker compatibility."""
from pathlib import Path
import unittest

from bake_models import bake_car, read_glb
from gt4_glb import LIMITS, PROFILE, build_car, wheel_layout
from gt4_specdb import car_specs

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / 'games/gran-turismo-4/cars'


class GlbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = car_specs(CARS / 'provenance/specdb/GT4_EU2560')
        cls.data = (CARS / 'acra0001/car/menu/acra0001').read_bytes()
        cls.glb, cls.record = build_car(cls.data, 'acra0001', cls.specs['acra0001'], {'file': 'test'})
        cls.doc, cls.binary = read_glb(cls.glb)

    def test_scene_nodes_and_provenance(self):
        names = [node['name'] for node in self.doc['nodes']]
        self.assertEqual(names[0], 'body')
        self.assertEqual(sorted(names[1:]), sorted(f'{kind}_{axle}_{side}' for kind in ('wheel', 'tire')
                                                   for axle in ('front', 'rear') for side in ('left', 'right')))
        extras = self.doc['extras']
        self.assertEqual((extras['source_profile'], extras['car'], extras['claim_limits']), (PROFILE, 'acra0001', LIMITS))
        body = self.record['parts']['body']
        self.assertGreater(body['omitted_overlay_shapes'], 0)
        self.assertEqual(body['triangles'], 3857)
        self.assertEqual(len(self.doc['images']), self.record['textures'])

    def test_wheels_face_minus_z_and_mirror_into_gltf_frame(self):
        layout = {w['name']: w for w in wheel_layout(self.specs['acra0001'])}
        # Native frame, used unchanged: the car faces -z and its right side is +x. 215/50R17 is 0.6468 m across.
        self.assertAlmostEqual(layout['front_right']['centre'][0], (1.769 - 0.215) / 2)
        self.assertAlmostEqual(layout['front_right']['centre'][2], -2.715 / 2)
        self.assertAlmostEqual(layout['rear_left']['centre'][2], 2.715 / 2)
        self.assertAlmostEqual(layout['front_left']['outer_radius'], (17 * 25.4 + 215) / 2000)
        nodes = {node['name']: node for node in self.doc['nodes']}
        # glTF: right wheels at +x, front axle at -z; left wheels mirror the outer face outward.
        self.assertGreater(nodes['wheel_front_right']['translation'][0], 0)
        self.assertLess(nodes['wheel_front_right']['translation'][2], 0)
        self.assertEqual(nodes['wheel_front_right']['scale'], [1, 1, 1])
        self.assertEqual(nodes['wheel_front_left']['scale'], [-1, 1, 1])
        # Ground 140 mm (SUSPENSION ride height) below the model origin.
        self.assertAlmostEqual(nodes['tire_rear_left']['translation'][1], (17 * 25.4 + 215) / 2000 - 0.140, places=4)

    def test_staggered_tires_follow_their_axles(self):
        spec = {**self.specs['acra0001'], 'rear_tire': {'aspect': 40, 'rim_inches': 19.0, 'width_mm': 315}}
        layout = {w['name']: w for w in wheel_layout(spec)}
        self.assertAlmostEqual(layout['rear_left']['outer_radius'], (19 * 25.4 + 2 * 0.4 * 315) / 2000)
        self.assertGreater(layout['rear_left']['centre'][2], 0)
        self.assertLess(layout['front_left']['outer_radius'], layout['rear_left']['outer_radius'])

    def test_body_bounds_and_baker(self):
        body = self.doc['meshes'][self.doc['nodes'][0]['mesh']]
        lows = [self.doc['accessors'][p['attributes']['POSITION']]['min'] for p in body['primitives']]
        self.assertGreater(min(low[1] for low in lows), -0.05)  # Brake parts follow wheel matrices, not the origin.
        baked = bake_car('GT4_ACRA0001', self.glb, source_mode=False)
        self.assertGreater(baked['triangleCount'], 5000)

    def test_implausible_ride_height_fails(self):
        with self.assertRaisesRegex(ValueError, 'implausible spec-database ride height'):
            wheel_layout({**self.specs['acra0001'], 'ride_height_mm': [900, 140]})

    def test_implausible_tire_data_fails(self):
        spec = {**self.specs['acra0001'], 'front_tire': {'aspect': 50, 'rim_inches': 170.0, 'width_mm': 215}}
        with self.assertRaisesRegex(ValueError, 'implausible spec-database tire size'):
            build_car(self.data, 'acra0001', spec, {})

if __name__ == '__main__':
    unittest.main()
