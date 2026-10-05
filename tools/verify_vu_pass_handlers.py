#!/usr/bin/env python3
"""Decode the VU1 pass-4 and pass-5 handlers into per-vertex dataflow and verify the result.

Reads the overlay binaries pinned by the residency receipt, decodes them with tools/vu1_decode.py (checked
pair by pair against the pinned disassembly), runs the dispatch, one handler prologue, one loop iteration
and the tail symbolically with tools/vu1_exec.py, and writes research/evidence/vu-dispatch/handlers-pass4-pass5.json.
Nothing is executed on the game or an emulator; the formulas describe the microcode, not a captured frame.

    python3 tools/verify_vu_pass_handlers.py            # derive, cross-check, run the controls, compare with the receipt
    python3 tools/verify_vu_pass_handlers.py --write    # refresh the receipt
"""
import copy
import json
import random
import re
import struct
import sys
from pathlib import Path

import static_inputs
import verifier_common
import vu1_decode as vd
import vu1_exec as vx

ROOT = Path(__file__).resolve().parents[1]
RESIDENCY = ROOT / 'research/evidence/packet-continuation/vu-overlay-residency.json'
DISPATCH = ROOT / 'research/evidence/vu-dispatch/dispatch-map.json'
RECEIPT = ROOT / 'research/evidence/vu-dispatch/handlers-pass4-pass5.json'
PAIRS_PER_OVERLAY = 256
PASS_WORDS = (4, 5)
DISPATCH_FIRST, DISPATCH_JR = 60, 73
SHIFTED_BASES = ('P', 'B1')  # per-vertex pointers that advance by 3 qwords per vertex


class HandlerError(ValueError):
    pass


need = verifier_common.make_need(HandlerError)
sha256 = verifier_common.sha256
normalise = verifier_common.normalise


# --- inputs ----------------------------------------------------------------------------------------

def load_inputs():
    vu_dir = static_inputs.overlay_dir()
    residency = json.loads(RESIDENCY.read_text())
    overlays = {}
    for n in range(7):
        recs = [s['overlays'][n] for s in residency['snapshots']]
        binary = (vu_dir / ('overlay-%d.bin' % n)).read_bytes()
        asm_bytes = (vu_dir / ('overlay-%d.s' % n)).read_bytes()
        need(sha256(binary) == recs[0]['sha256'] and all(r['sha256'] == recs[0]['sha256'] for r in recs), 'overlay %d differs from the residency pin' % n)
        need(recs[0]['aligned_exact_offsets'] == ['0x%04x' % (n * 0x800)], 'overlay %d is not resident at 0x%04x' % (n, n * 0x800))
        asm = asm_bytes.decode().split('\n')[1:]
        while asm and asm[-1] == '':
            asm.pop()
        overlays[n] = {'bin': binary, 'asm': asm, 'bin_sha256': sha256(binary), 'asm_sha256': sha256(asm_bytes)}
    dispatch_bytes = DISPATCH.read_bytes()
    return {'overlays': overlays, 'dispatch': json.loads(dispatch_bytes), 'dispatch_sha256': sha256(dispatch_bytes)}


def clone_inputs(inp):
    return copy.deepcopy(inp)


