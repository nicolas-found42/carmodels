#!/usr/bin/env python3
"""Reproduce the native tire-template receipt, optionally rederiving it from MC3 ISO."""

import argparse
import json
import struct
import sys

from mc3_archive import CookedDisc, DaveArchive, file_digest
from mc3_tire_alpha import (
    AREA,
    ROOT,
    SHADER_SHA,
    ISO_SHA,
    STORED_SHA,
    EXECUTABLE_SHA,
    PROOFS,
    TireAlphaError,
    decode_state_commands,
    load_proofs,
    need,
    native_renderer_passes,
    tire_alpha_policy,
    validate_proofs,
)
import verifier_common as common

STATE = bytes.fromhex("0101c30a000100090f0401c87f7f7f80ff")


def derive(inputs):
    shader, state = inputs["shader"], inputs["state"]
    policy = tire_alpha_policy(shader)
    commands = decode_state_commands(state)
    proof = validate_proofs(inputs["proofs"])
    need(state == STATE, "changed retained tire state")
    need(common.sha256(shader) == SHADER_SHA, "native shader identity mismatch")
    return {
        "schema": 1,
        "source": {
            "disc_sha256": ISO_SHA,
            "disc_bytes": 8539963392,
            "archive": "ASSETS.DAT;1",
            "member": "shaderlib/tire.shadert",
            "ordinal": 6745,
            "iso_stored_offset": 4238550016,
            "stored_bytes": 523,
            "stored_sha256": STORED_SHA,
            "unpacked_bytes": len(shader),
            "unpacked_sha256": common.sha256(shader),
        },
        "template_policy": policy,
        "retained_state": {
            "bytes_hex": state.hex(),
            "commands": commands,
            "writer_encoding": "byte command/value below 256, otherwise command|0xC0 and LE u32; FF terminator",
            "command_semantics_proven_by_this_check": False,
        },
        "native_static_proof": proof,
        "native_renderer_passes": native_renderer_passes(inputs["proofs"]),
        "claim_limits": [
            "Static source directives establish the active PS2 template, not observed execution.",
            "The base blend algebra is overwrite even though its C operand names source alpha.",
            "The configured native second-pass ALPHA equation uses destination alpha; PRIM.ABE and the exact texture/VU-to-framebuffer alpha path remain unrecovered.",
            "VU RGBAQ, TEX0 TCC/TFX, TEXA and reflection lighting are not fully decoded or emulated.",
            "The state writer/finalizer encoding is static executable evidence; command-to-GS semantics are separate.",
            "This receipt does not establish GLB transparency, lighting or full game-render equivalence.",
        ],
    }


def controls():
    def shader(old, new):
        return lambda x: x.update(shader=x["shader"].replace(old, new, 1))

    return [
        (
            "alpha compare changed",
            shader(b"alphafunc always", b"alphafunc greater 128"),
        ),
        ("blend changed", shader(b"ps2blend 0 0 As Cs 0", b"ps2blend Cs Cd As Cd 0")),
        ("alpha write changed", shader(b"colorwrite rgba", b"colorwrite rgb")),
        ("missing alpha", shader(b"alphafunc always", b";alphafunc always")),
        (
            "duplicate alpha",
            shader(b"alphafunc always", b"alphafunc always\\r\\nalphafunc always"),
        ),
        ("wrong branch", shader(b"#if PS2", b"#if XBOX")),
        (
            "unknown alpha directive",
            shader(b"colorwrite rgba", b"alphaenable true\\r\\ncolorwrite rgba"),
        ),
        ("unknown state flags", lambda x: x.update(state=bytes.fromhex("4101ff"))),
        ("unknown state command", lambda x: x.update(state=bytes.fromhex("0e00ff"))),
        (
            "truncated state argument",
            lambda x: x.update(state=bytes.fromhex("c30a0001")),
        ),
        (
            "noncanonical wide state",
            lambda x: x.update(state=bytes.fromhex("c301000000ff")),
        ),
        (
            "duplicate state command",
            lambda x: x.update(state=bytes.fromhex("01010101ff")),
        ),
        ("missing state terminator", lambda x: x.update(state=STATE[:-1])),
        ("trailing state bytes", lambda x: x.update(state=STATE + b"\0")),
        (
            "native renderer proof tamper",
            lambda x: x["proofs"].update(
                {
                    "renderer-preparation": x["proofs"]["renderer-preparation"].replace(
                        b"0x58", b"0x59", 1
                    )
                }
            ),
        ),
        (
            "native encoding proof tamper",
            lambda x: x["proofs"].update(
                {
                    "state-writer": x["proofs"]["state-writer"].replace(
                        b"sltiu", b"XXXXX", 1
                    )
                }
            ),
        ),
    ]


