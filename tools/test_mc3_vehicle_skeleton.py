"""Source palette identity, serialized joins and explicit refusal controls."""

import copy
import unittest

from mc3_vehicle_skeleton import (
    from_executable,
    native_context,
    output,
    source_contract,
)


class VehicleSkeletonTests(unittest.TestCase):
    def test_original_controls_cover_hierarchy_and_root_composition(self):
        proof = source_contract()
        self.assertEqual(len(proof["sources"]), 3)
        self.assertEqual(
            sorted(s["joint_count"] for s in proof["sources"].values()), [24, 111, 250]
        )
        self.assertEqual(len(proof["cases"]), 12)
        self.assertEqual(proof["controller_vtable"][4], 0x58E8E8)
        for name, source in proof["sources"].items():
            cases = [c for c in proof["cases"] if c["source"] == name]
            self.assertEqual([c["backend"] for c in cases], [0, 1, 0, 1])
            for a, b in zip(cases[::2], cases[1::2]):
                for key in ("local_frames", "world_palette", "parent_indices"):
                    self.assertEqual(a["expected"][key], b["expected"][key])
                self.assertNotEqual(a["job_sha256"], b["job_sha256"])
            self.assertEqual(
                cases[0]["expected"]["local_frames"],
                cases[2]["expected"]["local_frames"],
            )
            self.assertNotEqual(
                cases[0]["expected"]["world_palette"],
                cases[2]["expected"]["world_palette"],
            )
            for mesh in source["mesh_palette_joins"]:
                self.assertLess(mesh["bone"], source["joint_count"])
                self.assertTrue(mesh["packets"])
                self.assertTrue(all(len(p["sha256"]) == 64 for p in mesh["packets"]))

    def test_receipt_tampering_refused(self):
        proof = source_contract()
        for mutate in (
            lambda p: p["controller_vtable"].__setitem__(4, 0),
            lambda p: p["cases"][0]["root_words"].__setitem__(0, 0),
            lambda p: p["sources"]["vp_350z_04"]["mesh_palette_joins"][0].update(
                bone=0
            ),
            lambda p: p["cases"][0]["expected"].update(ram_sha256="0" * 64),
        ):
            bad = copy.deepcopy(proof)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, "receipt differs"):
                source_contract(bad)

    def test_invalid_source_and_context_refused_before_execution(self):
        with self.assertRaisesRegex(ValueError, "executable differs"):
            from_executable(b"wrong executable")
        frame = source_contract()["cases"][0]["root_words"]
        for words, backend in (
            (frame, 2),
            (frame[:-1], 0),
            ([-1] * 12, 0),
            ([0x7F800000] * 12, 0),
        ):
            with self.assertRaisesRegex(ValueError, "vehicle skeleton"):
                native_context("never-read-invalid-context.pck", words, backend)

    def test_output_extent_refused(self):
        with self.assertRaisesRegex(ValueError, "output extent"):
            output(b"wrong RAM", 24)
        for count in (0, 513, True):
            with self.assertRaisesRegex(ValueError, "output extent"):
                output(bytes(0x2000000), count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
