"""Read-only decoding of Midnight Club: Los Angeles car tuning resources (`.xct`, RSC5 type 50).

No external layout reference exists for car tuning (CodeX.Games.MCLA reads `.xct` as city data, which
these are not). The layout below is read from the resources themselves and checked on all 106 cars:

- Root: VFT (stored little-endian 0x0057C7FC), block map, the car code as an inline 64-byte string
  (+0x08), a zero word, -1, then seventeen section pointers (+0x50).
- A tuning section starts with a VFT, pointers to its owner name (`<code>`, `<code>_base` or
  `<code>_mods`), its class name and its tune folder (`$/tune/vehicle/`), a zero word and 1. Class
  names and the `%s_base` / `%s_mods` patterns also appear in the game executable.
- Slots 12 and 13 are headerless blocks of 32-bit floats; slot 16 has no class name.

Field names are not stored on the disc: fields are typed 32-bit words by offset (pointer, float,
integer, zero, or NaN such as the 0x7F800001 vector padding). A section ends at its first 0xCDCDCDCD fill word or
at the next object the resource points to.
"""
import math
import struct

from mcla_resource import Resource, ResourceError

ROOT_VFT = 0xFCC75700
SECTIONS = 17
SLOT_CLASSES = ('vehStuck', 'vehInput', 'vehInput', 'vehDamage', 'vehModel', 'vehCamShake', 'vehSim', 'vehSim',
                'vehGyro', 'vehGyro', 'vehAbility', 'vehAbility', None, None, 'vehZone', 'vehGrip', None)
FILL = 0xCDCDCDCD
TUNE_PATH = '$/tune/vehicle/'


class TuningError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise TuningError(message)


def word_type(r, value):
    if value == 0:
        return 'zero', 0
    if value >> 28 == 5:
        try:
            return 'pointer', r.offset(value)
        except ResourceError:
            pass
    if value < 0x00800000 or value == 0xFFFFFFFF:
        return 'int', struct.unpack('>i', struct.pack('>I', value))[0]
    number = struct.unpack('>f', struct.pack('>I', value))[0]
    if math.isfinite(number):
        return 'float', number
    return 'nan', '0x%08x' % value  # vector padding (0x7F800001 and other NaN patterns)


def object_starts(r, used):
    """Every offset a pointer in the used part of the resource addresses."""
    starts = set()
    for at in range(0, used - 3, 4):
        value = r.u32(at)
        if value >> 28 == 5 and (value & 0x0FFFFFFF) < r.virtual:
            starts.add(value & 0x0FFFFFFF)
    return sorted(starts)


def decode(data, virtual, physical):
    """A decompressed tuning resource -> {'code', 'sections': [...]}."""
    try:
        r = Resource(data, virtual, physical)
        need(r.u32(0) == ROOT_VFT, 'not a tuning resource (VFT 0x%08x)' % r.u32(0))
        code = r.cstring(8)
        need(len(code) < 64, 'car code longer than its field')
        need((r.u32(0x48), r.u32(0x4C)) == (0, 0xFFFFFFFF), 'unexpected root header words')
        pointers = [r.u32(0x50 + 4 * i) for i in range(SECTIONS + 1)]
        need(all(p >> 28 == 5 for p in pointers[:SECTIONS]) and pointers[SECTIONS] >> 28 != 5,
             'tuning root does not hold exactly seventeen section pointers')
        used = len(data)
        while used and data[used - 1] == 0xCD:
            used -= 1
        starts = object_starts(r, used)
        sections = []
        for slot, pointer in enumerate(pointers[:SECTIONS]):
            at = r.offset(pointer, 4)
            end = min([s for s in starts if s > at] + [virtual])
            stop = at
            while stop < end and r.u32(stop) != FILL:
                stop += 4
            sections.append(section(r, slot, at, stop, code))
        need(len({s['offset'] for s in sections}) == SECTIONS, 'two tuning slots share one section')
    except (ResourceError, struct.error) as error:
        raise TuningError(str(error)) from None
    return {'code': code, 'sections': sections}


def section(r, slot, at, stop, code):
    expected = SLOT_CLASSES[slot]
    out = {'slot': slot, 'offset': at, 'bytes': stop - at}
    if expected is None:
        out['class'] = None
        out['fields'] = [field(r, at, k) for k in range(0, stop - at, 4)]
        return out
    vft, owner, kind, path = (r.u32(at + 4 * k) for k in range(4))
    out.update(vft=vft, owner=r.cstring(r.offset(owner)), **{'class': r.cstring(r.offset(kind))},
               path=r.cstring(r.offset(path)))
    need(out['class'] == expected, 'slot %d holds %s, not %s' % (slot, out['class'], expected))
    need(out['path'] == TUNE_PATH, 'tuning section outside %s' % TUNE_PATH)
    need(out['owner'] in (code, code + '_base', code + '_mods'), 'tuning section owned by another car')
    need((r.u32(at + 16), r.u32(at + 20)) == (0, 0x01000000), 'unexpected tuning section header words')
    out['variant'] = out['owner'][len(code) + 1:] or None
    out['fields'] = [field(r, at, k) for k in range(24, stop - at, 4)]
    return out


def field(r, at, offset):
    kind, value = word_type(r, r.u32(at + offset))
    return {'offset': offset, 'type': kind, 'value': value}
