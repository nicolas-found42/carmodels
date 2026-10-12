"""GT4 GLB assembly: structure, handedness, wheel layout and display-baker compatibility."""
from pathlib import Path
import struct
import unittest

from bake_models import bake_car, read_glb
from gt4_glb import LIMITS, PROFILE, build_car, wheel_layout
from gt4_specdb import car_specs

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / 'gran-turismo-4/cars'


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

    def test_wheels_mirror_into_gltf_frame(self):
        layout = {w['name']: w for w in wheel_layout(self.specs['acra0001'], {'tire_diameter_front': 0.646, 'tire_diameter_rear': 0.6991})}
        self.assertAlmostEqual(layout['front_right']['centre'][0], (1.769 - 0.215) / 2)
        self.assertAlmostEqual(layout['front_right']['centre'][2], 2.715 / 2)
        nodes = {node['name']: node for node in self.doc['nodes']}
        # Native right (+x) wheels land at glTF -x; meshes built for the right wheel mirror there.
        self.assertLess(nodes['wheel_front_right']['translation'][0], 0)
        self.assertEqual(nodes['wheel_front_right']['scale'], [-1, 1, 1])
        self.assertEqual(nodes['wheel_front_left']['scale'], [1, 1, 1])
        self.assertAlmostEqual(nodes['tire_rear_left']['translation'][1], 0.6991 / 2, places=4)

    def test_body_bounds_and_baker(self):
        body = self.doc['meshes'][self.doc['nodes'][0]['mesh']]
        lows = [self.doc['accessors'][p['attributes']['POSITION']]['min'] for p in body['primitives']]
        self.assertGreater(min(low[1] for low in lows), -0.05)  # Brake parts follow wheel matrices, not the origin.
        baked = bake_car('GT4_ACRA0001', self.glb, source_mode=False)
        self.assertGreater(baked['triangleCount'], 5000)

    def test_implausible_tire_data_fails(self):
        corrupt = bytearray(self.data)
        struct.pack_into('<f', corrupt, 0x40 + 0x58, 9.0)
        with self.assertRaisesRegex(ValueError, 'implausible CAR4 tire diameters'):
            build_car(bytes(corrupt), 'acra0001', self.specs['acra0001'], {})


if __name__ == '__main__':
    unittest.main()
