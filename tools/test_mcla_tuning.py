"""Car tuning decoding on a synthetic resource: root, seventeen slots, section headers and field typing."""
import struct
import unittest

import mcla_tuning
from mcla_tuning import ROOT_VFT, SECTIONS, SLOT_CLASSES, TUNE_PATH, TuningError, decode
from test_mcla_resource import Builder

CODE = 'vp_test_car_01'
VARIANTS = {1: 'base', 2: 'mods', 6: 'base', 7: 'mods', 8: 'base', 9: 'mods', 10: 'base', 11: 'mods'}


def build():
    b, at = Builder(), {}
    root = b.alloc(0x98)
    b.put(root, 'II', ROOT_VFT, 0)
    b.data[root + 8:root + 8 + len(CODE)] = CODE.encode()
    b.put(root + 0x48, 'Ii', 0, -1)
    b.put(root + 0x94, 'I', 0)
    path, names, owners = b.text(TUNE_PATH), {}, {}
    for slot, cls in enumerate(SLOT_CLASSES):
        if cls:
            names.setdefault(cls, b.text(cls))
        owner = CODE + ('_' + VARIANTS[slot] if slot in VARIANTS else '')
        owners.setdefault(owner, b.text(owner))
    target = b.alloc(4)
    b.put(target, 'I', 7)
    for slot, cls in enumerate(SLOT_CLASSES):
        section = b.alloc(48)
        b.put(root + 0x50 + 4 * slot, 'I', b.pointer(section))
        if cls:
            owner = CODE + ('_' + VARIANTS[slot] if slot in VARIANTS else '')
            b.put(section, '6I', 0x1CE25700 + slot, b.pointer(owners[owner]), b.pointer(names[cls]), b.pointer(path),
                  0, 0x01000000)
            b.put(section + 24, 'fiIIIf', 1.5, 3, b.pointer(target), 0x7F800001, 0, 2.0)
        else:
            b.put(section, '4f', 60.0, 0.0, 0.2, 20.0)
            b.put(section + 16, 'II', 0x5FFFFFF0, 0xFFFFFFFF)
        b.alloc(16, fill=0xCD)
        at[slot] = section
    at.update(root=root, path=path, names=names, owners=owners, target=target)
    data, virtual, physical = b.segment()
    return bytearray(data), virtual, physical, at


def patched(data, at, fmt, *values):
    data = bytearray(data)
    struct.pack_into('>' + fmt, data, at, *values)
    return data


class Decoding(unittest.TestCase):
    def test_slots_variants_and_field_types(self):
        data, virtual, physical, at = build()
        decoded = decode(bytes(data), virtual, physical)
        self.assertEqual(decoded['code'], CODE)
        sections = decoded['sections']
        self.assertEqual(len(sections), SECTIONS)
        self.assertEqual([s['class'] for s in sections], list(SLOT_CLASSES))
        self.assertEqual({s['slot']: s['variant'] for s in sections if s.get('variant')}, VARIANTS)
        sim = sections[6]
        self.assertEqual((sim['owner'], sim['path'], sim['bytes']), (CODE + '_base', TUNE_PATH, 48))
        self.assertEqual([(f['offset'], f['type'], f['value']) for f in sim['fields']],
                         [(24, 'float', 1.5), (28, 'int', 3), (32, 'pointer', at['target']),
                          (36, 'nan', '0x7f800001'), (40, 'zero', 0), (44, 'float', 2.0)])
        block = sections[12]
        self.assertIsNone(block['class'])
        self.assertEqual([f['type'] for f in block['fields']][:6], ['float', 'zero', 'float', 'float', 'float', 'int'])
        self.assertEqual(block['fields'][5]['value'], -1)

    def test_section_ends_at_the_next_pointed_object(self):
        data, virtual, physical, at = build()
        # Remove the fill after slot 12 so the section runs until the next object a pointer names.
        start = at[12] + 48
        data[start:start + 16] = bytes(16)
        sections = decode(bytes(data), virtual, physical)['sections']
        self.assertEqual(sections[12]['bytes'], at[13] - at[12])


class Rejections(unittest.TestCase):
    def setUp(self):
        self.data, self.virtual, self.physical, self.at = build()

    def rejects(self, data, reason):
        with self.assertRaisesRegex(TuningError, reason):
            decode(bytes(data), self.virtual, self.physical)

    def test_root(self):
        self.rejects(patched(self.data, 0, 'I', 1), 'not a tuning resource')
        self.rejects(patched(self.data, 8, '64s', b'x' * 64), 'longer than its field')
        self.rejects(patched(self.data, 0x4C, 'I', 0), 'root header words')
        self.rejects(patched(self.data, 0x94, 'I', Builder.pointer(0x40)), 'exactly seventeen')
        self.rejects(patched(self.data, 0x50 + 4 * 7, 'I', struct.unpack_from('>I', self.data, 0x50 + 4 * 6)[0]),
                     'share one section')

    def test_sections(self):
        sim = self.at[6]
        gyro_name = Builder.pointer(self.at['names']['vehGyro'])
        self.rejects(patched(self.data, sim + 8, 'I', gyro_name), 'slot 6 holds vehGyro, not vehSim')
        self.rejects(patched(self.data, sim + 12, 'I', gyro_name), 'outside \\$/tune/vehicle/')
        foreign = Builder.pointer(self.at['path'])
        self.rejects(patched(self.data, sim + 4, 'I', foreign), 'owned by another car')
        self.rejects(patched(self.data, sim + 20, 'I', 1), 'section header words')
        self.rejects(patched(self.data, sim + 4, 'I', 0x50FFFFF0), 'outside its segment')

    def test_struct_errors_become_tuning_errors(self):
        original = mcla_tuning.section
        mcla_tuning.section = lambda *_: struct.unpack('>I', b'')
        try:
            self.rejects(self.data, 'unpack requires')
        finally:
            mcla_tuning.section = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
