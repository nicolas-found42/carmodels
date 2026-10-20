"""Literal original-control draw transports, omitting separately bound uploads."""

import json

from mc3_vehicle_mip import FIXTURE, packets


def controls():
    proof = json.loads(FIXTURE.read_text())
    return [
        {
            "name": row["case"]["name"],
            "chunks_hex": [chunk.hex() for chunk in packets(row["case"])[-3:]],
        }
        for row in proof["records"]
    ]


if __name__ == "__main__":
    print(json.dumps(controls()))
