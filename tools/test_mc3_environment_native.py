"""Native scene receipt mutation controls and selected scalar arithmetic."""

import copy
import json
import unittest

from mc3_environment_native import (
    EVIDENCE,
    contract,
    f32,
    from_executable,
    from_sources,
    sky_vertex_rgba,
)


class NativeSceneTests(unittest.TestCase):
    def test_fixed_camera_join_and_native_shader_colors(self):
        value = contract()
        self.assertEqual(value["camera"]["right"], [1, 0, 0])
        self.assertEqual(value["camera"]["up"], [0, 0, -1])
        self.assertEqual(value["camera"]["row0_world_axis"], "-Z")
        self.assertEqual(value["camera"]["garage_fov_degrees"], 100)
        self.assertEqual(value["floor"]["pass1_rgba"], [75, 69, 65, 128])
        self.assertEqual(value["fx"]["glow_projection_call_mask"], 128)
        self.assertEqual(value["fx"]["environment_queue_required_bit"], 64)
        self.assertEqual(value["heading"]["angle_units"], "radians")
        self.assertEqual(value["heading"]["rotation_z"], "z*cos(angle)-x*sin(angle)")

    def test_original_normalization_truncates_sky_alpha_to127(self):
        self.assertEqual(sky_vertex_rgba(), [55, 55, 55, 127])
        self.assertEqual(sky_vertex_rgba((255, 255, 255, 255)), [127] * 4)
        self.assertNotEqual(f32(379.563843), 379.563843)

    def test_every_technical_receipt_group_is_pinned(self):
        original = json.loads(EVIDENCE.read_text())
        for key in (
            "camera_contract",
            "main_view_axis_contract",
            "floor_contract",
            "world_palette127",
            "sky_color",
            "fx_contract",
            "vu_programs",
            "selected_words",
            "intervals",
            "heading_contract",
        ):
            changed = copy.deepcopy(original)
            changed[key] = {} if isinstance(changed[key], dict) else []
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(ValueError, "receipt changed"),
            ):
                contract(changed)

    def test_unidentified_source_and_executable_are_refused(self):
        with self.assertRaisesRegex(ValueError, "executable identity"):
            from_executable(b"not the original executable")
        with self.assertRaisesRegex(ValueError, "source identity"):
            from_sources(b"city", b"props", b"tune")


if __name__ == "__main__":
    unittest.main(verbosity=2)
