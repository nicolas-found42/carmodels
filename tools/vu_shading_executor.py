#!/usr/bin/env python3
"""Run a decoded Ford Racing 2 shading handler numerically for inspector test vectors.

This is the repository's real handler executor: tools/vu1_exec.py's NumDomain machine running the
pinned overlay microcode through the dispatch, the handler's prologue, one four-vertex loop iteration
and the tail - the same path tools/verify_vu_pass_handlers.py derives its receipt from. It exists so
the inspector's candidate shading (dealership/game-shading.mjs) can be compared with the microcode
itself by tools/test_recovered_game_shading.mjs instead of against a second copy of the formulas.

    python3 tools/vu_shading_executor.py --available         # 0 when the pinned overlays are configured
    python3 tools/vu_shading_executor.py --self-test         # both input mappings, no microcode needed
    python3 tools/vu_shading_executor.py --pass 5 < vectors.json

Pass 4 is the reflection handler (jump-table entry 4): the paraboloid lookup and the colour factor the
handler writes to the RGBA alpha lane. Pass 5 is the specular handler (entry 5): the STQ s lane and the
per-draw RGBA clamp. A vector carries {position: [x, y, z, w], normal: [x, y, z], eye: [x, y, z], q,
colour: [r, g, b]} plus, for pass 4, {rows: [9]} (TOP[12]-TOP[14]) and, for pass 5, the light inputs
{light: [r, g, b, w]}, {lightDirection: [x, y, z]} (DM[5] and DM[6]). The handler is
vertex-symmetric, so its four unrolled vertices must produce the same output; that is asserted here,
which turns a mis-mapped input plane into a failure instead of a silent pass.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import static_inputs  # noqa: E402
import vu1_decode as vd  # noqa: E402
import vu1_exec as vx  # noqa: E402
import verify_vu_pass_handlers as vph  # noqa: E402

RESIDENCY = ROOT / "research/evidence/packet-continuation/vu-overlay-residency.json"
DISPATCH = ROOT / "research/evidence/vu-dispatch/dispatch-map.json"
HANDLERS = ROOT / "research/evidence/vu-dispatch/handlers-pass4-pass5.json"
PASS_WORDS = (4, 5)
VERTICES = 4  # each handler's loop is unrolled four times
SHIFTED_BASES = (
    "P",
    "B1",
)  # per-vertex pointers that advance by three qwords per vertex
LANES = "xyzw"
# DM[5]/DM[6]/DM[7] are the handlers' light, light-direction and eye inputs; pass 4 reads only DM[7].
DM_INPUTS = {4: {7: "eye"}, 5: {5: "light", 6: "lightDirection", 7: "eye"}}
# The pass-4 matrix comes from TOP[12]-TOP[14]; both handlers take the per-draw colour from TOP[1].
MATRIX_TOP = (12, 13, 14)


def available():
    try:
        directory = Path(static_inputs.overlay_dir()).expanduser()
    except SystemExit:
        return False
    return DISPATCH.is_file() and all(
        (directory / ("overlay-%d.bin" % n)).is_file() for n in range(7)
    )


def load_program(pass_word):
    """The pinned overlay microcode and the dispatch entry for one shading handler, checked against its pins."""
    directory = Path(static_inputs.overlay_dir()).expanduser()
    residency = json.loads(RESIDENCY.read_text())
    pins = {
        entry["overlay"]: entry["sha256"]
        for entry in residency["snapshots"][0]["overlays"]
    }
    words = []
    for n in range(7):
        data = (directory / ("overlay-%d.bin" % n)).read_bytes()
        vph.need(
            vph.sha256(data) == pins[n], "overlay %d differs from the residency pin" % n
        )
        words += list(vd.pairs(data))
    dispatch = json.loads(DISPATCH.read_bytes())
    return words, dispatch["jump_table"]["entries"][pass_word]["target_address"]


def lane_of(vector, name, lane):
    """One lane of a vector field; a field shorter than four lanes maps its missing lanes to zero."""
    index = LANES.index(lane)
    values = vector[name]
    return values[index] if index < len(values) else 0.0


def lane_value(pass_word, base, index, lane, vector):
    """One handler input lane; the offsets follow the decoded per-vertex layout of the handler's loop."""
    if base == "P":
        _, qword = divmod(index, 3)
        if qword == 0:
            return (
                vector["position"][LANES.index(lane)]
                if lane != "w"
                else vector["position"][3]
            )
        if qword == 1:
            return vector["normal"][LANES.index(lane)] if lane != "w" else 0.0
        return 0.0
    if base == "B1":
        # Per vertex the preceding output carries STQ then XYZF: Q is the scale the handler writes
        # back, w is copied through, and XYZF is copied rather than read by the arithmetic.
        if (index - 1) % 3 == 0:
            return vector["q"] if lane == "z" else (1.0 if lane == "w" else 0.0)
        return 0.0
    if base == "DM":
        # Pass 5 reads DM[5].w (the RGBA alpha lane); a field shorter than four lanes maps its
        # missing lanes, including that one, to zero.
        name = DM_INPUTS[pass_word].get(index)
        return lane_of(vector, name, lane) if name else 0.0
    if base == "TOP":
        if index == 1:
            return lane_of(vector, "colour", lane)
        if pass_word == 4 and index in MATRIX_TOP:
            return (
                vector["rows"][MATRIX_TOP.index(index) * 3 + LANES.index(lane)]
                if lane != "w"
                else 0.0
            )
        return 0.0
    return 0.0


