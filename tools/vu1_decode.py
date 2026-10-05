#!/usr/bin/env python3
"""Decode VU1 microcode pairs from raw bytes, written from the VU instruction-set layout.

A pair is 64 bits: the lower instruction is the low 32-bit word, the upper instruction the high word
(little-endian in a binary). The decoder covers the instruction forms that occur in the Ford Racing 2
overlays; any other word decodes to an op named '?'. `render` prints the same style as the pinned
disassembly so a decoder result can be checked against it pair by pair (tools/test_vu1_decode.py).
Nothing here executes microcode.
"""
import struct

LANE_BITS = ((24, 'x'), (23, 'y'), (22, 'z'), (21, 'w'))
BC = 'xyzw'
UPPER_NOP = 0x000002FF
LOWER_NOP = 0x8000033C

# upper opcodes 0x00-0x2f; the bc forms carry the broadcast lane in the low two bits
UPPER_BC = {0x00: 'add', 0x04: 'sub', 0x08: 'madd', 0x0C: 'msub', 0x10: 'max', 0x14: 'mini', 0x18: 'mul'}
UPPER_FIXED = {0x1C: 'mulq', 0x1D: 'maxi', 0x1E: 'muli', 0x1F: 'minii', 0x20: 'addq', 0x21: 'maddq', 0x22: 'addi', 0x23: 'maddi',
               0x24: 'subq', 0x25: 'msubq', 0x26: 'subi', 0x27: 'msubi', 0x28: 'add', 0x29: 'madd', 0x2A: 'mul', 0x2B: 'max',
               0x2C: 'sub', 0x2D: 'msub', 0x2E: 'opmsub', 0x2F: 'mini'}
# upper opcodes 0x3c-0x3f select the instruction with bits 10-6; the low two bits of the opcode are the broadcast lane
UPPER_ACC = {0: 'adda', 1: 'suba', 2: 'madda', 3: 'msuba', 6: 'mula'}
UPPER_SPECIAL_CONV = {(0x3C, 4): ('itof0', 'conv'), (0x3D, 4): ('itof4', 'conv'), (0x3C, 5): ('ftoi0', 'conv'), (0x3D, 5): ('ftoi4', 'conv'),
                      (0x3D, 7): ('abs', 'conv'), (0x3F, 7): ('clipw', 'clipw'), (0x3E, 11): ('opmula', 'opmula'), (0x3F, 11): ('nop', 'nop')}

LOWER_TOP7 = {0x00: 'lq', 0x01: 'sq', 0x04: 'ilw', 0x05: 'isw', 0x08: 'iaddiu', 0x09: 'isubiu', 0x12: 'fcand', 0x13: 'fcor', 0x1A: 'fmand',
              0x1C: 'fcget', 0x20: 'b', 0x21: 'bal', 0x24: 'jr', 0x28: 'ibeq', 0x29: 'ibne', 0x2C: 'ibltz', 0x2D: 'ibgtz'}
LOWER_OP6 = {0x30: 'iadd', 0x31: 'isub', 0x32: 'iaddi', 0x34: 'iand', 0x35: 'ior'}
LOWER_OP11 = {0x33C: 'move', 0x33D: 'mr32', 0x37C: 'lqi', 0x37D: 'sqi', 0x37F: 'sqd', 0x3BC: 'div', 0x3BF: 'waitq', 0x3FC: 'mtir',
              0x3FD: 'mfir', 0x3FE: 'ilwr', 0x3FF: 'iswr', 0x67C: 'mfp', 0x6BC: 'xtop', 0x6FC: 'xgkick', 0x73F: 'erleng', 0x7BE: 'ercpr',
              0x7BF: 'waitp'}


def dest_lanes(word):
    return ''.join(c for bit, c in LANE_BITS if word >> bit & 1)


def sign(value, bits):
    return value - (1 << bits) if value >= 1 << (bits - 1) else value


