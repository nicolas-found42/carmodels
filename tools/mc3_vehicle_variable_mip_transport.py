"""Literal variable-Q original GS draw controls, with textures bound separately."""

import json

from mc3_vehicle_variable_mip import controls, packets


def transports():
    return [
        dict(
            name=case["name"], chunks_hex=[chunk.hex() for chunk in packets(case)[-3:]]
        )
        for case in controls()
    ]


if __name__ == "__main__":
    print(json.dumps(transports()))
