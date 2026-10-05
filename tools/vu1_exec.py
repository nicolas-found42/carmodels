#!/usr/bin/env python3
"""Straight-line VU1 executor over decoded pairs, with a symbolic and a numeric value domain.

The same executor runs both domains, so a symbolic result and its numeric evaluation cannot disagree about
what an instruction does. It runs straight-line segments only (it stops at a branch) and implements exactly
the instruction forms the car handlers use; any other form raises NotImplementedError. Pair semantics: the
upper and lower instruction of a pair both read the state before the pair and commit together. Latencies
are ignored (Q, P and FMAC results are available to the next pair), which holds for code that waits.
Nothing here executes the game or an emulator.
"""
import math
import struct

import vu1_decode as vd

LANES = 'xyzw'
F32_MAX = 3.4028234663852886e+38
F32_MIN_NORMAL = 1.1754943508222875e-38


def f32(x):
    """Host binary32 approximation with finite clamping and denormal flushing; not bit-exact VU rounding."""
    if x != x:
        return 0.0
    try:
        y = struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(F32_MAX, x)
    if math.isinf(y):
        return math.copysign(F32_MAX, y)
    return 0.0 if abs(y) < F32_MIN_NORMAL else y


def fmt(x):
    return '%.9g' % x


class E:
    """Immutable symbolic expression; `s` is its canonical text."""
    __slots__ = ('op', 'args', 's')

    def __init__(self, op, args, s):
        self.op, self.args, self.s = op, args, s

    def __repr__(self):
        return self.s


def text(v):
    return v.s if isinstance(v, E) else fmt(v)


def leaf(name):
    return E('sym', (name,), name)


class IV:
    """Integer register value: `base` plus `off`. base None means a plain integer."""
    __slots__ = ('base', 'off')

    def __init__(self, base, off=0):
        self.base, self.off = base, off

    def __repr__(self):
        if self.base is None:
            return str(self.off)
        return self.base + ('%+d' % self.off if self.off else '')

    def __eq__(self, other):
        return isinstance(other, IV) and (self.base, self.off) == (other.base, other.off)

    def __hash__(self):
        return hash((self.base, self.off))


class SymDomain:
    """Expression domain with light constant folding; floats are exact binary32 constants."""
    name = 'sym'

    def const(self, x):
        return f32(x)

    def neg(self, a):
        if not isinstance(a, E):
            return f32(-a)
        if a.op == 'neg':
            return a.args[0]
        return E('neg', (a,), '-' + (a.s if a.op in ('sym', 'fn', 'neg') else '(' + a.s + ')'))

    def add(self, a, b):
        if not isinstance(a, E) and not isinstance(b, E):
            return f32(a + b)
        if not isinstance(a, E) and a == 0:
            return b
        if not isinstance(b, E) and b == 0:
            return a
        return E('add', (a, b), '(%s + %s)' % (text(a), text(b)))

    def sub(self, a, b):
        if not isinstance(a, E) and not isinstance(b, E):
            return f32(a - b)
        if not isinstance(b, E) and b == 0:
            return a
        if not isinstance(a, E) and a == 0:
            return self.neg(b)
        return E('sub', (a, b), '(%s - %s)' % (text(a), text(b)))

    def mul(self, a, b):
        if not isinstance(a, E) and not isinstance(b, E):
            return f32(a * b)
        for x, y in ((a, b), (b, a)):
            if not isinstance(x, E):
                if x == 0:
                    return 0.0
                if x == 1:
                    return y
                if x == -1:
                    return self.neg(y)
        return E('mul', (a, b), '%s*%s' % (self._mulop(a), self._mulop(b)))

    @staticmethod
    def _mulop(v):
        if isinstance(v, E) and v.op in ('add', 'sub'):
            return v.s
        return text(v)

    def fn(self, name, *args):
        if all(not isinstance(a, E) for a in args):
            return NumDomain().fn(name, *args)
        return E('fn', (name,) + args, '%s(%s)' % (name, ', '.join(text(a) for a in args)))

    def mn(self, a, b):
        return self.fn('min', a, b)

    def mx(self, a, b):
        return self.fn('max', a, b)

    def ab(self, a):
        return self.fn('abs', a)

    def ftoi(self, a, shift):
        return self.fn('ftoi%d' % shift, a)

    def itof(self, a, shift):
        return self.fn('itof%d' % shift, a)

    def div(self, a, b):
        if not isinstance(a, E) and not isinstance(b, E):
            return NumDomain().div(a, b)
        return self.fn('div', a, b)

    def sym(self, name):
        return leaf(name)