def decode_upper(word):
    """Fields of an upper instruction: flags, op, dest lanes and register numbers."""
    f = {'word': word, 'i': word >> 31 & 1, 'e': word >> 30 & 1, 'm': word >> 29 & 1, 'd': word >> 28 & 1, 't': word >> 27 & 1,
         'dest': dest_lanes(word), 'ft': word >> 16 & 31, 'fs': word >> 11 & 31, 'fd': word >> 6 & 31}
    op6, ext = word & 63, word >> 6 & 31
    if op6 < 0x1C:
        f.update(op=UPPER_BC[op6 & ~3] + BC[op6 & 3], form='bc', bc=BC[op6 & 3])
    elif op6 < 0x30:
        name = UPPER_FIXED[op6]
        f.update(op=name, form='vec' if op6 >= 0x28 else 'q' if name.endswith('q') else 'i')
        if name == 'opmsub':
            f['form'] = 'vec'
    elif op6 >= 0x3C and ext in UPPER_ACC:
        f.update(op=UPPER_ACC[ext] + BC[op6 & 3], form='acc_bc', bc=BC[op6 & 3])
    elif (op6, ext) in UPPER_SPECIAL_CONV:
        name, form = UPPER_SPECIAL_CONV[(op6, ext)]
        f.update(op=name, form=form)
    else:
        f.update(op='?', form='?')
    return f


def decode_lower(word, immediate=False):
    """Fields of a lower instruction. With the upper I bit set the lower word is a float literal (loi)."""
    if immediate:
        return {'word': word, 'op': 'loi', 'value': struct.unpack('<f', struct.pack('<I', word))[0]}
    f = {'word': word, 'dest': dest_lanes(word), 'it': word >> 16 & 31, 'is': word >> 11 & 31, 'id': word >> 6 & 31,
         'fsf': 'xyzw'[word >> 21 & 3], 'ftf': 'xyzw'[word >> 23 & 3], 'imm11': sign(word & 0x7FF, 11)}
    if word == LOWER_NOP:
        f['op'] = 'nop'
    elif not word >> 31:
        top7 = word >> 25
        op = LOWER_TOP7.get(top7)
        f['op'] = op or '?'
        if op in ('iaddiu', 'isubiu'):
            f['imm15'] = (word >> 21 & 15) << 11 | word & 0x7FF
        if op in ('fcand', 'fcor'):
            f['imm24'] = word & 0xFFFFFF
    else:
        op = LOWER_OP11.get(word & 0x7FF) or LOWER_OP6.get(word & 63)
        f['op'] = op or '?'
        if op == 'iaddi':
            f['imm5'] = sign(word >> 6 & 31, 5)
    return f


def decode_pair(lower, upper):
    u = decode_upper(upper)
    lo = decode_lower(lower, immediate=bool(u['i']))
    return u, lo


def vf(n, lanes):
    return 'vf%02d%s' % (n, lanes)


def vi(n):
    return 'vi%02d' % n


def render_upper(u):
    flag = ('[i]' if u['i'] else '') + ('[e]' if u['e'] else '') + ('[m]' if u['m'] else '') + ('[d]' if u['d'] else '') + ('[t]' if u['t'] else '')
    op, d, form = u['op'], u['dest'], u['form']
    if op == '?':
        return '?0x%08x' % u['word']
    if form == 'nop':
        return 'nop' + flag
    head = '%s%s.%s' % (op, flag, d)
    if form == 'bc':
        return '%s %s,%s,%s' % (head, vf(u['fd'], d), vf(u['fs'], d), vf(u['ft'], u['bc']))
    if form == 'q':
        return '%s %s,%s,q' % (head, vf(u['fd'], d), vf(u['fs'], d))
    if form == 'i':
        return '%s %s,%s,i' % (head, vf(u['fd'], d), vf(u['fs'], d))
    if form == 'vec':
        return '%s %s,%s,%s' % (head, vf(u['fd'], d), vf(u['fs'], d), vf(u['ft'], d))
    if form == 'acc_bc':
        return '%s acc%s,%s,%s' % (head, d, vf(u['fs'], d), vf(u['ft'], u['bc']))
    if form == 'conv':
        return '%s %s,%s' % (head, vf(u['ft'], d), vf(u['fs'], d))
    if form == 'clipw':
        return '%s %s,%s' % (head, vf(u['fs'], d), vf(u['ft'], 'w'))
    if form == 'opmula':
        return '%s acc%s,%s,%s' % (head, d, vf(u['fs'], d), vf(u['ft'], d))
    return '?0x%08x' % u['word']


