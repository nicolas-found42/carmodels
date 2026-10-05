#!/usr/bin/env python3
"""Derive and verify the static VU1 dispatch map for the car packet path.

Everything here is read from pinned static sources: the overlay binaries and their disassembly, the
PS2 ELF, and the typed Ghidra export of the sibling reverse-engineering checkout. Nothing is executed
and no emulator runs. The receipt is a statically derived relationship, not an execution trace.

    python3 tools/verify_vu_dispatch_map.py            # derive, run the controls, compare with the receipt
    python3 tools/verify_vu_dispatch_map.py --write    # refresh research/evidence/vu-dispatch/dispatch-map.json
"""
import copy
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1] / 'reverse-engineering'
EXPORT = SOURCE / '.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po'
ELF = SOURCE / 'games/ford-racing-2/extracted/SLES_517.05'
VU_DIR = SOURCE / '.scratch/evidence/vu/private-work-016dac24781c4c9ea7c99aa0fa79c310'
REFRESH = ROOT / 'research/evidence/continuation/source-refresh/refresh-identity.json'
RESIDENCY = ROOT / 'research/evidence/packet-continuation/vu-overlay-residency.json'
RECEIPT = ROOT / 'research/evidence/vu-dispatch/dispatch-map.json'
SNAPSHOT = ROOT / 'research/evidence/continuation/runtime/race94-vu1MicroMem.bin'  # gitignored; used when present

OVERLAYS = range(7)  # overlay 7 has no exact aligned window in any captured micro memory
VU_NOP_LOWER, VU_NOP_UPPER = 0x8000033C, 0x000002FF
GP_NAMES = {-0x6DF4: 'mscal0', -0x6DF0: 'main_car_path', -0x6DEC: 'overlay5_path'}
NEEDED_FUNCTIONS = ['0022fda8', '0021bb48', '0021c3e0', '00128ca0', '001124c0', '0021cc88', '0021ced0']
DECOMPILED_CALLERS = ['0021cc88', '0021ced0', '0021c3e0']
DEST_FIRST = {'lui', 'addiu', 'ori', 'or', 'addu', 'subu', 'lw', 'li', 'move', 'sll', 'srl', 'andi', 'and', 'daddu', 'dsll', 'dsll32',
              'slt', 'sltu', 'movn', 'movz', 'lbu', 'lhu', 'lh', 'lb', 'ld', 'por', 'sra'}
REGISTERS = 'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split()


class DispatchError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise DispatchError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --- VU1 words -------------------------------------------------------------------------------------

LANES = {8: 'x', 4: 'y', 2: 'z', 1: 'w'}


def lower_text(word):
    """Canonical text for the VU1 lower instructions this derivation relies on; anything else is unknown."""
    if word == VU_NOP_LOWER:
        return 'nop'
    top7, op11 = word >> 25, word & 0x7FF
    it, is_, id_ = (word >> 16) & 31, (word >> 11) & 31, (word >> 6) & 31
    dest = (word >> 21) & 15
    if top7 == 8:
        return 'iaddiu vi%02d,vi%02d,%d' % (it, is_, (dest << 11) | (word & 0x7FF))
    if top7 == 5:
        return 'isw.%s vi%02d,%d(vi%02d)%s' % (LANES[dest], it, word & 0x7FF, is_, LANES[dest])
    if top7 == 0:
        return 'lq.xyzw vf%02dxyzw,%d(vi%02d)' % (it, word & 0x7FF, is_) if dest == 15 else '?lq'
    if top7 == 0x24:
        return 'jr vi%02d' % is_
    if top7 == 0x40:
        if op11 == 0x6BC:
            return 'xtop vi%02d' % it
        if op11 == 0x3FE:
            return 'ilwr.%s vi%02d,(vi%02d)%s' % (LANES[dest], it, is_, LANES[dest])
        if op11 & 0x3F == 0x30:
            return 'iadd vi%02d,vi%02d,vi%02d' % (id_, is_, it)
    return '?0x%08x' % word


def normalise(text):
    return re.sub(r'(?<![\w])(0x[0-9a-f]+|\d+)(?![\w])', lambda m: str(int(m.group(1), 0)), text.strip())


def pair_words(binary, pair):
    return struct.unpack_from('<II', binary, pair * 8)


def asm_lower(asm, pair):
    return asm[pair].split('\t', 1)[1].strip()


def bound_lower(inp, overlay, pair):
    """Lower word of an overlay pair, checked against the pinned disassembly's text for that pair."""
    ov = inp['overlays'][overlay]
    word = pair_words(ov['bin'], pair)[0]
    text = lower_text(word)
    need(not text.startswith('?'), 'overlay %d pair %d: undecoded lower word 0x%08x' % (overlay, pair, word))
    need(normalise(text) == normalise(asm_lower(ov['asm'], pair)),
         'overlay %d pair %d: bytes decode to %r but disassembly says %r' % (overlay, pair, text, asm_lower(ov['asm'], pair)))
    return word, text


