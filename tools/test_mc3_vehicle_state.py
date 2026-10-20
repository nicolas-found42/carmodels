import copy
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

import mc3_vehicle_state as state


class NativeStateTests(unittest.TestCase):
    def test_source_identity_and_instruction_intervals(self):
        with self.assertRaisesRegex(ValueError, "executable changed"):
            state.source_contract(b"changed")
        with (
            patch.object(
                state, "EXECUTABLE_SHA", hashlib.sha256(b"fixture").hexdigest()
            ),
            patch.object(state, "_read_elf", return_value=b"wrong interval"),
        ):
            with self.assertRaisesRegex(ValueError, "source interval changed"):
                state.source_contract(b"fixture")

    def test_jobs_bound_original_context_and_reject_wrong_shape(self):
        proof = json.loads(state.FIXTURE.read_text())
        self.assertEqual(len(proof["contexts"]), 32)
        for context in proof["contexts"]:
            job = state.reference_job(context)
            self.assertEqual(
                hashlib.sha256(job).hexdigest(), context["execution"]["job_sha256"]
            )
            self.assertEqual(
                context["execution"]["original_mc3_executable_sha256"],
                state.EXECUTABLE_SHA,
            )
            # Expected output fields have no role in native input construction.
            changed = copy.deepcopy(context)
            changed["vu"]["42"] = [0, 0, 0, 0]
            self.assertEqual(state.reference_job(changed), job)
            changed["words"][8] ^= 1
            self.assertNotEqual(state.reference_job(changed), job)
        changed = copy.deepcopy(proof["contexts"][0])
        changed["words"].pop()
        with self.assertRaisesRegex(ValueError, "state words"):
            state.reference_job(changed)
        changed = copy.deepcopy(proof["contexts"][0])
        changed["bpp"] = 16
        with self.assertRaisesRegex(ValueError, "state context"):
            state.reference_job(changed)

    def test_transport_bounds_and_exact_vif_gif_decode(self):
        proof = json.loads(state.FIXTURE.read_text())
        for context in proof["contexts"]:
            raw = bytes.fromhex(context["dma_hex"])
            ram = bytearray(32 * 1024 * 1024)
            ram[0x1006000 : 0x1006000 + len(raw)] = raw
            struct.pack_into("<I", ram, 0x1000000, 0x1006000 + len(raw))
            decoded = state.decode_reference(ram)
            self.assertEqual(decoded["gs"], context["gs"])
            self.assertEqual(
                decoded["vu"], {int(k): v for k, v in context["vu"].items()}
            )
            self.assertEqual(decoded["dma_sha256"], context["dma_sha256"])
        with self.assertRaisesRegex(ValueError, "RAM extent"):
            state.decode_reference(b"")
        struct.pack_into("<I", ram, 0x1000000, 0x100F001)
        with self.assertRaisesRegex(ValueError, "DMA cursor"):
            state.decode_reference(ram)
        struct.pack_into("<I", ram, 0x1000000, 0x1006000 + len(raw))
        ram[0x1006000] ^= 1
        with self.assertRaisesRegex(ValueError, "VIF packet"):
            state.decode_reference(ram)


if __name__ == "__main__":
    unittest.main(verbosity=2)
