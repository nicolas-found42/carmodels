#!/usr/bin/env python3
"""Run the decoded pass-4 VU1 handler numerically for inspector test vectors.

This is the repository's real handler executor: tools/vu1_exec.py's NumDomain machine running the
pinned overlay microcode through the dispatch, the pass-4 prologue, one four-vertex loop iteration
and the tail - the same path tools/verify_vu_pass_handlers.py derives its receipt from. It exists so
the inspector's candidate shading (dealership/game-shading.mjs) can be compared with the microcode
itself by tools/test_recovered_game_shading.mjs instead of against a second copy of the formulas.

    python3 tools/vu_pass4_executor.py --available      # 0 when the pinned overlays are configured
    python3 tools/vu_pass4_executor.py < vectors.json    # {"vectors": [...]} on stdin, JSON out

A vector is {position: [x, y, z, w], normal: [x, y, z], eye: [x, y, z], rows: [9], q, colour: [r, g, b]}.
The handler is vertex-symmetric, so its four unrolled vertices must produce the same output; that is
asserted here, which turns a mis-mapped input plane into a failure instead of a silent pass.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import static_inputs  # noqa: E402
import vu1_decode as vd  # noqa: E402
import vu1_exec as vx  # noqa: E402
import verify_vu_pass_handlers as vph  # noqa: E402

RESIDENCY = ROOT / 'research/evidence/packet-continuation/vu-overlay-residency.json'
DISPATCH = ROOT / 'research/evidence/vu-dispatch/dispatch-map.json'
HANDLERS = ROOT / 'research/evidence/vu-dispatch/handlers-pass4-pass5.json'
PASS_WORD = 4
VERTICES = 4  # the handler's loop is unrolled four times
SHIFTED_BASES = ('P', 'B1')  # per-vertex pointers that advance by three qwords per vertex
LANES = 'xyzw'


def available():
    try:
        directory = Path(static_inputs.overlay_dir()).expanduser()
    except SystemExit:
        return False
    return DISPATCH.is_file() and all((directory / ('overlay-%d.bin' % n)).is_file() for n in range(7))


def load_program():
    """The pinned overlay microcode and the pass-4 dispatch entry, checked against their pins."""
    directory = Path(static_inputs.overlay_dir()).expanduser()
    residency = json.loads(RESIDENCY.read_text())
    pins = {entry['overlay']: entry['sha256'] for entry in residency['snapshots'][0]['overlays']}
    words = []
    for n in range(7):
        data = (directory / ('overlay-%d.bin' % n)).read_bytes()
        vph.need(vph.sha256(data) == pins[n], 'overlay %d differs from the residency pin' % n)
        words += list(vd.pairs(data))
    dispatch = json.loads(DISPATCH.read_bytes())
    return words, dispatch['jump_table']['entries'][PASS_WORD]['target_address']


def lane_value(base, index, lane, vector):
    """One handler input lane; the offsets follow the decoded per-vertex layout of the pass-4 loop."""
    if base == 'P':
        _, qword = divmod(index, 3)
        if qword == 0:
            return vector['position'][LANES.index(lane)] if lane != 'w' else vector['position'][3]
        if qword == 1:
            return vector['normal'][LANES.index(lane)] if lane != 'w' else 0.0
        return 0.0
    if base == 'B1':
        # Per vertex the preceding output carries STQ then XYZF: Q is the scale the handler writes
        # back, w is copied through, and XYZF is copied rather than read by the arithmetic.
        if (index - 1) % 3 == 0:
            return vector['q'] if lane == 'z' else (1.0 if lane == 'w' else 0.0)
        return 0.0
    if base == 'DM':
        return vector['eye'][LANES.index(lane)] if index == 7 and lane != 'w' else 0.0
    if base == 'TOP':
        if 12 <= index <= 14:
            return vector['rows'][(index - 12) * 3 + LANES.index(lane)] if lane != 'w' else 0.0
        if index == 1:
            return vector['colour'][LANES.index(lane)] if lane != 'w' else 0.0
        return 0.0
    return 0.0


def memory_for(reads, vector):
    """The four lanes of every qword the handler reads, for one test vector."""
    memory = {}
    for key in sorted(reads, key=lambda item: (str(item[0]), item[1])):
        base, index = key
        memory[key] = [vx.f32(lane_value('DM' if base is None else base, index, lane, vector)) for lane in LANES]
    return memory


def run(vector, words, structure, reads):
    machine = vph.run_handler(words, structure, dom=vx.NumDomain(), memory=memory_for(reads, vector))
    rows = []
    for vertex in range(VERTICES):
        stq, rgba, _ = vph.vertex_outputs(machine, vertex)
        rows.append({'s': stq[0], 't': stq[1], 'q': stq[2], 'factor': rgba[3], 'rgb': [int(value) for value in rgba[:3]]})
    vph.need(all(row == rows[0] for row in rows), 'the four loop vertices disagree for vector %r' % (vector,))
    return rows[0]


def collect(vectors):
    words, entry = load_program()
    structure = vph.find_structure(words, entry)
    reads = set(vph.run_handler(words, structure).reads)
    names, keys = receipt_inputs()
    vph.need(keys <= reads, 'the handler does not read the receipt inputs: %r' % sorted(map(str, keys - reads)))
    return {'entry': entry, 'receipt_input_qwords': sorted(str(key) for key in keys),
            'extra_qwords': sorted(str(key) for key in reads - keys),
            'vertices': [run(vector, words, structure, reads) for vector in vectors]}


def receipt_inputs():
    """The pass-4 input qwords the committed handler receipt names, expanded to all four vertices.

    The receipt lists one vertex's leaves (P[0], P[1], B1[1], B1[3], DM[7], TOP[1], TOP[12]-TOP[14]);
    the handler is unrolled four times with P and B1 advancing three qwords per vertex.
    """
    receipt = json.loads(HANDLERS.read_text())
    names = receipt['handlers'][str(PASS_WORD)]['inputs']
    keys = set()
    for name in names:
        base, rest = name.split('[', 1)
        index, _ = rest.split('].', 1)
        key = (None if base == 'DM' else base, int(index))
        keys.add(key)
        for vertex in range(1, VERTICES):
            if key[0] in SHIFTED_BASES:
                keys.add((key[0], key[1] + 3 * vertex))
    return names, keys


def self_test():
    """The input mapping needs no microcode, so it is checked wherever the overlays are absent."""
    names, keys = receipt_inputs()
    vph.need(len(names) == 28 and len(keys) == 21, 'the receipt names %d leaves in %d qwords' % (len(names), len(keys)))
    vector = {'position': [1.5, -2.25, 0.75, 1.5], 'normal': [0.5, -1.25, 2.5], 'eye': [-3.0, 4.0, -5.0],
              'rows': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 'q': 0.5, 'colour': [128.0, 64.0, 32.0]}
    memory = memory_for(keys, vector)
    vph.need(set(memory) == set(keys), 'the mapping dropped or invented an input qword')
    vph.need(all(len(lanes) == 4 for lanes in memory.values()), 'an input qword is not four lanes')
    vph.need(memory[('P', 0)] == [vx.f32(v) for v in vector['position']], 'the position plane mapping differs')
    vph.need(memory[('P', 3)] == memory[('P', 0)] and memory[('P', 6)] == memory[('P', 0)], 'a later vertex does not repeat the position plane')
    vph.need(memory[('P', 1)][:3] == [vx.f32(v) for v in vector['normal']], 'the normal plane mapping differs')
    vph.need(memory[('B1', 1)][2] == vx.f32(0.5) and memory[('B1', 1)][3] == 1.0, 'the preceding STQ mapping differs')
    vph.need(memory[(None, 7)][:3] == [vx.f32(v) for v in vector['eye']], 'the eye mapping differs')
    vph.need(memory[('TOP', 1)][:3] == [vx.f32(v) for v in vector['colour']], 'the colour mapping differs')
    vph.need(memory[('TOP', 13)][:3] == [vx.f32(v) for v in vector['rows'][3:6]], 'the matrix row mapping differs')
    # Every named input must carry a value; only the copied-through XYZF qwords are deliberately zero.
    blank = {key for key, lanes in memory.items() if not any(lanes)}
    vph.need(blank == {('B1', 3 + 3 * vertex) for vertex in range(VERTICES)},
              'an input qword maps to no value: %r' % sorted(map(str, blank)))
    print('PASS vu_pass4_executor self-test: %d receipt qwords mapped over %d vertices' % (len(keys), VERTICES))
    return 0


def main(argv):
    if '--available' in argv:
        return 0 if available() else 1
    if '--self-test' in argv:
        return self_test()
    vectors = json.load(sys.stdin)['vectors']
    vph.need(isinstance(vectors, list) and vectors, 'no test vectors supplied')
    sys.stdout.write(json.dumps(collect(vectors)) + '\n')
    return 0


if __name__ == '__main__':
    if '--available' not in sys.argv and '--self-test' not in sys.argv and not available():
        sys.exit('SKIP vu_pass4_executor: pinned VU overlays are not configured (see docs/static-inputs.md)')
    try:
        sys.exit(main(sys.argv[1:]))
    except (vph.HandlerError, KeyError) as error:
        sys.exit('EXECUTOR FAILED: ' + str(error))
