"""Real corpus and synthetic VIF controls for MC3 PS2 geometry."""
from pathlib import Path
import struct
import unittest

from mc3_pck import MAX_VERTICES, Pck, decode_batches, read_bones, read_mesh_object, read_resource_group, read_vehicle, strip_indices, vif_planes

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x6800000


def command(cmd, count, address, payload=b""):
    return struct.pack("<I", cmd << 24 | count << 16 | address) + payload + b"\0" * (-len(payload) % 4)


def packet(count=4):
    header = struct.pack("<4f4I", 1 / 8192, 0, 0, 1, count, 0, 0, count)
    positions = [(0, 0, 0), (8192, 0, 0), (0, 8192, 0), (8192, 8192, 0)][:count]
    data = command(0x6C, 2, 0x98, header)
    data += command(0x69, count, 0xEE, struct.pack("<" + "h" * count * 3, *(x for v in positions for x in v)))
    data += command(0x65, count, 0xC4, struct.pack("<" + "h" * count * 2, *([0, 4096] * count)))
    data += command(0x6E, count, 0x4118, bytes([128, 129, 130, 12] * count))
    data += command(0x6A, count, 0x9A, bytes([0, 0, 127] * count))
    return data + b"\0" * (-len(data) % 16)


def carrier(payload, kind=22):
    return struct.pack("<4I", BASE, kind, 1, len(payload)) + b"\0" * 112 + payload


