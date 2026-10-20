"""Source pin and executed-binder output refusal controls."""

import copy
import struct
import unittest

from mc3_vehicle_bindings import (
    decode_reference_output,
    from_executable,
    reference_jobs,
    source_contract,
    verify_reference_output,
)


class VehicleBindingReferenceTests(unittest.TestCase):
    def test_all_five_retained_original_oracle_outputs_and_mutations(self):
        for probe in source_contract()["executed_probes"]:
            ram = bytearray(0x1008000)
            ram[0x1002000:0x1002004] = bytes(probe["rgba"])
            for index, (address, values) in enumerate(probe["uniform_words"].items()):
                offset = 0x1006000 + index * 32
                struct.pack_into(
                    "<8I",
                    ram,
                    offset,
                    0x10000001,
                    0,
                    0x11000000,
                    0x6C010000 | int(address),
                    *values,
                )
            with self.subTest(name=probe["name"]):
                self.assertEqual(
                    verify_reference_output(bytes(ram), probe)["rgba"], probe["rgba"]
                )
                changed = bytearray(ram)
                changed[0x1002000] ^= 1
                with self.assertRaisesRegex(ValueError, "RGBA differs"):
                    verify_reference_output(bytes(changed), probe)
                changed = bytearray(ram)
                changed[0x1006010] ^= 1
                with self.assertRaisesRegex(ValueError, "uniforms differ"):
                    verify_reference_output(bytes(changed), probe)

    def test_recipe_and_source_identity_tampering_fail_closed(self):
        proof = copy.deepcopy(source_contract())
        proof["executed_probes"][0]["entry"] ^= 4
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            source_contract(proof)
        with self.assertRaisesRegex(ValueError, "executable identity"):
            from_executable(b"fake executable")
        with self.assertRaisesRegex(ValueError, "executable identity"):
            reference_jobs(b"fake executable", b"fake source")
        with self.assertRaisesRegex(ValueError, "extent changed"):
            decode_reference_output(b"fake RAM")


if __name__ == "__main__":
    unittest.main(verbosity=2)
