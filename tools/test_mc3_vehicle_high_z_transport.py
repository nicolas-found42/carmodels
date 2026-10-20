"""High-depth shared-consumer transport preserves literal native controls."""

import json
import unittest

from mc3_vehicle_high_z import FIXTURE, packets
from mc3_vehicle_depth32 import clear_packets
from mc3_vehicle_high_z_transport import controls


class HighDepthTransportTests(unittest.TestCase):
    def test_literal_original_draws(self):
        rows = json.loads(FIXTURE.read_text())["records"]
        for row, transport in zip(rows, controls(), strict=True):
            self.assertEqual(transport["name"], row["case"]["name"])
            self.assertEqual(
                [bytes.fromhex(h) for h in transport["chunks_hex"]],
                [clear_packets()[0], *packets(row["case"])[-3:]],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