# --- inputs and mutation helpers -------------------------------------------------------------------

def load_inputs():
    refresh = json.loads(REFRESH.read_text())
    raw = (EXPORT / 'inventory.json').read_bytes()
    need(sha256(raw) == refresh['inventory_sha256'], 'typed inventory differs from refresh identity')
    inventory = json.loads(raw)
    elf = ELF.read_bytes()
    need(sha256(elf) == refresh['executable_sha256'], 'ELF differs from refresh identity')
    callees, callers, functions, jal = {}, {}, {}, {}
    for f in inventory['functions']:
        callees[f['entry']], callers[f['entry']] = f['callees'], f['callers']
        text = ' '.join(i['text'] for i in f['instructions'])
        if f['entry'] in NEEDED_FUNCTIONS or any('%s(gp)' % signed_hex(k) in text for k in GP_NAMES):
            functions[f['entry']] = {'instructions': f['instructions']}
        for i in f['instructions']:
            if i['text'].lstrip('_') == 'jal 0x0021bb48':
                jal.setdefault(f['entry'], []).append(i['address'])
    decompiled = {}
    for entry in DECOMPILED_CALLERS:
        data = (EXPORT / 'decompilation/functions' / (entry + '.c')).read_bytes()
        decompiled[entry] = {'text': data.decode(), 'sha256': sha256(data)}
    residency = json.loads(RESIDENCY.read_text())
    snapshots = residency['snapshots']
    overlays, offsets = {}, {}
    for n in OVERLAYS:
        rec = [s['overlays'][n] for s in snapshots]
        need(all(r['sha256'] == rec[0]['sha256'] and r['aligned_exact_offsets'] == rec[0]['aligned_exact_offsets'] for r in rec),
             'overlay %d residency differs between captures' % n)
        binary = (VU_DIR / ('overlay-%d.bin' % n)).read_bytes()
        asm_bytes = (VU_DIR / ('overlay-%d.s' % n)).read_bytes()
        need(sha256(binary) == rec[0]['sha256'], 'overlay %d binary differs from the residency receipt pin' % n)
        asm = asm_bytes.decode().split('\n')[1:]
        if asm and asm[-1] == '':
            asm.pop()
        overlays[n] = {'bin': binary, 'asm': asm, 'bin_sha256': sha256(binary), 'asm_sha256': sha256(asm_bytes)}
        need(len(rec[0]['aligned_exact_offsets']) == 1, 'overlay %d does not have exactly one exact window' % n)
        offsets[n] = int(rec[0]['aligned_exact_offsets'][0], 16)
    snapshot = SNAPSHOT.read_bytes() if SNAPSHOT.exists() else None
    return {'refresh': refresh, 'elf': elf, 'elf_sha256': sha256(elf), 'inventory_sha256': sha256(raw),
            'callees': callees, 'callers': callers, 'functions': functions, 'jal_sites': jal,
            'decompiled': decompiled, 'overlays': overlays, 'residency_offsets': offsets,
            'residency_receipt_sha256': sha256(RESIDENCY.read_bytes()), 'snapshot': snapshot}


def clone_inputs(inp):
    out = {k: v for k, v in inp.items() if k not in ('callees', 'callers', 'functions', 'decompiled', 'overlays', 'residency_offsets')}
    for k in ('callees', 'callers', 'functions', 'decompiled', 'overlays', 'residency_offsets'):
        out[k] = copy.deepcopy(inp[k])
    return out


def mutate_overlay_lower(inp, overlay, pair, xor_mask):
    ov = inp['overlays'][overlay]
    lo, up = pair_words(ov['bin'], pair)
    ov['bin'] = ov['bin'][:pair * 8] + struct.pack('<II', lo ^ xor_mask, up) + ov['bin'][pair * 8 + 8:]


def mutate_overlay_upper(inp, overlay, pair, value):
    ov = inp['overlays'][overlay]
    lo, _ = pair_words(ov['bin'], pair)
    ov['bin'] = ov['bin'][:pair * 8] + struct.pack('<II', lo, value) + ov['bin'][pair * 8 + 8:]


def mutate_residency(inp, overlay, offset):
    inp['residency_offsets'][overlay] = offset


def mutate_call_edge(inp, caller, callee, both=False):
    inp['callees'][caller] = [c for c in inp['callees'][caller] if c != callee]
    if both:
        inp['callers'][callee] = [c for c in inp['callers'][callee] if c != caller]


