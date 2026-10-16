"""Adapter boundary controls; optional execution is a separate explicit check."""
import copy
import json
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import mc3_reference_runtime as reference


def vu_job(pc=0, patches=(), vfpatches=()):
    micro, data = bytearray(16384), bytearray(16384)
    struct.pack_into('<IIII', micro, 0, 0x8000033c, 0x400002ff, 0x8000033c, 0x2ff)
    result = b'MC3VU001' + micro + data + struct.pack('<7I', 1, pc, 0x9e, 0x9e, 1000, len(patches), len(vfpatches))
    for offset, value in patches:
        result += struct.pack('<II', offset, len(value)) + value
    for register, value in vfpatches:
        result += struct.pack('<I', register) + value
    return bytes(result)


def ee_job(patches=()):
    result = b'MC3EE001' + struct.pack('<5I', 0x41ca38, 10000, 0, 1, len(patches)) + struct.pack('<If', 12, .5)
    for offset, value in patches:
        result += struct.pack('<II', offset, len(value)) + value
    return result


class ReferenceRuntimeTests(unittest.TestCase):
    def test_reference_contract_pins_every_abi_group(self):
        original = reference.contract()
        for key in ('source', 'symbols', 'layouts', 'adaptations', 'observed_controls'):
            changed = copy.deepcopy(original)
            changed[key] = {}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'receipt changed'):
                reference.contract(changed)
        with self.assertRaisesRegex(ValueError, 'binary identity'):
            reference.from_binary(b'not the pinned official binary')

    def test_vu_call_and_patch_bounds(self):
        reference.validate_job(vu_job(patches=[(16380, b'abcd')], vfpatches=[(1, bytes(16))]), 'vu')
        controls = [(vu_job(pc=2048), 'call input'),
                    (vu_job(patches=[(16381, b'abcd')]), 'data patch'),
                    (vu_job(vfpatches=[(0, bytes(16))]), 'VF patch')]
        for data, reason in controls:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                reference.validate_job(data, 'vu')

    def test_source_job_truncation_and_trailing_bytes(self):
        for data, reason in [(vu_job()[:-1], 'truncated'), (vu_job()+b'x', 'trailing'),
                             (b'notmagic'+vu_job()[8:], 'magic')]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                reference.validate_job(data, 'vu')

    def test_ee_ram_alias_scratchpad_and_refusal(self):
        reference.validate_job(ee_job([(0x80001000, b'abcd'), (0x70003ffc, b'abcd')]), 'ee')
        for address in [0x02000000, 0x70003ffd, 0x10000000]:
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, 'RAM patch'):
                reference.validate_job(ee_job([(address, b'abcd')]), 'ee')

    def test_gif_chunks_preserve_split_native_packet(self):
        tag, payload = bytes(range(16)), bytes(range(16, 32))
        carrier = struct.pack('<I', 16)+tag+struct.pack('<I', 16)+payload
        self.assertEqual(reference.gif_chunks(carrier), [tag, payload])
        for changed in [struct.pack('<I', 15)+tag, struct.pack('<I', 32)+tag, b'xx']:
            with self.assertRaises(ValueError):
                reference.gif_chunks(changed)

    def test_unprovisioned_runtime_is_explicit(self):
        with patch.object(reference.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(reference.RuntimeUnavailable, 'Docker'):
                reference.identity()

    def test_wrong_binary_refuses_abi_calls(self):
        with patch.object(reference.shutil, 'which', return_value='/docker'), \
                patch.object(reference, 'command', side_effect=['image', '{"binary":"changed","appimage":"changed"}']):
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                reference.identity()

    def test_unsupported_simd_profile_does_not_silently_change_math(self):
        result = json.dumps({'binary': reference.BINARY_SHA, 'appimage': reference.APPIMAGE_SHA, 'flags': ['sse4_1']})
        with patch.object(reference.shutil, 'which', return_value='/docker'), \
                patch.object(reference, 'command', side_effect=['image', result]):
            with self.assertRaisesRegex(reference.RuntimeUnavailable, 'AVX2/FMA'):
                reference.identity()

    def test_no_overwriting_previous_reference_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'run'
            reference.fresh_directory(path)
            (path/'receipt.json').write_text('original')
            with self.assertRaisesRegex(ValueError, 'must be empty'):
                reference.fresh_directory(path)
            self.assertEqual((path/'receipt.json').read_text(), 'original')

    def test_gs_completion_waits_for_whole_frame_and_alpha(self):
        png = b'\x89PNG\r\n\x1a\n'+b'body'+b'\0\0\0\0IEND'+bytes(4)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'00001_f00002_rt1_00000_C_32.png'
            target.write_bytes(png)
            target.with_name(target.stem+'_alpha.png').write_bytes(png)
            self.assertFalse(reference.gs_frame_complete(root))
            marker = root/'00003_f00002_fr0_00000_C_32.png'
            marker.write_bytes(png)
            alpha = marker.with_name(marker.stem+'_alpha.png')
            self.assertFalse(reference.gs_frame_complete(root))
            alpha.write_bytes(png[:-1])
            self.assertFalse(reference.gs_frame_complete(root))
            alpha.write_bytes(png)
            self.assertTrue(reference.gs_frame_complete(root))

    def test_opt_in_depth_preserves_default_and_waits_for_raw_depth(self):
        self.assertEqual(reference.gs_configuration(), reference.GS_CONFIG)
        configured = reference.gs_configuration(True)
        self.assertEqual(configured.replace('SaveDepth = true\n', ''), reference.GS_CONFIG)
        self.assertEqual(configured.count('SaveDepth = true\n'), 1)
        with self.assertRaisesRegex(ValueError, 'boolean'):
            reference.gs_configuration(1)
        png = b'\x89PNG\r\n\x1a\n'+b'body'+b'\0\0\0\0IEND'+bytes(4)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['00001_f00002_rt1_00000_C_32', '00002_f00002_fr0_00000_C_32']:
                (root/(name+'.png')).write_bytes(png)
                (root/(name+'_alpha.png')).write_bytes(png)
            self.assertTrue(reference.gs_frame_complete(root))
            self.assertFalse(reference.gs_frame_complete(root, save_depth=True))
            depth = root/'00001_f00002_rz1_01000_Z_16S.png'
            depth.write_bytes(png[:-1])
            self.assertFalse(reference.gs_frame_complete(root, save_depth=True))
            depth.write_bytes(png)
            self.assertTrue(reference.gs_frame_complete(root, save_depth=True))

    def test_gs_carrier_has_three_real_replay_frames(self):
        packet = reference.ad([(0x61, 0)])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.gs'
            reference.write_gs_dump(path, [packet], 64, 64)
            raw = path.read_bytes()
            magic, header_size = struct.unpack_from('<II', raw)
            self.assertEqual((magic, header_size), (0xffffffff, 36))
            state_size = struct.unpack_from('<I', raw, 12)[0]
            event = 8 + header_size + state_size + 8192
            for _ in range(3):
                self.assertEqual(raw[event:event+2], b'\0\2')
                length = struct.unpack_from('<I', raw, event+2)[0]
                self.assertEqual(raw[event+6:event+6+length], packet)
                event += 6+length
                self.assertEqual(raw[event], 3)
                event += 1+8192
                self.assertEqual(raw[event:event+2], b'\1\0')
                event += 2
            self.assertEqual(event, len(raw))

    def test_gs_display_framebuffer_maps_every_frame_without_changing_gif(self):
        packet = reference.ad([(0x61, 0)])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'display.gs'
            for base in [0, 0x100, 511]:
                reference.write_gs_dump(path, [packet], 64, 64, display_fbp=base)
                raw = path.read_bytes()
                header_size = struct.unpack_from('<I', raw, 4)[0]
                state_size = struct.unpack_from('<I', raw, 12)[0]
                registers = 8+header_size+state_size
                self.assertEqual(struct.unpack_from('<Q', raw, registers+0x70)[0], base | 1 << 9)
                event = registers+8192
                for _ in range(3):
                    length = struct.unpack_from('<I', raw, event+2)[0]
                    self.assertEqual(raw[event+6:event+6+length], packet)
                    event += 6+length
                    self.assertEqual(struct.unpack_from('<Q', raw, event+1+0x70)[0], base | 1 << 9)
                    event += 1+8192+2
            for base in [-1, 512, True, .5]:
                with self.assertRaisesRegex(ValueError, 'display framebuffer'):
                    reference.write_gs_dump(path, [packet], display_fbp=base)

    def test_image_nloop_limit_splits_without_resetting_transfer(self):
        pixels = bytes((i*13) % 256 for i in range(512*256*4))
        stream = reference.upload_rgba(pixels, 512, 256)
        offset, chunks, output = 16+4*16, [], bytearray()
        while offset < len(stream):
            tag, registers = struct.unpack_from('<QQ', stream, offset)
            self.assertEqual((tag >> 58) & 3, 2)
            self.assertEqual(registers, 0)
            count = tag & 0x7fff
            self.assertGreater(count, 0)
            chunks.append(count)
            offset += 16
            output.extend(stream[offset:offset+count*16])
            offset += count*16
        self.assertEqual(chunks, [32767, 1])
        self.assertEqual(bytes(output), pixels)
        self.assertEqual(offset, len(stream))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            reference.upload_rgba(bytes(1024*256*4), 1024, 256)

    def test_native_image_upload_is_not_png_color_conversion(self):
        pixels = bytes([4, 7, 12, 128])*16
        upload = reference.upload_rgba(pixels, 4, 4)
        self.assertEqual(upload[-len(pixels):], pixels)
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            reference.upload_rgba(pixels[:-1], 4, 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