class NumDomain:
    """Concrete domain: floats are binary32 values, ftoi results are Python ints."""
    name = 'num'

    def const(self, x):
        return f32(x)

    def neg(self, a):
        return -a if isinstance(a, int) else f32(-a)

    def add(self, a, b):
        return f32(a + b)

    def sub(self, a, b):
        return f32(a - b)

    def mul(self, a, b):
        return f32(a * b)

    def mn(self, a, b):
        return min(a, b)

    def mx(self, a, b):
        return max(a, b)

    def ab(self, a):
        return abs(a)

    def ftoi(self, a, shift):
        return max(-2 ** 31, min(2 ** 31 - 1, int(a * (1 << shift)) if abs(a * (1 << shift)) < 2 ** 62 else int(math.copysign(2 ** 31, a))))

    def itof(self, a, shift):
        return f32(a / (1 << shift))

    def div(self, a, b):
        if b == 0:
            return math.copysign(F32_MAX, a) if a else 0.0
        return f32(a / b)

    def fn(self, name, *args):
        if name == 'min':
            return self.mn(*args)
        if name == 'max':
            return self.mx(*args)
        if name == 'abs':
            return self.ab(*args)
        if name == 'div':
            return self.div(*args)
        if name.startswith('ftoi'):
            return self.ftoi(args[0], int(name[4:]))
        if name.startswith('itof'):
            return self.itof(args[0], int(name[4:]))
        raise NotImplementedError(name)

    def sym(self, name):
        raise KeyError(name)


def evaluate(expr, env):
    """Evaluate a symbolic expression numerically; env maps leaf names to floats."""
    num = NumDomain()
    if not isinstance(expr, E):
        return expr
    if expr.op == 'sym':
        return env[expr.args[0]]
    if expr.op == 'neg':
        return num.neg(evaluate(expr.args[0], env))
    if expr.op in ('add', 'sub', 'mul'):
        a, b = (evaluate(x, env) for x in expr.args)
        return getattr(num, expr.op)(a, b)
    if expr.op == 'fn':
        return num.fn(expr.args[0], *(evaluate(x, env) for x in expr.args[1:]))
    raise NotImplementedError(expr.op)


def leaves(expr, out=None):
    out = set() if out is None else out
    if isinstance(expr, E):
        if expr.op == 'sym':
            out.add(expr.args[0])
        else:
            for a in expr.args:
                if isinstance(a, (E, float, int)) and not isinstance(a, str):
                    leaves(a, out)
    return out