def swap_residency(inp, a, b):
    inp['residency_offsets'][a], inp['residency_offsets'][b] = inp['residency_offsets'][b], inp['residency_offsets'][a]


def mutate_ee_instruction(inp, function, address, text):
    for ins in inp['functions'][function]['instructions']:
        if ins['address'] == address:
            ins['text'] = text
            return
    raise KeyError(address)


def mutate_ee_bytes(inp, function, address, hex_bytes):
    for ins in inp['functions'][function]['instructions']:
        if ins['address'] == address:
            ins['bytes'] = hex_bytes
            return
    raise KeyError(address)


def mutate_asm(inp, overlay, pair, text):
    inp['overlays'][overlay]['asm'][pair] = text


def mutate_decompilation(inp, function, old, new):
    d = inp['decompiled'][function]
    need(old in d['text'], 'mutation target absent')
    d['text'] = d['text'].replace(old, new)


# --- EE instructions -------------------------------------------------------------------------------

def elf_loads(elf):
    phoff = struct.unpack_from('<I', elf, 28)[0]
    stride, count = struct.unpack_from('<HH', elf, 42)
    loads = []
    for i in range(count):
        kind, offset, va, _, size = struct.unpack_from('<5I', elf, phoff + i * stride)
        if kind == 1:
            loads.append((va, va + size, offset))
    return loads


def signed_hex(v):
    return '-0x%x' % -v if v < 0 else '0x%x' % v


