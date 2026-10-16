"""Transport selection cannot change the original authored control commands."""
import unittest

from mc3_vehicle_mip import controls as cases, packets
from mc3_vehicle_mip_transport import controls


class TransportTests(unittest.TestCase):
    def test_exact_original_draw_packets(self):
        rows = controls()
        self.assertEqual(len(rows), 19)
        for row, case in zip(rows, cases(), strict=True):
            self.assertEqual(row['name'], case['name'])
            self.assertEqual([bytes.fromhex(s) for s in row['chunks_hex']], packets(case)[-3:])


if __name__ == '__main__':
    unittest.main(verbosity=2)
