"""Literal high-depth native GIF controls without their zero-clear sprites."""
import json

from mc3_vehicle_high_z import FIXTURE, packets
from mc3_vehicle_depth32 import clear_packets


def controls():
    proof = json.loads(FIXTURE.read_text())
    # Keep the original global state preamble and draw's exact state/geometry.
    return [{'name': row['case']['name'],
             'chunks_hex': [chunk.hex() for chunk in
                            [clear_packets()[0], *packets(row['case'])[-3:]]]}
            for row in proof['records']]


if __name__ == '__main__':
    print(json.dumps(controls()))