def decode_ee(word):
    """Decode only the EE instruction subset the derivation asserts on."""
    op, rs, rt, rd, sa, fn = word >> 26, (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31, (word >> 6) & 31, word & 63
    imm = word & 0xFFFF
    simm = imm - 65536 if imm >= 32768 else imm
    r = REGISTERS
    if op == 0x0F:
        return 'lui %s,0x%x' % (r[rt], imm)
    if op == 0x09:
        return 'addiu %s,%s,%s' % (r[rt], r[rs], signed_hex(simm))
    if op == 0x0D:
        return 'ori %s,%s,0x%x' % (r[rt], r[rs], imm)
    if op in (0x23, 0x2B):
        return '%s %s,%s(%s)' % ('lw' if op == 0x23 else 'sw', r[rt], signed_hex(simm), r[rs])
    if op == 0 and fn == 0x23:
        return 'subu %s,%s,%s' % (r[rd], r[rs], r[rt])
    if op == 0 and fn == 0x25:
        return 'or %s,%s,%s' % (r[rd], r[rs], r[rt])
    if op == 0 and fn == 2 and rs == 0:
        return 'srl %s,%s,0x%x' % (r[rd], r[rt], sa)
    return None


def bind_function(inp, entry):
    """Every instruction word of the function equals the ELF word; decoded subset also matches its text."""
    loads = elf_loads(inp['elf'])
    for ins in inp['functions'][entry]['instructions']:
        address = int(ins['address'], 16)
        payload = bytes.fromhex(ins['bytes'])
        spans = [x for x in loads if x[0] <= address and address + 4 <= x[1]]
        need(len(spans) == 1 and len(payload) == 4, '%s: instruction outside a unique load segment' % ins['address'])
        start, _, offset = spans[0]
        need(inp['elf'][offset + address - start:offset + address - start + 4] == payload, '%s: instruction bytes differ from the ELF' % ins['address'])
        decoded = decode_ee(struct.unpack('<I', payload)[0])
        text = ins['text'].lstrip('_')
        if decoded is not None and decoded.split(' ')[0] == text.split(' ')[0]:
            need(decoded == text, '%s: text %r differs from decoded %r' % (ins['address'], text, decoded))


def note_write(held, text, lui):
    """Track registers last set to 0x14000000 by a lui; any other write to the register clears it."""
    m = re.match(r'(\w+) (\w+)', text)
    if not m or m.group(1) not in DEST_FIRST:
        return
    if text == 'lui %s,0x1400' % m.group(2):
        held[m.group(2)] = True
    else:
        held.pop(m.group(2), None)


def by_address(inp, entry):
    return {i['address']: i for i in inp['functions'][entry]['instructions']}


def text_at(inp, entry, address):
    return by_address(inp, entry)[address]['text'].lstrip('_')


# --- derivation ------------------------------------------------------------------------------------

def overlay_spans(inp):
    """overlay -> (first VU instruction address, instruction pairs) from the residency offsets."""
    return {n: (inp['residency_offsets'][n] // 8, len(inp['overlays'][n]['bin']) // 8) for n in OVERLAYS}


def derive_jump_table(inp):
    ov0 = inp['overlays'][0]
    regs, memory, written_pairs = {0: 0}, {}, []
    for pair in range(15):
        need(pair_words(ov0['bin'], pair)[1] == VU_NOP_UPPER, 'overlay 0 pair %d: upper instruction is not a nop' % pair)
        word, _ = bound_lower(inp, 0, pair)
        if word >> 25 == 8:
            regs[(word >> 16) & 31] = regs.get((word >> 11) & 31, 0) + (((word >> 21) & 15) << 11 | (word & 0x7FF))
        elif word >> 25 == 5:
            need((word >> 21) & 15 == 1, 'overlay 0 pair %d: ISW does not write the w lane only' % pair)
            memory[regs[(word >> 11) & 31] + (word & 0x7FF)] = regs[(word >> 16) & 31]
            written_pairs.append(pair)
        else:
            raise DispatchError('overlay 0 pair %d: unexpected lower instruction' % pair)
    base = 0x14
    need(sorted(memory) == list(range(base, base + 7)), 'jump table does not occupy seven consecutive words at 0x14')
    entries = []
    spans = overlay_spans(inp)
    ordered = sorted(spans.values())
    need(all(a[0] + a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlay residency windows overlap')
    for index in range(7):
        target = memory[base + index]
        hits = [n for n, (b, size) in spans.items() if b <= target < b + size]
        need(len(hits) == 1, 'table entry %d (0x%x) does not land in exactly one resident overlay' % (index, target))
        n = hits[0]
        local = target - spans[n][0]
        lo, up = pair_words(inp['overlays'][n]['bin'], local)
        entries.append({'index': index, 'target_address': target, 'overlay': n, 'local_pair': local,
                        'target_lower_word': '0x%08x' % lo, 'target_upper_word': '0x%08x' % up,
                        'target_text': inp['overlays'][n]['asm'][local]})
    stop = entries[0]
    need(int(stop['target_upper_word'], 16) & (1 << 30) and int(stop['target_lower_word'], 16) == VU_NOP_LOWER, 'table entry 0 is not an E-bit stop')
    return {'data_memory_base': base, 'written_by_overlay0_pairs': [0, written_pairs[-1]], 'entries': entries}


def derive_init_program(inp):
    ov0 = inp['overlays'][0]
    ends = [p for p in range(len(ov0['bin']) // 8) if pair_words(ov0['bin'], p)[1] & (1 << 30)]
    need(ends and ends[0] == 24, 'the first E-bit pair of overlay 0 is not pair 24')
    for p in range(24):
        need(asm_upper_ok(ov0, p), 'overlay 0 pair %d: upper disassembly disagrees with the E bit' % p)
    need(asm_upper_ok(ov0, 24) and ov0['asm'][24].startswith('nop[e]'), 'pair 24 is not disassembled as nop[e]')
    return {'first_pair': 0, 'last_pair_with_e_bit': 24, 'delay_slot_pair': 25, 'next_entry_address': 24 + 2}


def asm_upper_ok(ov, pair):
    upper = pair_words(ov['bin'], pair)[1]
    shown = ov['asm'][pair].split('\t', 1)[0].strip()
    return (shown.endswith('[e]')) == bool(upper & (1 << 30))


BRANCH_TOP7 = {0x20, 0x21, 0x24, 0x25, 0x28, 0x29, 0x2C, 0x2D, 0x2E, 0x2F}  # B BAL JR JALR IBEQ IBNE IBLTZ IBGTZ IBLEZ IBGEZ


def rx(pattern, text):
    m = re.fullmatch(pattern, text)
    need(m is not None, 'unexpected instruction text %r' % text)
    return m.groups()


def derive_dispatch(inp, init):
    entry = init['next_entry_address']
    expected = {'xtop': 60, 'ilwr_index_x': 61, 'table_base_iaddiu': 64, 'iadd_index': 65, 'ilwr_handler_w': 66, 'jr': 73}
    binary = inp['overlays'][0]['bin']
    _, text = bound_lower(inp, 0, entry)
    need(text == 'xtop vi01', 'MSCAL entry 0x%x is not an xtop' % entry)
    # raw scan: exactly two xtop pairs and no branch or jump before the jr that ends the dispatch
    tops = [p for p in range(entry, expected['jr'] + 1) if pair_words(binary, p)[0] >> 25 == 0x40 and pair_words(binary, p)[0] & 0x7FF == 0x6BC]
    need(tops == [entry, expected['xtop']], 'expected a matrix prologue then a second xtop at pair %d, found %r' % (expected['xtop'], tops))
    control = [p for p in range(entry, expected['jr'] + 1) if pair_words(binary, p)[0] >> 25 in BRANCH_TOP7]
    need(control == [expected['jr']], 'branches or jumps found between the entry and the jr: %r' % control)
    # symbolic dataflow over the second xtop .. jr
    value, seen = {}, {}
    for p in range(expected['xtop'], expected['jr'] + 1):
        _, t = bound_lower(inp, 0, p)
        seen[p] = t
        if t.startswith('xtop'):
            value[int(rx(r'xtop vi(\d+)', t)[0])] = 'TOP'
        elif t.startswith('ilwr.'):
            lane, dest, base, _lane = rx(r'ilwr\.(\w) vi(\d+),\(vi(\d+)\)(\w)', t)
            value[int(dest)] = 'DM[%s].%s' % (value.get(int(base), '?'), lane)
        elif t.startswith('iaddiu'):
            dest, src, imm = (int(x) for x in rx(r'iaddiu vi(\d+),vi(\d+),(\d+)', t))
            value[dest] = '%d' % imm if src == 0 else '(%s+%d)' % (value.get(src, '?'), imm)
        elif t.startswith('iadd '):
            dest, src, other = (int(x) for x in rx(r'iadd vi(\d+),vi(\d+),vi(\d+)', t))
            value[dest] = '(%s+%s)' % (value.get(src, '?'), value.get(other, '?'))
        elif t.startswith('jr '):
            handler = value.get(int(rx(r'jr vi(\d+)', t)[0]))
    need(handler == 'DM[(20+DM[TOP].x)].w', 'jr target is not the table lookup DM[0x14 + DM[TOP].x].w: %r' % handler)
    return {'entry_address': entry, 'overlay': 0, 'prologue_pairs': [entry, expected['xtop'] - 1], 'dispatch_pairs': expected,
            'index_lane': {'qword_offset_from_top': 0, 'lane': 'x'}, 'handler_expression': 'DM[0x14 + DM[TOP+0].x].w',
            'lower_text_by_pair': {str(p): seen[p] for p in seen}}


def derive_mscal(inp, init):
    for entry in NEEDED_FUNCTIONS:
        bind_function(inp, entry)
    # FUN_0022fda8: (label - base) >> 3 into gp-relative globals
    regs = {'zero': 0}
    stores = {}
    for ins in inp['functions']['0022fda8']['instructions']:
        t = ins['text'].lstrip('_')
        m = re.match(r'(\w+) (.*)', t)
        op, args = m.group(1), m.group(2).split(',')
        if op == 'lui':
            regs[args[0]] = int(args[1], 16) << 16
        elif op == 'addiu':
            regs[args[0]] = regs[args[1]] + int(args[2], 16)
        elif op == 'subu':
            regs[args[0]] = regs[args[1]] - regs[args[2]]
        elif op == 'srl':
            regs[args[0]] = regs[args[1]] >> int(args[2], 16)
        elif op == 'sw':
            off, base = re.match(r'(-?0x[0-9a-f]+)\((\w+)\)', args[1]).groups()
            need(base == 'gp', 'FUN_0022fda8 stores through a non-gp base')
            stores[int(off, 16)] = regs[args[0]]
        elif op == 'jr':
            pass
        else:
            raise DispatchError('FUN_0022fda8 contains an unexpected instruction: ' + t)
    need(stores == {-0x6DF4: 0, -0x6DF0: 0x1A, -0x6DEC: 0x5CC, -0x6DE8: 0, -0x6DE4: 0}, 'FUN_0022fda8 stores unexpected values: %r' % stores)
    need(init['next_entry_address'] == stores[-0x6DF0], 'MSCAL entry stored by FUN_0022fda8 is not the instruction after the init program')
    # emitters: lw of the global, then an or with a register last loaded with 0x14000000 (linear scan, not path-sensitive)
    emitters = {k: [] for k in GP_NAMES}
    for entry, f in inp['functions'].items():
        held, ins_list = {}, f['instructions']
        for idx, ins in enumerate(ins_list):
            t = ins['text'].lstrip('_')
            note_write(held, t, lui=True)
            m = re.fullmatch(r'lw (\w+),(-0x[0-9a-f]+)\(gp\)', t)
            if m and int(m.group(2), 16) in GP_NAMES:
                probe = dict(held)
                for later in ins_list[idx + 1:idx + 8]:
                    lt = later['text'].lstrip('_')
                    o = re.fullmatch(r'or %s,%s,(\w+)' % (m.group(1), m.group(1)), lt)
                    note_write(probe, lt, lui=True)
                    if o and probe.get(o.group(1)):
                        if entry not in emitters[int(m.group(2), 16)]:
                            emitters[int(m.group(2), 16)].append(entry)
                        break
    need({k: v for k, v in emitters.items()} == {-0x6DF4: ['001124c0'], -0x6DF0: ['0021c3e0'], -0x6DEC: ['00128ca0']}, 'unexpected MSCAL emitters: %r' % emitters)
    spans = overlay_spans(inp)
    out = []
    for off, name in GP_NAMES.items():
        value = stores[off]
        hits = [n for n, (b, size) in spans.items() if b <= value < b + size]
        need(len(hits) == 1, 'MSCAL value 0x%x is not in exactly one overlay' % value)
        out.append({'name': name, 'global': 'gp%s' % signed_hex(off), 'value': value, 'emitters': emitters[off], 'overlay': hits[0], 'local_pair': value - spans[hits[0]][0]})
    return out


def last_writer(ins_list, call_index, reg):
    """Text of the last instruction before the callee reads `reg`: the delay slot first, then backwards."""
    for j in [call_index + 1] + list(range(call_index - 1, max(call_index - 16, -1), -1)):
        t = ins_list[j]['text'].lstrip('_')
        m = re.match(r'(\w+) (\w+)', t)
        if m and m.group(1) in DEST_FIRST and m.group(2) == reg:
            return t
    return None


def writes_between(ins_list, reg, first, last):
    out = []
    for ins in ins_list:
        if first <= ins['address'] <= last:
            m = re.match(r'(\w+) (\w+)', ins['text'].lstrip('_'))
            if m and m.group(1) in DEST_FIRST and m.group(2) == reg:
                out.append(ins['address'])
    return out


def derive_pass_header(inp, table):
    fn, ins_list = '0021bb48', inp['functions']['0021bb48']['instructions']
    need(text_at(inp, fn, '0021bb70') == 'lw v1,0x0(a0)', 'block pointer is not loaded from the first argument')
    need(text_at(inp, fn, '0021bb80') == 'sw t3,0x0(v1)' and text_at(inp, fn, '0021bb84') == 'addiu v1,v1,0x4', 'unpack code is not word 0 of the block')
    need(not writes_between(ins_list, 'v1', '0021bb88', '0021bbc4'), 'v1 is rewritten between the pointer advance and the lane stores')
    lanes = {}
    for address, reg, off in [('0021bba8', 'a1', 0), ('0021bbac', 'a3', 8), ('0021bbbc', 'a2', 4), ('0021bbc4', 't0', 12)]:
        need(text_at(inp, fn, address) == 'sw %s,0x%x(v1)' % (reg, off), '0021bb48 store at %s changed' % address)
        lanes['xyzw'[off // 4]] = 'param_%d' % {'a1': 2, 'a2': 3, 'a3': 4, 't0': 5}[reg]
    need(not writes_between(ins_list, 'a1', '0021bb48', '0021bba8'), 'a1 is rewritten before the pass-word store')
    constants = [text_at(inp, fn, a) for a in ('0021bb54', '0021bb5c', '0021bb6c', '0021bb64', '0021bb74')]
    need(constants == ['lui v1,0x3', 'ori v1,v1,0x8000', 'lui v0,0x6c00', 'or t3,t3,v1', 'or t3,t3,v0'], '0021bb48 unpack code construction changed')
    code = (0x3 << 16) | 0x8000 | (0x6C00 << 16)
    unpack = {'format': 'V4-32' if (code >> 24) & 0xF == 0xC else '?', 'num': (code >> 16) & 0xFF, 'tops_relative': bool(code & 0x8000), 'address_field': code & 0x3FF}
    need(unpack == {'format': 'V4-32', 'num': 3, 'tops_relative': True, 'address_field': 0}, 'unexpected unpack code')
    # every call site: the eighth argument is zeroed by an instruction; pass words come from the pseudocode
    sites, eighth = 0, []
    for entry in ('0021cc88', '0021ced0', '0021c3e0'):
        lst = inp['functions'][entry]['instructions']
        for k, ins in enumerate(lst):
            if ins['text'].lstrip('_') == 'jal 0x0021bb48':
                sites += 1
                eighth.append(last_writer(lst, k, 't3'))
    need(all(t == 'move t3,zero' for t in eighth), 'a FUN_0021bb48 call site does not zero its eighth argument: %r' % eighth)
    passes = []
    for entry in DECOMPILED_CALLERS:
        text = inp['decompiled'][entry]['text']
        for m in re.finditer(r'FUN_0021bb48\(([^;]*?)\);', text, re.S):
            args = [a.strip() for a in m.group(1).replace('\n', ' ').split(',')]
            need(len(args) in (6, 8), 'unexpected FUN_0021bb48 call shape')
            if re.fullmatch(r'\d+|0x[0-9a-f]+', args[1]):
                passes.append(int(args[1], 0))
            else:
                before = text[:m.start()]
                label = before.rfind('LAB_0021c67c:')
                need(label >= 0 and entry == '0021c3e0', 'cannot resolve a variable pass word in %s' % entry)
                values = [int(v) for v in re.findall(r'\b%s = (\d+);' % re.escape(args[1]), before[label:])]
                need(values, 'variable pass word %s has no literal assignment' % args[1])
                passes.extend(values)
    call_count = sum(len(re.findall(r'FUN_0021bb48\(', inp['decompiled'][e]['text'])) for e in DECOMPILED_CALLERS)
    all_sites = sum(len(v) for v in inp['jal_sites'].values())
    need(call_count == sites == all_sites == 6, 'FUN_0021bb48 call-site counts differ: pseudocode %d, scanned callers %d, whole export %d' % (call_count, sites, all_sites))
    static = sorted(set(passes))
    indices = [e['index'] for e in table['entries'] if e['index'] != 0]
    outside = [p for p in static if p not in indices]
    need(not outside, 'pass words outside the jump table: %r' % outside)
    return {'unpack_code_without_param8': code, 'unpack_decoded': unpack, 'payload_qword0_lanes': lanes, 'eighth_argument_at_call_sites': 'move t3,zero',
            'static_pass_words': static, 'table_indices_without_stop': indices, 'pass_words_outside_table': outside, 'table_index_0_is_stop': True,
            'call_sites': sites, 'pseudocode_sha256': {e: inp['decompiled'][e]['sha256'] for e in DECOMPILED_CALLERS}}


def reach(callees, start):
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        for c in callees.get(x, []):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen


def shortest(callees, src, dst):
    prev, frontier, count = {src: None}, [src], {src: 1}
    while frontier and dst not in prev:
        nxt = []
        for x in frontier:
            for c in sorted(callees.get(x, [])):
                if c not in prev:
                    prev[c] = x
                    count[c] = 0
                    nxt.append(c)
                if prev.get(c) is not None and c in nxt:
                    count[c] += count[x]
        frontier = nxt
    need(dst in prev, 'no path %s -> %s' % (src, dst))
    path, x = [], dst
    while x:
        path.append(x)
        x = prev[x]
    return path[::-1], count[dst]


def derive_call_graph(inp):
    callees, callers = inp['callees'], inp['callers']
    inverse = {}
    for a, outs in callees.items():
        for b in outs:
            inverse.setdefault(b, set()).add(a)
    need(all(set(callers[b]) == inverse.get(b, set()) for b in callers), 'callers and callees lists are not inverses')
    targets = ['00128e88', '0021ba50']
    ancestors = {}
    for t in targets:
        stack, seen = [t], {t}
        while stack:
            x = stack.pop()
            for c in callers[x]:
                if c not in seen:
                    seen.add(c)
                    stack.append(c)
        ancestors[t] = seen
    common = ancestors[targets[0]] & ancestors[targets[1]]
    lowest = sorted(c for c in common if not (reach(callees, c) & (common - {c})))
    need(len(lowest) == 1, 'the two packet emitters do not have exactly one lowest common ancestor: %r' % lowest)
    chain = '0021ba50' in reach(callees, '00128e88') or '00128e88' in reach(callees, '0021ba50')
    paths, counts = {}, {}
    for t in targets:
        paths[t], counts[t] = shortest(callees, lowest[0], t)
    return {'direct_callers': {t: sorted(callers[t]) for t in targets}, 'common_ancestor_count': len(common),
            'lowest_common_ancestors': lowest, 'direct_chain_either_way': chain, 'paths': paths, 'shortest_path_counts': counts,
            'edge_scope': 'direct JAL edges of the typed export; indirect calls are not represented'}


def derive(inp):
    table = derive_jump_table(inp)
    init = derive_init_program(inp)
    dispatch = derive_dispatch(inp, init)
    mscal = derive_mscal(inp, init)
    header = derive_pass_header(inp, table)
    graph = derive_call_graph(inp)
    if inp['snapshot'] is not None:
        for n in OVERLAYS:
            found = [o for o in range(0, len(inp['snapshot']) - len(inp['overlays'][n]['bin']) + 1, 8)
                     if inp['snapshot'][o:o + len(inp['overlays'][n]['bin'])] == inp['overlays'][n]['bin']]
            need(found == [inp['residency_offsets'][n]], 'overlay %d window in the micro-memory snapshot is %r, receipt says 0x%x' % (n, found, inp['residency_offsets'][n]))
    return {
        'schema': 'fr2-vu-dispatch-map/v1',
        'scope': 'Static map from VIF MSCAL entries and the retained packet header to the VU1 overlay-0 jump table; no code was executed.',
        'render_fidelity_complete': False,
        'pins': {'inventory_sha256': inp['inventory_sha256'], 'elf_sha256': inp['elf_sha256'], 'residency_receipt_sha256': inp['residency_receipt_sha256'],
                 'overlays': {str(n): {'bin_sha256': inp['overlays'][n]['bin_sha256'], 'asm_sha256': inp['overlays'][n]['asm_sha256'],
                                       'micro_memory_offset': inp['residency_offsets'][n]} for n in OVERLAYS}},
        'jump_table': table,
        'init_program': init,
        'dispatch_at_entry_0x1a': dispatch,
        'mscal_entries': mscal,
        'pass_word_header': header,
        'call_graph': graph,
        'claim_limits': [
            'Static derivation only; no VU1 or EE code was executed and no emulator ran. Residency of the overlays in captured micro memory is not execution.',
            'The pass-word-to-jump-table relationship assumes the UNPACK of the 0021bb48 block is TOPS-relative at address 0 and that VIF MODE/CYCLE write its words unchanged; the live VIF state was not captured.',
            'Handler identity for any captured GIF tag is not proven. Entry 0x1a is also continued by MSCNT; whether other paths re-enter the table was not traced.',
            'Dispatch-sequence mnemonics are decoded from the overlay bytes for the subset used here and bound to the pinned disassembly text; other pairs are not decoded.',
            'Call edges are direct JAL edges of the typed export; typed pseudocode supplies the FUN_0021bb48 argument values and is not an execution trace.',
        ],
    }


def make_controls():
    return [
        ('table value bumped', lambda i: mutate_overlay_lower(i, 0, 3, 1)),
        ('table base moved', lambda i: mutate_overlay_lower(i, 0, 0, 1)),
        ('init program E bit cleared', lambda i: mutate_overlay_upper(i, 0, 24, VU_NOP_UPPER)),
        ('jr register changed', lambda i: mutate_overlay_lower(i, 0, 73, 0x800)),
        ('overlay 1 residency offset shifted', lambda i: mutate_residency(i, 1, 0x1000)),
        ('overlay 1 and 2 residency offsets swapped', lambda i: swap_residency(i, 1, 2)),
        ('call edge removed from one list', lambda i: mutate_call_edge(i, '001cf848', '001ce288')),
        ('call edge removed from both lists', lambda i: mutate_call_edge(i, '001cf848', '001ce288', both=True)),
        ('table entry 0 stop bit cleared', lambda i: mutate_overlay_upper(i, 2, 254, VU_NOP_UPPER)),
        ('disassembly text of a table pair changed', lambda i: mutate_asm(i, 0, 2, 'nop \tiaddiu vi03,vi00,0x4e')),
        ('EE instruction word differs from the ELF', lambda i: mutate_ee_bytes(i, '0021bb48', '0021bba8', '00000000')),
        ('MSCAL source literal changed', lambda i: mutate_ee_instruction(i, '0022fda8', '0022fdc0', 'addiu v0,v0,0xd8')),
        ('pass-word store moved to another lane', lambda i: mutate_ee_instruction(i, '0021bb48', '0021bba8', 'sw a1,0x4(v1)')),
        ('a pass word leaves the table', lambda i: mutate_decompilation(i, '0021ced0', 'FUN_0021bb48(piVar4,6,', 'FUN_0021bb48(piVar4,7,')),
    ]


CONTROLS = make_controls()


def run_controls(inp):
    """Each mutated copy of the inputs must make the derivation raise; a mutation that derives cleanly escaped."""
    results = []
    for label, mutate in CONTROLS:
        mutated = clone_inputs(inp)
        mutate(mutated)
        try:
            derive(mutated)
        except DispatchError as e:
            results.append({'mutation': label, 'rejected': True, 'reason': str(e)})
        else:
            raise AssertionError('mutation escaped: ' + label)
    return results


def main(argv):
    inp = load_inputs()
    receipt = derive(inp)
    receipt['controls'] = run_controls(inp)
    text = json.dumps(receipt, indent=1) + '\n'
    if '--write' in argv:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(text)
    elif not RECEIPT.exists() or RECEIPT.read_text() != text:
        print('RECEIPT MISMATCH: %s does not reproduce from the pinned sources (re-run with --write only after reading the diff)' % RECEIPT.relative_to(ROOT))
        return 1
    print(json.dumps({'jump_table': [e['target_address'] for e in receipt['jump_table']['entries']], 'mscal': {e['name']: e['value'] for e in receipt['mscal_entries']},
                      'static_pass_words': receipt['pass_word_header']['static_pass_words'], 'lowest_common_ancestors': receipt['call_graph']['lowest_common_ancestors'],
                      'controls_rejected': sum(c['rejected'] for c in receipt['controls']), 'controls': len(receipt['controls'])}))
    print('VERIFY OK')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