def memory_for(pass_word, reads, vector):
    """The four lanes of every qword the handler reads, for one test vector."""
    memory = {}
    for key in sorted(reads, key=lambda item: (str(item[0]), item[1])):
        base, index = key
        memory[key] = [
            vx.f32(
                lane_value(
                    pass_word, "DM" if base is None else base, index, lane, vector
                )
            )
            for lane in LANES
        ]
    return memory


def run(pass_word, vector, words, structure, reads):
    machine = vph.run_handler(
        words,
        structure,
        dom=vx.NumDomain(),
        memory=memory_for(pass_word, reads, vector),
    )
    rows = []
    for vertex in range(VERTICES):
        stq, rgba, _ = vph.vertex_outputs(machine, vertex)
        row = {
            "s": stq[0],
            "t": stq[1],
            "q": stq[2],
            "rgba": [int(value) for value in rgba],
        }
        if pass_word == 4:
            row["factor"] = rgba[3]
            row["rgb"] = row.pop("rgba")[:3]
        else:
            # The GS reads the specular back as the perspective-corrected coordinate s/q, so the
            # stored lane pair is also reported as the intensity the inspector shades with.
            row["specular"] = vx.NumDomain().div(stq[0], stq[2])
        rows.append(row)
    vph.need(
        all(row == rows[0] for row in rows),
        "the four loop vertices disagree for vector %r" % (vector,),
    )
    return rows[0]


def collect(pass_word, vectors):
    words, entry = load_program(pass_word)
    structure = vph.find_structure(words, entry)
    reads = set(vph.run_handler(words, structure).reads)
    names, keys = receipt_inputs(pass_word)
    vph.need(
        keys <= reads,
        "the handler does not read the receipt inputs: %r"
        % sorted(map(str, keys - reads)),
    )
    return {
        "pass": pass_word,
        "entry": entry,
        "receipt_input_qwords": sorted(str(key) for key in keys),
        "extra_qwords": sorted(str(key) for key in reads - keys),
        "vertices": [
            run(pass_word, vector, words, structure, reads) for vector in vectors
        ],
    }


def receipt_inputs(pass_word):
    """The input qwords the committed handler receipt names, expanded to all four vertices.

    The receipt lists one vertex's leaves; each handler is unrolled four times with P and B1 advancing
    three qwords per vertex.
    """
    receipt = json.loads(HANDLERS.read_text())
    names = receipt["handlers"][str(pass_word)]["inputs"]
    keys = set()
    for name in names:
        base, rest = name.split("[", 1)
        index, _ = rest.split("].", 1)
        key = (None if base == "DM" else base, int(index))
        keys.add(key)
        for vertex in range(1, VERTICES):
            if key[0] in SHIFTED_BASES:
                keys.add((key[0], key[1] + 3 * vertex))
    return names, keys