def render_lower(f):
    op, d = f['op'], f.get('dest', '')
    if op == 'loi':
        return 'loi %.9g' % f['value']
    if op == '?':
        return '?0x%08x' % f['word']
    if op == 'nop':
        return 'nop'
    it, is_, id_ = f['it'], f['is'], f['id']
    if op == 'lq':
        return 'lq.%s %s,%d(%s)' % (d, vf(it, d), f['imm11'], vi(is_))
    if op == 'sq':
        return 'sq.%s %s,%d(%s)' % (d, vf(is_, d), f['imm11'], vi(it))
    if op in ('ilw', 'isw'):
        return '%s.%s %s,%d(%s)%s' % (op, d, vi(it), f['imm11'], vi(is_), d)
    if op in ('iaddiu', 'isubiu'):
        return '%s %s,%s,%d' % (op, vi(it), vi(is_), f['imm15'])
    if op in ('fcand', 'fcor'):
        return '%s vi01,0x%x' % (op, f['imm24'])
    if op == 'fmand':
        return 'fmand %s,%s' % (vi(it), vi(is_))
    if op == 'fcget':
        return 'fcget %s' % vi(it)
    if op == 'b':
        return 'b %d' % f['imm11']
    if op == 'bal':
        return 'bal %s,%d' % (vi(it), f['imm11'])
    if op == 'jr':
        return 'jr %s' % vi(is_)
    if op in ('ibeq', 'ibne'):
        return '%s %s,%s,%d' % (op, vi(it), vi(is_), f['imm11'])
    if op in ('ibltz', 'ibgtz'):
        return '%s %s,%d' % (op, vi(is_), f['imm11'])
    if op in ('iadd', 'isub', 'iand', 'ior'):
        return '%s %s,%s,%s' % (op, vi(id_), vi(is_), vi(it))
    if op == 'iaddi':
        return 'iaddi %s,%s,%d' % (vi(it), vi(is_), f['imm5'])
    if op in ('move', 'mr32'):
        return '%s.%s %s,%s' % (op, d, vf(it, d), vf(is_, d))
    if op == 'lqi':
        return 'lqi.%s %s,(%s++)' % (d, vf(it, d), vi(is_))
    if op == 'sqi':
        return 'sqi.%s %s,(%s++)' % (d, vf(is_, d), vi(it))
    if op == 'sqd':
        return 'sqd.%s %s,(--%s)' % (d, vf(is_, d), vi(it))
    if op == 'div':
        return 'div q,%s,%s' % (vf(is_, f['fsf']), vf(it, f['ftf']))
    if op == 'waitq':
        return 'waitq'
    if op == 'waitp':
        return 'waitp'
    if op == 'mtir':
        return 'mtir %s,%s' % (vi(it), vf(is_, f['fsf']))
    if op == 'mfir':
        return 'mfir.%s %s,%s' % (d, vf(it, d), vi(is_))
    if op == 'ilwr':
        return 'ilwr.%s %s,(%s)%s' % (d, vi(it), vi(is_), d)
    if op == 'iswr':
        return 'iswr.%s %s,(%s)%s' % (d, vi(it), vi(is_), d)
    if op == 'mfp':
        return 'mfp.%s %s,p' % (d, vf(it, d))
    if op == 'xtop':
        return 'xtop %s' % vi(it)
    if op == 'xgkick':
        return 'xgkick %s' % vi(is_)
    if op == 'erleng':
        return 'erleng p,vf%02d' % is_
    if op == 'ercpr':
        return 'ercpr p,%s' % vf(is_, f['fsf'])
    return '?0x%08x' % f['word']


def render_pair(lower, upper):
    u, lo = decode_pair(lower, upper)
    return '%s \t%s' % (render_upper(u), render_lower(lo))


def pairs(binary):
    return [struct.unpack_from('<II', binary, p * 8) for p in range(len(binary) // 8)]