class Machine:
    """VU1 register state over a value domain; memory is keyed by (base, offset) qwords."""

    def __init__(self, dom, memory=None):
        self.dom = dom
        self.vf = [[0.0, 0.0, 0.0, 0.0] for _ in range(32)]
        self.vf[0] = [0.0, 0.0, 0.0, 1.0]
        self.vi = [IV(None, 0) for _ in range(16)]
        self.acc = [0.0] * 4
        self.q = 0.0
        self.p = 0.0
        self.i = 0.0
        self.mem = memory if memory is not None else {}
        self.reads = []
        self.stores = []
        self.kicks = []
        self.branches = []

    # --- memory ---------------------------------------------------------------------------------
    def address(self, reg, imm):
        v = self.vi[reg]
        return (v.base, v.off + imm)

    def read_qword(self, key):
        """Lanes of a qword; a lane that was never written reads as a leaf symbol (symbolic domain only)."""
        known = self.mem.get(key)
        if known is not None and None not in known:
            return known
        if self.dom.name != 'sym':
            raise KeyError(key)
        name = self._name(key)
        if known is None:
            self.reads.append(key)
        return [self.dom.sym('%s.%s' % (name, c)) if known is None or known[k] is None else known[k] for k, c in enumerate(LANES)]

    # --- one pair -------------------------------------------------------------------------------
    def step(self, lower, upper):
        u, lo = vd.decode_pair(lower, upper)
        vf_w, vi_w, other = [], [], []
        self._upper(u, vf_w, other)
        self._lower(lo, vf_w, vi_w, other)
        seen = set()
        for reg, lane, _ in vf_w:
            if (reg, lane) in seen and reg != 0:
                raise AssertionError('pair writes vf%d.%s twice' % (reg, lane))
            seen.add((reg, lane))
        for reg, lane, val in vf_w:
            if reg:
                self.vf[reg][lane] = val
        for reg, val in vi_w:
            if reg:
                self.vi[reg] = val
        for fn in other:
            fn()

    # --- upper ---------------------------------------------------------------------------------
    def _lanes(self, mask):
        return [LANES.index(c) for c in mask]

    def _ft_operand(self, u, lane_index):
        if u['form'] in ('bc', 'acc_bc'):
            return self.vf[u['ft']][LANES.index(u['bc'])]
        if u['form'] == 'q':
            return self.q
        if u['form'] == 'i':
            return self.i
        return self.vf[u['ft']][lane_index]

    def _upper(self, u, vf_w, other):
        d, op, form = self.dom, u['op'], u['form']
        if op == 'nop':
            return
        lanes = self._lanes(u['dest'])
        fs = self.vf[u['fs']]
        if form == 'conv':
            convert = {'ftoi0': lambda a: d.ftoi(a, 0), 'ftoi4': lambda a: d.ftoi(a, 4), 'itof0': lambda a: d.itof(a, 0),
                       'itof4': lambda a: d.itof(a, 4), 'abs': d.ab}[op]
            for k in lanes:
                vf_w.append((u['ft'], k, convert(fs[k])))
            return
        if form in ('clipw', 'opmula') or op == 'opmsub':
            raise NotImplementedError(op)
        base = op[:-1] if form in ('bc', 'acc_bc', 'q', 'i') else op
        arithmetic = {'add': d.add, 'adda': d.add, 'sub': d.sub, 'suba': d.sub, 'mul': d.mul, 'mula': d.mul, 'max': d.mx, 'mini': d.mn}
        results = {}
        for k in lanes:
            ft = self._ft_operand(u, k)
            if base in ('madd', 'madda'):
                results[k] = d.add(self.acc[k], d.mul(fs[k], ft))
            elif base in ('msub', 'msuba'):
                results[k] = d.sub(self.acc[k], d.mul(fs[k], ft))
            elif base in arithmetic:
                results[k] = arithmetic[base](fs[k], ft)
            else:
                raise NotImplementedError(op)
        if form == 'acc_bc':
            def commit(results=results):
                for k, r in results.items():
                    self.acc[k] = r
            other.append(commit)
        else:
            for k, r in results.items():
                vf_w.append((u['fd'], k, r))

    # --- lower ---------------------------------------------------------------------------------
    def _lower(self, f, vf_w, vi_w, other):
        op, d = f['op'], f.get('dest', '')
        it, is_, id_ = f.get('it'), f.get('is'), f.get('id')
        if op in ('nop', 'waitq', 'waitp'):
            return
        if op in ('b', 'bal', 'jr', 'ibeq', 'ibne', 'ibltz', 'ibgtz'):
            self.branches.append(op)  # straight-line executor: control flow is orchestrated by the caller
            return
        if op == 'loi':
            self.i = f32(f['value'])
            return
        lanes = self._lanes(d) if d else []
        if op == 'lq':
            qw = self.read_qword(self.address(is_, f['imm11']))
            for k in lanes:
                vf_w.append((it, k, qw[k]))
        elif op == 'lqi':
            key = self.address(is_, 0)
            qw = self.read_qword(key)
            for k in lanes:
                vf_w.append((it, k, qw[k]))
            vi_w.append((is_, IV(key[0], key[1] + 1)))
        elif op in ('sq', 'sqi', 'sqd'):
            if op == 'sq':
                key = self.address(it, f['imm11'])
                post = None
            elif op == 'sqi':
                key = self.address(it, 0)
                post = IV(key[0], key[1] + 1)
            else:
                v = self.vi[it]
                key = (v.base, v.off - 1)
                post = IV(key[0], key[1])
            snapshot = list(self.vf[is_])

            def store(key=key, d=d, snapshot=snapshot):
                old = self.mem.get(key)
                if old is None:
                    old = [None] * 4
                new = [snapshot[k] if LANES[k] in d else old[k] for k in range(4)]
                self.mem[key] = new
                self.stores.append((key, d, [snapshot[k] for k in range(4) if LANES[k] in d]))
            other.append(store)
            if post is not None:
                vi_w.append((it, post))
        elif op in ('move', 'mr32'):
            src = self.vf[is_]
            for k in lanes:
                vf_w.append((it, k, src[k] if op == 'move' else src[(k + 1) % 4]))
        elif op == 'mfir':
            for k in lanes:
                vf_w.append((it, k, self.dom.sym(repr(self.vi[is_]))))
        elif op == 'mfp':
            for k in lanes:
                vf_w.append((it, k, self.p))
        elif op == 'div':
            a, b = self.vf[is_]['xyzw'.index(f['fsf'])], self.vf[it]['xyzw'.index(f['ftf'])]
            q = self.dom.div(a, b)
            other.append(lambda q=q: setattr(self, 'q', q))
        elif op == 'ercpr':
            a = self.vf[is_]['xyzw'.index(f['fsf'])]
            p = self.dom.div(1.0, a)
            other.append(lambda p=p: setattr(self, 'p', p))
        elif op == 'xtop':
            vi_w.append((it, IV('TOP', 0)))
        elif op == 'xgkick':
            self.kicks.append(self.vi[is_])
        elif op in ('iaddiu', 'isubiu'):
            v = self.vi[is_]
            imm = f['imm15'] if op == 'iaddiu' else -f['imm15']
            vi_w.append((it, IV(v.base, v.off + imm)))
        elif op == 'iaddi':
            v = self.vi[is_]
            vi_w.append((it, IV(v.base, v.off + f['imm5'])))
        elif op in ('iadd', 'isub'):
            a, b = self.vi[is_], self.vi[it]
            sign = 1 if op == 'iadd' else -1
            if b.base is None:
                vi_w.append((id_, IV(a.base, a.off + sign * b.off)))
            elif a.base is None and op == 'iadd':
                vi_w.append((id_, IV(b.base, b.off + a.off)))
            else:
                vi_w.append((id_, IV('(%r %s %r)' % (a, '+' if sign > 0 else '-', b), 0)))
        elif op in ('iand', 'ior'):
            a, b = self.vi[is_], self.vi[it]
            if a.base is None and b.base is None:
                vi_w.append((id_, IV(None, a.off & b.off if op == 'iand' else a.off | b.off)))
            else:
                vi_w.append((id_, IV('(%r %s %r)' % (a, '&' if op == 'iand' else '|', b), 0)))
        elif op == 'ilw':
            key = self.address(is_, f['imm11'])
            vi_w.append((it, IV('%s.%s' % (self._name(key), d), 0)))
        elif op == 'ilwr':
            key = self.address(is_, 0)
            vi_w.append((it, IV('%s.%s' % (self._name(key), d), 0)))
        elif op in ('isw', 'iswr'):
            key = self.address(is_, f['imm11'] if op == 'isw' else 0)
            val, mask = self.vi[it], d

            def store_int(key=key, val=val, mask=mask):
                old = self.mem.get(key) or [None] * 4
                new = [val if LANES[k] in mask else old[k] for k in range(4)]
                self.mem[key] = new
                self.stores.append((key, mask, [val]))
            other.append(store_int)
        else:
            raise NotImplementedError(op)

    @staticmethod
    def _name(key):
        base, off = key
        return 'DM[%d]' % off if base is None else '%s[%d]' % (base, off)