def program(inp):
    """VU instruction memory as (lower, upper) pairs and disassembly lines, addressed by instruction pair."""
    words, asm = [], []
    for n in range(7):
        ov = inp['overlays'][n]
        words += [(lo, up) for lo, up in vd.pairs(ov['bin'])]
        asm += ov['asm']
        if n < 6:
            need(len(ov['bin']) // 8 == PAIRS_PER_OVERLAY and len(ov['asm']) == PAIRS_PER_OVERLAY, 'overlay %d does not have %d pairs' % (n, PAIRS_PER_OVERLAY))
    return words, asm


def mutate_pair(inp, address, lower=None, upper=None, consistent=False):
    """Change one pair in the overlay bytes; with consistent=True the pinned disassembly text is rewritten to match."""
    n, local = divmod(address, PAIRS_PER_OVERLAY)
    ov = inp['overlays'][n]
    lo, up = struct.unpack_from('<II', ov['bin'], local * 8)
    lo, up = (lo if lower is None else lower), (up if upper is None else upper)
    ov['bin'] = ov['bin'][:local * 8] + struct.pack('<II', lo, up) + ov['bin'][local * 8 + 8:]
    if consistent:
        ov['asm'][local] = vd.render_pair(lo, up)


def mutate_dispatch_entry(inp, index, value):
    inp['dispatch']['jump_table']['entries'][index]['target_address'] = value


# --- structure -------------------------------------------------------------------------------------

def bind(words, asm, addresses):
    """Every listed pair decodes from its bytes to the same text as the pinned disassembly."""
    for a in addresses:
        lo, up = words[a]
        mine = vd.render_pair(lo, up)
        for part, text in zip(mine.split('\t'), asm[a].split('\t')):
            if part.startswith('loi') and text.strip().startswith('loi'):
                same = abs(float(part.split()[1]) - float(text.split()[1])) <= 1e-6 * max(1.0, abs(float(text.split()[1])))
            else:
                same = normalise(part) == normalise(text)
            need(same, 'pair %d: bytes decode to %r but the disassembly says %r' % (a, part.strip(), text.strip()))


def lower_of(words, a):
    return vd.decode_pair(*words[a])[1]


def branch_target(words, a):
    f = lower_of(words, a)
    return a + 1 + f['imm11']


def find_structure(words, entry):
    """Prologue, one four-vertex loop, tail and exit branch of a handler, derived from its decoded branches."""
    a = entry
    while lower_of(words, a)['op'] not in ('ibgtz', 'b', 'jr', 'ibne', 'ibeq', 'ibltz', 'bal'):
        a += 1
        need(a < entry + 400, 'no branch found after entry %d' % entry)
    loop_branch = a
    need(lower_of(words, loop_branch)['op'] == 'ibgtz' and lower_of(words, loop_branch)['is'] == 2, 'handler at %d does not end its loop with ibgtz vi02' % entry)
    loop_start = branch_target(words, loop_branch)
    need(entry <= loop_start < loop_branch, 'loop of handler %d does not branch backwards into the handler' % entry)
    b = loop_branch + 2
    while lower_of(words, b)['op'] not in ('b', 'jr', 'ibgtz', 'ibne', 'ibeq', 'ibltz', 'bal'):
        b += 1
        need(b < loop_branch + 40, 'no exit branch after the loop of handler %d' % entry)
    need(lower_of(words, b)['op'] == 'b', 'handler %d tail does not end in an unconditional branch' % entry)
    kicks = [p for p in range(loop_branch + 2, b) if lower_of(words, p)['op'] == 'xgkick']
    need(len(kicks) == 1, 'handler %d tail does not have exactly one xgkick' % entry)
    return {'entry': entry, 'loop_start': loop_start, 'loop_branch': loop_branch, 'loop_delay_slot': loop_branch + 1,
            'tail_kick': kicks[0], 'tail_branch': b, 'exit_target': branch_target(words, b)}


def derive_epilogue(words, exit_target):
    """The shared epilogue every handler branches to: stop-address store, flag test, optional kick, E-bit stop, branch back."""
    ops = []
    a = exit_target
    while True:
        f = lower_of(words, a)
        ops.append((a, f))
        if f['op'] == 'b':
            break
        a += 1
        need(a < exit_target + 30, 'epilogue does not end in a branch')
    branch_back = branch_target(words, a)
    flag_test = [(p, f) for p, f in ops if f['op'] == 'ibne'][0]
    kick = [p for p, f in ops if f['op'] == 'xgkick']
    stop = [p for p in range(exit_target, a + 2) if vd.decode_upper(words[p][1])['e']]
    loads = {f['it']: f['imm15'] for _, f in ops if f['op'] == 'iaddiu'}
    need(len(kick) == 1 and len(stop) == 1 and sorted(loads) == [2, 9], 'epilogue does not have one kick, one E-bit pair and the vi02 and vi09 constants')
    stores = [f for _, f in ops if f['op'] == 'isw']
    need(len(stores) == 1 and stores[0]['dest'] == 'w' and stores[0]['imm11'] == 59, 'epilogue does not store the next entry at DM[59].w')
    return {'first_pair': exit_target, 'next_entry_store': {'address': 'DM[59].w', 'value': loads[2]},
            'flag_mask_tested_on_vi13': loads[9], 'kick_register': 'vi%02d' % lower_of(words, kick[0])['is'], 'kick_pair': kick[0],
            'flag_set_branch': {'pair': flag_test[0], 'target': branch_target(words, flag_test[0])}, 'e_bit_pair': stop[0], 'branch_back_pair': a,
            'branch_back_target': branch_back}


# --- symbolic run ----------------------------------------------------------------------------------

def run_handler(words, st, dom=None, memory=None):
    m = vx.Machine(dom or vx.SymDomain(), memory)
    m.vi[11], m.vi[12] = vx.IV('B1', 0), vx.IV('B0', 0)
    vx.run_pairs(m, words[DISPATCH_FIRST:DISPATCH_JR])  # xtop .. the pair before jr
    need(repr(m.vi[3]) == 'TOP[0].z' and repr(m.vi[4]) == 'B0+1' and repr(m.vi[2]) == 'TOP[0].y', 'dispatch left unexpected pointer registers')
    m.vi[3] = vx.IV('P', 0)
    vx.run_pairs(m, words[st['entry']:st['loop_start']])
    need(not m.branches, 'branch inside the prologue of handler %d' % st['entry'])
    vx.run_pairs(m, words[st['loop_start']:st['loop_branch'] + 2])
    need(m.branches == ['ibgtz'], 'loop body contains branches other than its ibgtz')
    vx.run_pairs(m, words[st['loop_branch'] + 2:st['tail_branch'] + 2])
    return m


def canonical(text, vertex):
    """Shift per-vertex pointer offsets back by three qwords per vertex so the four vertices can be compared."""
    def shift(m):
        return '%s[%d]' % (m.group(1), int(m.group(2)) - 3 * vertex)
    return re.sub(r'\b(%s)\[(\d+)\]' % '|'.join(SHIFTED_BASES), shift, text)


def vertex_outputs(m, vertex):
    out = []
    for j in range(3):
        key = ('B0', 1 + 3 * vertex + j)
        found = [v for k, d, v in m.stores if k == key and d == 'xyzw']
        need(len(found) == 1, 'qword %s of vertex %d is not written exactly once' % (key, vertex))
        out.append(found[0])
    return out


def derive_handler(words, pass_word, entry):
    st = find_structure(words, entry)
    m = run_handler(words, st)
    need(m.kicks and repr(m.kicks[0]).isdigit(), 'handler %d does not kick a static address' % entry)
    # the loop advances the plane, output and previous-output pointers by 12 qwords and the counter by 4
    adv = {'P': m.vi[3], 'B0': m.vi[4], 'B1': m.vi[6]}
    need(repr(adv['P']) == 'P+12' and repr(adv['B0']) == 'B0+13' and repr(adv['B1']) == 'B1+13' and repr(m.vi[2]) == 'TOP[0].y-4',
         'loop pointer or counter update is not 12 qwords and 4 vertices: %r' % {k: repr(v) for k, v in adv.items()})
    # vertex symmetry: every vertex computes the same formulas after the per-vertex shift
    texts = []
    for vtx in range(4):
        row = []
        for qw in vertex_outputs(m, vtx):
            row.append([canonical(vx.text(x), vtx) for x in qw])
        texts.append(row)
    need(all(t == texts[0] for t in texts[1:]), 'the four unrolled vertices do not compute the same formulas')
    roots = [x for qw in vertex_outputs(m, 0) for x in qw]
    bindings, rendered = vx.ssa(roots)
    lanes = [rendered[i:i + 4] for i in (0, 4, 8)]
    reads = sorted({vx_leaf for r in roots for vx_leaf in vx.leaves(r)})
    gif_tag = [v for k, _, v in m.stores if k == ('B0', 0)]
    need(len(gif_tag) == 1 and [vx.text(x) for x in gif_tag[0]] == ['TOP[2].%s' % c for c in 'xyzw'], 'GIF tag is not copied from TOP[2]')
    flag = [(k, d, [repr(x) for x in v]) for k, d, v in m.stores if k[0] is None and k[1] == 59]
    need(flag == [((None, 59), 'y', ['(DM[59].y | 1)'])], 'unexpected DM[59] write: %r' % flag)
    return {'pass_word': pass_word, 'entry_address': entry, 'overlay': entry // PAIRS_PER_OVERLAY, 'local_pair': entry % PAIRS_PER_OVERLAY,
            'pairs': {k: v for k, v in st.items() if k not in ('entry', 'exit_target')} | {'entry': entry},
            'loop': {'vertices_per_iteration': 4, 'qwords_per_vertex': 3, 'counter': 'TOP[0].y', 'counter_step': -4, 'pointer_step_qwords': 12,
                     'pointers': {'P': 'plane base TOP[0].z', 'B0': 'output buffer (vi11)', 'B1': 'previous output buffer (vi12)'}},
            'static_kick': {'pair': st['tail_kick'], 'dm_address': int(repr(m.kicks[0]))},
            'dm59_y_write': 'DM[59].y = DM[59].y | 1', 'exit_target': st['exit_target'],
            'output_layout': 'B0[0] = TOP[2] (GIF tag); vertex k writes B0[1+3k] STQ, B0[2+3k] RGBA, B0[3+3k] XYZF',
            'vertex0': {'bindings': [[n, b] for n, b in bindings], 'stq': lanes[0], 'rgba': lanes[1], 'xyzf': lanes[2]},
            'vertices_identical_after_shift': True,
            'inputs': reads}


def numeric_cross_check(words, st, seeds=40):
    """Evaluate the symbolic outputs numerically and compare with a run of the same code in the numeric domain."""
    sym_machine = run_handler(words, st)
    roots = {}
    for vtx in range(4):
        for j, qw in enumerate(vertex_outputs(sym_machine, vtx)):
            for lane, expr in enumerate(qw):
                roots[(vtx, j, lane)] = expr
    names = set()
    for expr in roots.values():
        names |= vx.leaves(expr)
    keys = sorted(set(sym_machine.reads), key=lambda k: (str(k[0]), k[1]))
    checked = 0
    for seed in range(seeds):
        rng = random.Random(seed)
        env = {n: vx.f32(rng.uniform(-2.0, 2.0)) for n in sorted(names)}
        memory = {}
        for key in keys:
            base, off = key
            name = 'DM[%d]' % off if base is None else '%s[%d]' % (base, off)
            memory[key] = [env.get('%s.%s' % (name, c), vx.f32(rng.uniform(-2.0, 2.0))) for c in 'xyzw']
        num_machine = run_handler(words, st, dom=vx.NumDomain(), memory=memory)
        for vtx in range(4):
            for j, qw in enumerate(vertex_outputs(num_machine, vtx)):
                for lane, value in enumerate(qw):
                    expected = vx.evaluate(roots[(vtx, j, lane)], env)
                    need(value == expected, 'seed %d vertex %d qword %d lane %d: numeric run %r, expression %r' % (seed, vtx, j, lane, value, expected))
                    checked += 1
    return checked


def matrix_prologue(words):
    """Track the retained matrix packet into the fixed DM input qwords."""
    machine = vx.Machine(vx.SymDomain())
    vx.run_pairs(machine, words[26:60])
    stores = {str(k[1]): [vx.text(x) for x in values]
              for k, _, values in machine.stores if k[0] is None and k[1] in (5, 6, 7)}
    expected = {'5': ['TOP[21].%s' % c for c in 'xyzw'],
                '6': ['-TOP[22].%s' % c for c in 'xyz'] + ['TOP[22].w'],
                '7': ['TOP[23].%s' % c for c in 'xyzw']}
    need(stores == expected, 'matrix prologue DM5/6/7 input mapping differs')
    return {'pairs': [26, 59], 'dm_inputs': stores}


def derive(inp):
    words, asm = program(inp)
    entries = inp['dispatch']['jump_table']['entries']
    handlers, bound, structures = {}, set(range(26, DISPATCH_JR + 1)), {}
    prologue = matrix_prologue(words)
    for pass_word in PASS_WORDS:
        entry = entries[pass_word]['target_address']
        need(entries[pass_word]['index'] == pass_word, 'dispatch receipt entry %d has the wrong index' % pass_word)
        st = find_structure(words, entry)
        structures[pass_word] = st
        bound |= set(range(entry, st['tail_branch'] + 2))
    epi_start = structures[4]['exit_target']
    need(all(s['exit_target'] == epi_start for s in structures.values()), 'handlers do not share one epilogue')
    epilogue = derive_epilogue(words, epi_start)
    bound |= set(range(epi_start, epilogue['branch_back_pair'] + 2))
    bind(words, asm, sorted(bound))
    need(epilogue['branch_back_target'] == DISPATCH_FIRST, 'epilogue does not branch back to the dispatch xtop')
    for pass_word in PASS_WORDS:
        handlers[str(pass_word)] = derive_handler(words, pass_word, structures[pass_word]['entry'])
    checked = {str(p): numeric_cross_check(words, structures[p]) for p in PASS_WORDS}
    return {
        'schema': 'fr2-vu-pass-handlers/v1',
        'scope': 'Symbolic decode of the VU1 handlers for pass words 4 and 5 (jump-table entries 4 and 5); no code was executed and no frame was captured.',
        'render_fidelity_complete': False,
        'pins': {'dispatch_map_sha256': inp['dispatch_sha256'],
                 'overlays': {str(n): {'bin_sha256': inp['overlays'][n]['bin_sha256'], 'asm_sha256': inp['overlays'][n]['asm_sha256']} for n in range(7)}},
        'decoder': 'tools/vu1_decode.py, from the VU1 instruction layout; every pair used here equals the pinned disassembly text',
        'bound_pairs': len(bound),
        'handlers': handlers,
        'matrix_prologue': prologue,
        'epilogue': epilogue,
        'numeric_cross_check_values': checked,
        'claim_limits': [
            'Static derivation of the microcode only. Captured packet comparisons and retained matrix inputs are checked separately by verify_vu_handler_dump.py; the per-vertex working planes and live dispatch are not established here.',
            'Host numeric reconstruction is not bit-exact VU arithmetic. Formulas treat Q and P results as available to the next pair, ignore FMAC latency, flags and denormal timing, and assume finite inputs where a product with zero is folded to zero.',
            'The producer of the static kick packets (DM 0x25 for pass 4, 0x1c for pass 5) and the flag-0x100 clip path at the epilogue branch target were not decoded.',
            'Interpreting the formulas (reflection-map coordinates, specular intensity, colour factors) is a reading of the arithmetic; this static receipt does not compare a frame.',
        ],
    }


def make_controls():
    entry4 = 558
    return [
        ('matrix prologue DM5 store moved', lambda i: mutate_pair(i, 51, lower=0x03e07004, consistent=True)),
        ('handler lower word bit flipped', lambda i: mutate_pair(i, 600, lower=struct.unpack_from('<II', i['overlays'][2]['bin'], (600 - 512) * 8)[0] ^ 1)),
        ('handler upper word op changed', lambda i: mutate_pair(i, 600, upper=struct.unpack_from('<II', i['overlays'][2]['bin'], (600 - 512) * 8)[1] ^ 2)),
        ('dispatch entry for pass 4 moved', lambda i: mutate_dispatch_entry(i, 4, entry4 + 1)),
        ('loop counter step changed, text rewritten to match', lambda i: mutate_pair(i, 579, lower=struct.unpack_from('<II', i['overlays'][2]['bin'], (579 - 512) * 8)[0] ^ (0x1c ^ 0x1d) << 6, consistent=True)),
        ('vertex 2 plane offset changed, text rewritten to match', lambda i: mutate_pair(i, 577, lower=struct.unpack_from('<II', i['overlays'][2]['bin'], (577 - 512) * 8)[0] ^ 1, consistent=True)),
        ('colour factor constant changed, text rewritten to match', lambda i: mutate_pair(i, 565, lower=struct.unpack('<I', struct.pack('<f', -0.9))[0], consistent=True)),
        ('static kick address changed, text rewritten to match', lambda i: mutate_pair(i, 689, lower=struct.unpack_from('<II', i['overlays'][2]['bin'], (689 - 512) * 8)[0] ^ 0x1, consistent=True)),
        ('pass 5 colour clamp constant changed, text rewritten to match', lambda i: mutate_pair(i, 476, lower=struct.unpack('<I', struct.pack('<f', 64.0))[0], consistent=True)),
    ]


CONTROLS = make_controls()


def run_controls(inp, baseline):
    """Reject changed words, structure or formulas through the shared control runner."""
    return verifier_common.run_controls(inp, CONTROLS, derive, HandlerError,
                                        clone=clone_inputs, baseline=baseline)


def main(argv):
    inp = load_inputs()
    receipt = derive(inp)
    receipt['controls'] = run_controls(inp, derive(inp))
    summary = {'handlers': {k: {'entry': v['entry_address'], 'kick': v['static_kick']['dm_address']} for k, v in receipt['handlers'].items()},
                      'epilogue_first_pair': receipt['epilogue']['first_pair'], 'numeric_cross_check_values': receipt['numeric_cross_check_values'],
                      'controls_rejected': sum(c['rejected'] for c in receipt['controls']), 'controls': len(receipt['controls'])}
    return verifier_common.finish(receipt, RECEIPT, argv, ROOT, summary)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
