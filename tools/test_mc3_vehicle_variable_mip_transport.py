"""Composed sampler controls preserve literal native register and geometry bytes."""
import unittest

from mc3_vehicle_variable_mip import controls, packets
from mc3_vehicle_variable_mip_transport import transports


class VariableMipTransportTests(unittest.TestCase):
    def test_literal_draw_packets(self):
        for case, exported in zip(controls(), transports(), strict=True):
            self.assertEqual(exported['name'], case['name'])
            self.assertEqual([bytes.fromhex(raw) for raw in exported['chunks_hex']], packets(case)[-3:])


if __name__ == '__main__':
    unittest.main(verbosity=2)
