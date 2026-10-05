#!/usr/bin/env python3
"""Static instruction-level float32 model for the VU0 routine at byte VMA 0x268.

This is an offline reference reconstruction, not a hardware or emulator run.
It follows the paired upper instructions from overlay-7.s, loads exact raw LOI
binary32 payloads, and rounds only arithmetic results toward zero. Caller test inputs are
converted once to binary32 to model QMTC2 payload transfer. Flags, latency, COP2
interlocks, FMAC scheduling, and the E-bit control transition are not modeled.
"""
from __future__ import annotations

import json
import math
import random
import struct


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def f32_bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


# Exact lower-word payloads from overlay 7, byte span beginning at file offset
# 1,162,480 in the pinned executable. LOI loads these bits directly; it is not
# an arithmetic result and must not pass through the model's RTZ operator.
LOI_BITS = {
    "pi_over_2": 0x3FC90FDB,
    "minus_inv_tau": 0xBE22F983,
    "magic_12582912": 0x4B400000,
    "half": 0x3F000000,
    "quarter": 0x3E800000,
    "coefficient_minus_76_5749588": 0xC2992661,
    "coefficient_minus_41_3416748": 0xC2255DE0,
    "coefficient_81_6022263": 0x42A33457,
    "coefficient_39_710659": 0x421ED7B7,
    "coefficient_6_28318501": 0x40C90FDA,
}


def load_i(name: str) -> float:
    return struct.unpack("<f", struct.pack("<I", LOI_BITS[name]))[0]


def vu_round0(x: float) -> float:
    """Binary32 conversion rounded toward zero, approximating VU's rule."""
    if not math.isfinite(x) or x == 0.0:
        return f32(x)
    nearest = f32(x)
    if (x > 0.0 and nearest > x) or (x < 0.0 and nearest < x):
        nearest = struct.unpack("<f", struct.pack("<I", f32_bits(nearest) - 1))[0]
    return nearest


def add(a: float, b: float) -> float:
    return vu_round0(float(a) + float(b))


def sub(a: float, b: float) -> float:
    return vu_round0(float(a) - float(b))


def mul(a: float, b: float) -> float:
    return vu_round0(float(a) * float(b))