def run_pairs(machine, pairs_list):
    for lo, up in pairs_list:
        machine.step(lo, up)


def ssa(roots, min_len=24):
    """Render expressions as shared bindings plus one line per root.

    Subtrees that occur more than once and print longer than `min_len` characters become named bindings
    (t1, t2, ...) in dependency order. Returns (bindings, rendered roots)."""
    counts = {}

    def count(e):
        if not isinstance(e, E) or e.op == 'sym':
            return
        counts[e.s] = counts.get(e.s, 0) + 1
        if counts[e.s] == 1:
            for a in e.args:
                count(a)
    for r in roots:
        count(r)
    names, bindings = {}, []

    def render(e, top=False):
        if not isinstance(e, E):
            return fmt(e)
        if e.op == 'sym':
            return e.s
        if e.s in names:
            return names[e.s]
        shared = counts.get(e.s, 0) > 1 and len(e.s) > min_len and not top
        body = rebuild(e)
        if shared:
            names[e.s] = 't%d' % (len(names) + 1)
            bindings.append((names[e.s], body))
            return names[e.s]
        return body

    def paren(e, text_):
        return text_ if (not isinstance(e, E)) or e.op in ('sym', 'fn', 'neg') or e.s in names else '(' + text_ + ')'

    def rebuild(e):
        if e.op == 'neg':
            return '-' + paren(e.args[0], render(e.args[0]))
        if e.op == 'fn':
            return '%s(%s)' % (e.args[0], ', '.join(render(a) for a in e.args[1:]))
        a, b = e.args
        sym = {'add': ' + ', 'sub': ' - ', 'mul': '*'}[e.op]
        left, right = render(a), render(b)
        if e.op == 'mul':
            left = paren(a, left) if isinstance(a, E) and a.op in ('add', 'sub') else left
            right = paren(b, right) if isinstance(b, E) and b.op in ('add', 'sub') else right
        else:
            left = left if not isinstance(a, E) or a.op in ('sym', 'fn', 'neg', 'mul') or a.s in names else '(' + left + ')'
            right = right if not isinstance(b, E) or b.op in ('sym', 'fn', 'neg', 'mul') or b.s in names else '(' + right + ')'
        return left + sym + right
    rendered = [render(r, top=True) for r in roots]
    return bindings, rendered