def receipt(shader):
    inputs = {"shader": shader, "state": STATE, "proofs": load_proofs()}
    result = derive(inputs)
    result["negative_controls"] = common.run_controls(
        inputs, controls(), derive, TireAlphaError
    )
    return result


def elf_slice(data, start, end):
    need(data[:7] == b"\x7fELF\x01\x01\x01" and len(data) >= 52, "unsupported MC3 ELF")
    phoff = struct.unpack_from("<I", data, 28)[0]
    phsize, phnum = struct.unpack_from("<HH", data, 42)
    need(
        phsize >= 32 and phnum <= 128 and phoff + phsize * phnum <= len(data),
        "invalid ELF segments",
    )
    found = []
    for i in range(phnum):
        kind, offset, address, _, size = struct.unpack_from(
            "<IIIII", data, phoff + i * phsize
        )
        if kind == 1 and address <= start < end <= address + size:
            need(offset + size <= len(data), "truncated ELF load segment")
            found.append(data[offset + start - address : offset + end - address])
    need(len(found) == 1, "missing or ambiguous native code interval")
    return found[0]


def shader_from_disc(path):
    need(file_digest(path) == ISO_SHA, "MC3 disc identity mismatch")
    disc = CookedDisc(path)
    try:
        need(disc.size == 8539963392, "MC3 disc size mismatch")
        entries = [e for e in disc.entries if e["path"] == "ASSETS.DAT;1"]
        need(len(entries) == 1, "missing ASSETS archive")
        executable_rows = [e for e in disc.entries if e["path"] == "SLUS_213.55;1"]
        need(len(executable_rows) == 1, "missing native executable")
        executable = disc.read_at(
            executable_rows[0]["lba"] * 2048, executable_rows[0]["size"]
        )
        need(
            common.sha256(executable) == EXECUTABLE_SHA,
            "native executable identity mismatch",
        )
        import mc3_tire_vu
        import mc3_specular_native
        import mc3_environment_gs
        import mc3_garage
        import mc3_environment_sky
        import mc3_environment_native
        import mc3_environment_raster

        need(
            mc3_environment_raster.source_contract(executable)
            == mc3_environment_raster.source_contract(),
            "native environment raster source contract differs from executable",
        )
        need(
            mc3_environment_native.from_executable(executable)
            == mc3_environment_native.contract(),
            "native environment scene contract differs from executable",
        )
        need(
            mc3_environment_gs.from_executable(executable)
            == mc3_environment_gs.contract(),
            "native environment GS contract differs from executable",
        )
        mc3_garage.shared_texture_from_executable(executable)
        need(
            mc3_specular_native.from_executable(executable)
            == mc3_specular_native.contract(),
            "native specular generation contract differs from executable",
        )
        need(
            mc3_tire_vu.from_executable(executable) == mc3_tire_vu.contract(),
            "native VU reflection contract differs from executable",
        )
        for name, (start, end, _, pin) in PROOFS.items():
            need(
                common.sha256(elf_slice(executable, start, end)) == pin,
                "native code interval mismatch: " + name,
            )
        archive = DaveArchive(disc.region(entries[0]), entries[0]["size"])
        original_environment = {}
        for ordinal, name in [
            (5737, "resources/city/sd_midnight_clear.pck"),
            (6306, "resources/prop/sd_midnight_clear_garage_props.pck"),
            (10409, "tune/garage/garage.garageshared"),
        ]:
            matches = [
                r
                for r in archive.records
                if r["ordinal"] == ordinal and r["name"] == name
            ]
            need(len(matches) == 1, "missing original garage environment input")
            original_environment[ordinal] = archive.payload(matches[0])
        mc3_environment_sky.verify_fragment_source(original_environment[5737])
        mc3_garage.verify_fragment_source(original_environment[6306])
        native_scene = mc3_environment_native.from_sources(
            original_environment[5737],
            original_environment[6306],
            original_environment[10409],
        )
        import mc3_environment

        pack = mc3_environment.from_archive(archive)
        need(
            pack["camera"]["eye"]
            == [
                native_scene["car_position_native"][0],
                native_scene["car_position_native"][1] + 1,
                native_scene["car_position_native"][2],
            ],
            "native source camera pose differs from environment pack",
        )
        need(
            pack["car_heading"] == native_scene["car_angle_native"],
            "native source car angle differs from environment pack",
        )
        need(
            mc3_environment.OUTPUT.read_bytes() == mc3_environment.encode(pack),
            "native environment pack differs from original disc",
        )
        expected_garage = json.loads((AREA / "garage-environment.json").read_text())
        need(
            json.loads(
                json.dumps(mc3_garage.garage_receipt(original_environment[6306]))
            )
            == expected_garage,
            "original garage environment input receipt differs",
        )
        tire_rows = [
            r
            for r in archive.records
            if r["ordinal"] == 6483 and r["name"] == "resources/vehicle/tire.ppf"
        ]
        need(len(tire_rows) == 1, "missing native tire PPF")
        native_pages = mc3_tire_vu.from_tire_ppf(archive.payload(tire_rows[0]))
        vu_fixture = json.loads((AREA / "vu-reflection.json").read_text())
        need(
            native_pages == vu_fixture["native_tire_ppf"],
            "native tire texture/UV receipt differs from disc",
        )
        rim_rows = [
            r
            for r in archive.records
            if r["ordinal"] == 6479 and r["name"] == "resources/vehicle/rim.ppf"
        ]
        need(len(rim_rows) == 1, "missing native rim PPF")
        need(
            mc3_tire_vu.from_rim_ppf(archive.payload(rim_rows[0]))
            == vu_fixture["wheel_culling"]["rim_ppf"],
            "native rim culling receipt differs from disc",
        )
        rows = [r for r in archive.records if r["name"] == "shaderlib/tire.shadert"]
        need(len(rows) == 1, "missing or duplicate tire template")
        row = rows[0]
        need(
            row["ordinal"] == 6745 and row["size"] == 1162 and row["stored"] == 523,
            "tire member extent mismatch",
        )
        need(
            entries[0]["lba"] * 2048 + row["offset"] == 4238550016,
            "tire disc offset mismatch",
        )
        need(
            common.sha256(archive.read(row["offset"], row["stored"])) == STORED_SHA,
            "compressed tire template mismatch",
        )
        return archive.payload(row)
    finally:
        disc.close()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--available", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--disc",
        action="store_true",
        help="Rederive the retained template from the pinned ISO",
    )
    args = parser.parse_args(argv)
    try:
        if args.available or args.disc:
            import static_inputs

            path = static_inputs.mc3_disc()
            if args.available:
                return 0
            shader = shader_from_disc(path)
            need(
                shader == (AREA / "tire.shadert").read_bytes(),
                "retained template differs from disc",
            )
        else:
            shader = (AREA / "tire.shadert").read_bytes()
        result = receipt(shader)
        summary = {
            "native_tire_template": "verified",
            "controls": len(result["negative_controls"]),
        }
        if args.disc:
            summary.update(
                native_environment_pack="original-disc-byte-exact",
                native_scene="original-executable-and-inputs-verified",
            )
        return common.finish(result, AREA / "native-alpha.json", argv, ROOT, summary)
    except (ValueError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