def fixture():
    stream = packet()
    data = bytearray(96 + len(stream))
    struct.pack_into("<6I", data, 0, 0x7A0F98, 0, 1, BASE + 32, BASE + 64, 0)
    struct.pack_into("<H", data, 32, 0)
    struct.pack_into("<I", data, 64, BASE + 80)
    struct.pack_into("<IHH", data, 80, BASE + 96, len(stream) // 16, 4)
    data[96:] = stream
    return carrier(data)


class PacketTests(unittest.TestCase):
    def test_destination_skip_cycles_do_not_become_contiguous_geometry(self):
        stream = packet()
        # CL=2, WL=1 writes VU addresses start, start+2, start+4, ...
        # It must not produce the contiguous square accepted by the old reader.
        controls = {
            "header_and_attributes": command(1, 0, 0x0102) + stream,
            "attributes_only": stream[:36] + command(1, 0, 0x0102) + stream[36:],
        }
        for name, altered in controls.items():
            with self.subTest(name=name):
                planes = vif_planes(Pck(carrier(altered)), 128, len(altered))
                self.assertTrue(any(plane["cl"] > plane["wl"] for plane in planes))
                self.assertEqual(planes[-1]["count"], 4)
                with self.assertRaisesRegex(ValueError, "destination skip cycle"):
                    decode_batches(planes)
        # A state command without a following UNPACK does not affect geometry.
        trailing_state = stream + command(1, 0, 0x0102)
        batch = decode_batches(vif_planes(Pck(carrier(trailing_state)), 128, len(trailing_state)))[0]
        self.assertEqual(batch["positions"], [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)])

    def test_shared_group_recovers_exact_missing_body(self):
        code = "vp_belair_57"
        main = read_vehicle(next((ROOT / "midnight-club-3-remix/cars" / code).rglob(code + ".pck")))
        path = next((ROOT / "midnight-club-3-remix/cars/shared").rglob(code + "_g.pck"))
        group = read_resource_group(path)
        name = "vroot_body_chptp_stk_rkstrsd_bel57_chptp_stk_rkstrsd_bel57_LOD_hlod_group_shell_h.mesh"
        missing = next(part for part in main["lods"]["high"] if part["name"] == name)
        self.assertIsNone(missing["mesh"])
        resolved = group["parts"][name]
        self.assertEqual(resolved["bone"], missing["bone"])
        self.assertEqual(len(group["materials"]), len(main["materials"]))
        self.assertGreater(sum(len(batch["positions"]) for draw in resolved["mesh"]["draws"] for batch in draw["batches"]), 1000)
        self.assertNotIn(name.lower(), group["parts"])
        self.assertNotIn("shell_h.mesh", group["parts"])

    def test_scalar_batch_header_matches_native_wheel_profile(self):
        # PPF wheel packets upload scale/count through S32 instead of V4_32.
        stream = command(0x60, 2, 0x98, struct.pack("<fI", 1 / 8192, 4)) + packet()[36:]
        batch = decode_batches(vif_planes(Pck(carrier(stream)), 128, len(stream)))[0]
        self.assertEqual(batch["positions"], [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)])
        self.assertEqual(len(batch["header_words"]), 2)
        altered = bytearray(stream)
        struct.pack_into("<I", altered, 0, 0x60010098)
        with self.assertRaisesRegex(ValueError, "header layout"):
            planes = vif_planes(Pck(carrier(altered)), 128, len(altered))
            decode_batches(planes)

    def test_native_rest_tree_and_corruption_controls(self):
        path = next((ROOT / "midnight-club-3-remix/cars/vp_350z_04").rglob("vp_350z_04.pck"))
        vehicle = read_vehicle(path)
        skeleton = vehicle["skeleton"]
        bones = skeleton["bones"]
        self.assertEqual(len(bones), 250)
        self.assertEqual(bones[16]["name"], "trunkbone")
        self.assertEqual(bones[16]["parent"], 0)
        for actual, expected in zip(bones[16]["global_position"], (0, 1.240475, .767380)):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertEqual(bones[40]["name"], "hood")
        self.assertEqual(bones[40]["rotation_raw"], (0, 0, 0))
        self.assertEqual(bones[8]["global_position"], bones[7]["global_position"])
        self.assertEqual(bones[8]["local_position"], (0, 0, 0))
        source = path.read_bytes()
        start = skeleton["joint_array_offset"]
        controls = [
            (skeleton["offset"], "H", 0, "bone count"),
            (start + 68 + 56, "H", 0, "bone index"),
            (start + 68 + 28, "I", BASE + start - 128 + 1, "joint array"),
            (start + 68 + 20, "I", BASE + start - 128 + 68, "ancestry cycle"),
            (start + 16 * 68, "f", float("nan"), "nonfinite bone"),
            (start + 16 * 68, "f", 5, "rest translation"),
            (start + 24, "I", 0, "unreachable"),
        ]
        for offset, code, value, reason in controls:
            with self.subTest(reason=reason):
                altered = bytearray(source)
                struct.pack_into("<" + code, altered, offset, value)
                with self.assertRaisesRegex(ValueError, reason):
                    read_bones(Pck(bytes(altered)), skeleton["offset"])

    def test_exact_geometry_and_source_locations(self):
        pck = Pck(fixture())
        draw = read_mesh_object(pck, 128)["draws"][0]
        batch = draw["batches"][0]
        self.assertEqual(draw["packet_offset"], 224)
        self.assertEqual(draw["vertex_count"], 4)
        self.assertEqual(batch["positions"], [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)])
        self.assertEqual(batch["uvs"], [(0, 1)] * 4)
        self.assertEqual(batch["normals"], [(0, 0, 127 / 128)] * 4)
        self.assertEqual(batch["flags"], [12] * 4)
        self.assertEqual(batch["color_integers"], [(128, 129, 130, 12)] * 4)

    def test_strip_adc_and_degenerate_controls(self):
        batch = {"positions": [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], "adc": [1, 1, 0, 0]}
        self.assertEqual(strip_indices(batch), [0, 1, 2, 2, 1, 3])
        batch["adc"][2] = 1
        self.assertEqual(strip_indices(batch), [2, 1, 3])
        batch["positions"][3] = batch["positions"][1]
        self.assertEqual(strip_indices(batch), [])
        batch["adc"].pop()
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            strip_indices(batch)

    def test_differential_unpack_and_cycle_fill(self):
        # STROW seeds a signed absolute vector, STMOD2 accumulates each delta.
        stream = command(0x30, 0, 0, struct.pack("<4i", 100, -100, 20, 0))
        stream += command(5, 0, 2)
        stream += command(0x6A, 3, 0xEE, struct.pack("<9b", 0, 0, 0, 1, -2, 3, -1, 2, -3))
        data = Pck(carrier(stream))
        self.assertEqual(vif_planes(data, 128, len(stream))[0]["values"], [(100, -100, 20), (101, -102, 23), (100, -100, 20)])
        # The native wheel packets fill many vertices from one masked value.
        stream = command(0x20, 0, 0, struct.pack("<I", 0x55555555))
        stream += command(0x30, 0, 0, struct.pack("<4I", 127, 127, 127, 0))
        stream += command(1, 0, 0x0401)
        stream += command(0x7E, 4, 0x4118, b"\0" * 4)
        planes = vif_planes(Pck(carrier(stream)), 128, len(stream))
        self.assertEqual(planes[0]["values"], [(127, 127, 127, 0)] * 4)

    def test_controls_reject_for_the_intended_reason(self):
        source = fixture()
        controls = [
            (12, "I", len(source), "payload length"),
            (128, "I", 0xDEADBEEF, "mesh profile"),
            (144, "I", BASE - 1, "outside payload"),
            (212, "H", 65535, "outside payload"),
            (214, "H", 5, "vertex count"),
            (228, "f", float("nan"), "position scale"),
            (224, "I", 0x4A020098, "VIF command"),
            (260, "I", 0x69FF00EE, "unpack exceeds"),
        ]
        for offset, code, value, reason in controls:
            altered = bytearray(source)
            struct.pack_into("<" + code, altered, offset, value)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                read_mesh_object(Pck(bytes(altered)), 128)
        planes = vif_planes(Pck(source), 224, len(source) - 224)
        planes.append(dict(planes[-1]))
        with self.assertRaisesRegex(ValueError, "overlapping"):
            decode_batches(planes)
        del planes[-2:]
        with self.assertRaisesRegex(ValueError, "missing VIF normals"):
            decode_batches(planes)

    def test_vertex_budget_and_finite_strip_positions(self):
        pck = Pck(fixture())
        pck.decoded_vertices = MAX_VERTICES
        with self.assertRaisesRegex(ValueError, "vertex budget"):
            read_mesh_object(pck, 128)
        with self.assertRaisesRegex(ValueError, "finite XYZ"):
            strip_indices({"positions": [(0, float("nan"), 0)], "adc": [1]})

    def test_all_94_exact_main_sources_and_native_profiles(self):
        folders = sorted((ROOT / "midnight-club-3-remix/cars").glob("vp_*"))
        self.assertEqual(len(folders), 94)
        profiles = set()
        for folder in folders:
            paths = list(folder.glob("assets/**/" + folder.name + ".pck"))
            self.assertEqual(len(paths), 1, folder.name)
            model = read_vehicle(paths[0])
            profiles.add(model["model_vtable"])
            self.assertEqual(set(model["lods"]), {"high", "middle", "low"})
            self.assertTrue(any(part["mesh"] for part in model["lods"]["high"]), folder.name)
            for part in model["lods"]["high"]:
                if part["mesh"]:
                    for draw in part["mesh"]["draws"]:
                        self.assertLess(draw["material"], len(model["materials"]))
                        self.assertEqual(draw["vertex_count"], sum(len(b["positions"]) for b in draw["batches"]))
        self.assertEqual(profiles, {0x7A9420, 0x7AA728, 0x7A9620})


if __name__ == "__main__":
    unittest.main()