def run(angle: float, initial_yzw=(0.0, 0.0, 0.0), rounding=vu_round0):
    """Execute the upper dataflow in pairs 77..101 for one scalar input.

    The qmtc2 caller supplies a full VF16 from an EE GPR; the model only fixes
    x to `angle`. Pair 77 overwrites y from x. x/y outputs are independent of
    initial z/w. `initial_yzw` is varied in the regression checks to verify that.
    The lower LOI word takes effect after the upper instruction in its pair.
    """
    op_add = lambda a, b: rounding(float(a) + float(b))
    op_sub = lambda a, b: rounding(float(a) - float(b))
    op_mul = lambda a, b: rounding(float(a) * float(b))
    vf00 = (0.0, 0.0, 0.0, 1.0)
    # QMTC2 moves the caller's binary32 GPR payload; round host test inputs
    # once to binary32, independently of the arithmetic rounding mode.
    vf16 = [f32(angle), *(f32(x) for x in initial_yzw)]
    vf17 = [0.0] * 4
    vf18 = [0.0] * 4
    vf19 = [0.0] * 4
    vf20 = [0.0] * 4
    vf21 = [0.0] * 4
    acc = [0.0] * 4
    I = 0.0

    # Pair 77: addx.y vf16y,vf00y,vf16x
    vf16[1] = op_add(vf00[1], vf16[0])
    # Pair 78: mulz[i].w vf16w,vf00w,vf16z ; loi pi/2
    vf16[3] = op_mul(vf00[3], vf16[2])
    I = load_i("pi_over_2")
    # Pair 79: subi.xz vf16xz,vf16xz,i
    vf16[0] = op_sub(vf16[0], I)
    vf16[2] = op_sub(vf16[2], I)
    # Pair 80 loads -1/(2*pi) after ABS (ABS has no I operand).
    vf16 = [rounding(abs(v)) for v in vf16]
    I = load_i("minus_inv_tau")
    # Pair 81: maxw vf17,vf00,vf00w => four lanes of 1.0.
    vf17 = [rounding(max(v, vf00[3])) for v in vf00]

    # Pairs 82-86: magic-constant ceil/fraction fold. Each lower LOI changes I
    # only after its pair's upper operation.
    acc = [op_mul(v, I) for v in vf16]                         # mulai
    I = load_i("magic_12582912")
    acc = [op_sub(a, op_mul(vf17[j], I)) for j, a in enumerate(acc)]  # msubai
    acc = [op_add(a, op_mul(vf17[j], I)) for j, a in enumerate(acc)]  # maddai
    I = load_i("minus_inv_tau")
    acc = [op_sub(a, op_mul(vf16[j], I)) for j, a in enumerate(acc)]  # msubai
    I = load_i("half")
    vf16 = [op_sub(acc[j], op_mul(vf17[j], I)) for j in range(4)]  # msubi
    vf16 = [rounding(abs(v)) for v in vf16]
    I = load_i("quarter")
    vf16 = [op_sub(v, I) for v in vf16]
    t = tuple(vf16)

    # Pairs 89-101: odd degree minimax-like sine polynomial in t.
    vf17 = [op_mul(v, v) for v in vf16]                         # t^2
    I = load_i("coefficient_minus_76_5749588")
    vf21 = [op_mul(v, I) for v in vf16]                        # -76.57 t
    I = load_i("coefficient_minus_41_3416748")
    vf19 = [op_mul(v, I) for v in vf16]                        # -41.34 t
    I = load_i("coefficient_81_6022263")
    vf20 = [op_mul(v, I) for v in vf16]                        # 81.60 t
    vf18 = [op_mul(v, v) for v in vf17]                         # t^4
    vf21 = [op_mul(a, b) for a, b in zip(vf21, vf17)]          # -76.57 t^3
    acc = [op_mul(a, b) for a, b in zip(vf19, vf17)]           # -41.34 t^3
    I = load_i("coefficient_39_710659")
    vf19 = [op_mul(v, I) for v in vf16]                        # 39.71 t
    vf17 = [op_mul(v, v) for v in vf18]                         # t^8
    acc = [op_add(a, op_mul(b, c)) for a, b, c in zip(acc, vf21, vf18)]
    acc = [op_add(a, op_mul(b, c)) for a, b, c in zip(acc, vf20, vf18)]
    I = load_i("coefficient_6_28318501")
    acc = [op_add(a, op_mul(v, I)) for a, v in zip(acc, vf16)]
    # Pair 100 has E set; pair 101 is the documented one-instruction delay
    # slot and writes the final 39.71*t^9 term to vf16.
    vf16 = [op_add(a, op_mul(b, c)) for a, b, c in zip(acc, vf19, vf17)]
    return tuple(vf16), t


def run_nearest(angle: float):
    return run(angle, rounding=f32)