def self_test():
    """The input mappings need no microcode, so they are checked wherever the overlays are absent."""
    vph.need(len(PASS_WORDS) == len(set(PASS_WORDS)), "a pass word is listed twice")
    names, keys = receipt_inputs(4)
    vph.need(
        len(names) == 28 and len(keys) == 21,
        "the pass-4 receipt names %d leaves in %d qwords" % (len(names), len(keys)),
    )
    vector = {
        "position": [1.5, -2.25, 0.75, 1.5],
        "normal": [0.5, -1.25, 2.5],
        "eye": [-3.0, 4.0, -5.0],
        "rows": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
        "q": 0.5,
        "colour": [128.0, 64.0, 32.0],
    }
    memory = memory_for(4, keys, vector)
    vph.need(set(memory) == set(keys), "the mapping dropped or invented an input qword")
    vph.need(
        all(len(lanes) == 4 for lanes in memory.values()),
        "an input qword is not four lanes",
    )
    vph.need(
        memory[("P", 0)] == [vx.f32(v) for v in vector["position"]],
        "the position plane mapping differs",
    )
    vph.need(
        memory[("P", 3)] == memory[("P", 0)] and memory[("P", 6)] == memory[("P", 0)],
        "a later vertex does not repeat the position plane",
    )
    vph.need(
        memory[("P", 1)][:3] == [vx.f32(v) for v in vector["normal"]],
        "the normal plane mapping differs",
    )
    vph.need(
        memory[("B1", 1)][2] == vx.f32(0.5) and memory[("B1", 1)][3] == 1.0,
        "the preceding STQ mapping differs",
    )
    vph.need(
        memory[(None, 7)][:3] == [vx.f32(v) for v in vector["eye"]],
        "the eye mapping differs",
    )
    vph.need(
        memory[("TOP", 1)][:3] == [vx.f32(v) for v in vector["colour"]],
        "the colour mapping differs",
    )
    vph.need(
        memory[("TOP", 13)][:3] == [vx.f32(v) for v in vector["rows"][3:6]],
        "the matrix row mapping differs",
    )
    # Every named input must carry a value; only the copied-through XYZF qwords are deliberately zero.
    blank = {key for key, lanes in memory.items() if not any(lanes)}
    vph.need(
        blank == {("B1", 3 + 3 * vertex) for vertex in range(VERTICES)},
        "an input qword maps to no value: %r" % sorted(map(str, blank)),
    )
    shaded = dict(
        vector,
        light=[0.745098, 0.717647, 0.717647, 0.647059],
        lightDirection=[0.695614, -0.531002, -0.483899],
    )
    names, keys = receipt_inputs(5)
    vph.need(
        len(names) == 27 and len(keys) == 20,
        "the pass-5 receipt names %d leaves in %d qwords" % (len(names), len(keys)),
    )
    memory = memory_for(5, keys, shaded)
    vph.need(
        memory[(None, 5)] == [vx.f32(v) for v in shaded["light"]],
        "the pass-5 light mapping differs",
    )
    vph.need(
        memory[(None, 6)][:3] == [vx.f32(v) for v in shaded["lightDirection"]],
        "the pass-5 light-direction mapping differs",
    )
    vph.need(
        memory[(None, 6)][3] == 0.0,
        "the pass-5 light direction maps a w lane the handler never reads",
    )
    # The pass-5 handler also reads the per-draw colour's alpha lane, which carries TOP[1].w.
    vph.need(
        memory[("TOP", 1)] == [vx.f32(v) for v in shaded["colour"]] + [0.0],
        "the pass-5 colour mapping differs",
    )
    blank = {key for key, lanes in memory.items() if not any(lanes)}
    vph.need(
        blank == {("B1", 3 + 3 * vertex) for vertex in range(VERTICES)},
        "a pass-5 input qword maps to no value: %r" % sorted(map(str, blank)),
    )
    print(
        "PASS vu_shading_executor self-test: pass-4 and pass-5 receipt qwords mapped over %d vertices"
        % VERTICES
    )
    return 0


def main(argv):
    parser = argparse.ArgumentParser(
        description="Run a decoded shading handler numerically."
    )
    parser.add_argument(
        "--pass", dest="pass_word", type=int, choices=PASS_WORDS, default=PASS_WORDS[0]
    )
    parser.add_argument("--available", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.available:
        return 0 if available() else 1
    if arguments.self_test:
        return self_test()
    vectors = json.load(sys.stdin)["vectors"]
    vph.need(isinstance(vectors, list) and vectors, "no test vectors supplied")
    sys.stdout.write(json.dumps(collect(arguments.pass_word, vectors)) + "\n")
    return 0


if __name__ == "__main__":
    if (
        "--available" not in sys.argv
        and "--self-test" not in sys.argv
        and not available()
    ):
        sys.exit(
            "SKIP vu_shading_executor: pinned VU overlays are not configured (see docs/static-inputs.md)"
        )
    try:
        sys.exit(main(sys.argv[1:]))
    except (vph.HandlerError, KeyError) as error:
        sys.exit("EXECUTOR FAILED: " + str(error))