def evaluate_suite():
    eps = 1.0e-3
    inputs = [
        -100.0, -10.0, -2.0 * math.pi, -math.pi, -math.pi / 2,
        -eps, 0.0, eps, math.pi / 6, math.pi / 4, math.pi / 2,
        math.pi, 3.0 * math.pi / 2, 2.0 * math.pi,
        3.0 * math.pi / 2 - eps, 3.0 * math.pi / 2 + eps,
        100.0, 1000.0, 1.0e6,
    ]
    rows = []
    for a in inputs:
        (sx, cy, sz, one), t = run(a)
        rows.append({
            "angle": a,
            "vx": sx,
            "vy": cy,
            "vz": sz,
            "vw": one,
            "sin_abs_error": abs(sx - math.sin(a)),
            "cos_abs_error": abs(cy - math.cos(a)),
            "folded_t_x": t[0],
            "folded_t_y": t[1],
        })

    # Sweep the main representative domain and a wider stress range.
    sweep = {}
    for name, lo, hi, count in [
        ("period_0_to_2pi", 0.0, 2.0 * math.pi, 20001),
        ("signed_small", -10.0, 10.0, 20001),
        ("wide_100", -100.0, 100.0, 20001),
    ]:
        max_s = (0.0, None)
        max_c = (0.0, None)
        for i in range(count):
            a = lo + (hi - lo) * i / (count - 1)
            (sx, cy, _, _), _ = run(a)
            es, ec = abs(sx - math.sin(a)), abs(cy - math.cos(a))
            if es > max_s[0]:
                max_s = (es, a)
            if ec > max_c[0]:
                max_c = (ec, a)
        sweep[name] = {"samples": count, "max_sin_error": max_s[0], "at_sin": max_s[1],
                       "max_cos_error": max_c[0], "at_cos": max_c[1]}

    # Negative control 1: ordinary round-to-nearest is wrong near the fold edge.
    a = 1.5 * math.pi + 1.0e-3
    (near_s, near_c, _, _), _ = run(a)
    (ieee_s, ieee_c, _, _), _ = run_nearest(a)
    nearest_control = {
        "angle": a,
        "vu_round0_sin_error": abs(near_s - math.sin(a)),
        "nearest_sin_error": abs(ieee_s - math.sin(a)),
    }

    # Negative control 2: x/y outputs must not depend on caller's other lanes.
    lane0 = run(0.7, (0.0, 0.0, 0.0))[0][:2]
    lane_random = run(0.7, (123.0, -77.0, 0.125))[0][:2]
    assert lane0 == lane_random

    # Range-reduction invariant on a deterministic randomized signed domain.
    rng = random.Random(0x268)
    random_range = {"seed": "0x268", "samples": 10000, "min_t": 1.0, "max_t": -1.0,
                    "max_sin_error": 0.0, "max_cos_error": 0.0}
    for _ in range(random_range["samples"]):
        a = rng.uniform(-100.0, 100.0)
        (sx, cy, _, _), t = run(a)
        assert all(-0.250001 <= x <= 0.250001 for x in t[:2])
        random_range["min_t"] = min(random_range["min_t"], *t[:2])
        random_range["max_t"] = max(random_range["max_t"], *t[:2])
        random_range["max_sin_error"] = max(random_range["max_sin_error"], abs(sx - math.sin(a)))
        random_range["max_cos_error"] = max(random_range["max_cos_error"], abs(cy - math.cos(a)))

    # Explicit values on and immediately around quarter-turn fold boundaries.
    boundary_rows = []
    for k in range(-8, 9):
        center = k * (math.pi / 2)
        for delta in (-1.0e-4, 0.0, 1.0e-4):
            a = center + delta
            (sx, cy, _, _), t = run(a)
            boundary_rows.append({"angle": a, "delta": delta, "tx": t[0], "ty": t[1],
                                  "sin_error": abs(sx - math.sin(a)),
                                  "cos_error": abs(cy - math.cos(a))})
            assert all(-0.250001 <= x <= 0.250001 for x in t[:2])
            assert abs(sx - math.sin(a)) < 6.0e-6
            assert abs(cy - math.cos(a)) < 6.0e-6

    # Negative control 3: the x lane is sin and y lane is cos; swapping fails.
    for a in [0.0, 0.2, math.pi / 3, -2.1]:
        (sx, cy, _, _), _ = run(a)
        assert abs(sx - math.sin(a)) < 3.0e-6
        assert abs(cy - math.cos(a)) < 3.0e-6
        assert abs(sx - math.cos(a)) > 0.05 or abs(cy - math.sin(a)) > 0.05

    assert sweep["period_0_to_2pi"]["max_sin_error"] < 4.0e-6
    assert sweep["period_0_to_2pi"]["max_cos_error"] < 4.0e-6
    assert sweep["signed_small"]["max_sin_error"] < 5.0e-6
    assert sweep["signed_small"]["max_cos_error"] < 5.0e-6
    assert nearest_control["nearest_sin_error"] > 0.1
    assert nearest_control["vu_round0_sin_error"] < 5.0e-6
    return {"sample_rows": rows, "sweeps": sweep,
            "random_range": random_range, "quarter_turn_boundaries": boundary_rows,
            "rounding_negative_control": nearest_control,
            "other_lane_negative_control_equal": lane0 == lane_random}


def main():
    print(json.dumps(evaluate_suite(), indent=2))


if __name__ == "__main__":
    main()
