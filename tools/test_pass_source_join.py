#!/usr/bin/env python3
"""Regression of source joins, intended control reasons and GS export decoding."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile

import verify_pass_source_join as check


def main():
    inputs = check.load_inputs()
    result, png = check.derive(inputs)
    assert [result['by_pass_word'][str(p)]['draws'] for p in (4, 5)] == [37, 63]
    assert len(result['rows']) == 100 and len(result['loaded_car_bases']) == 6
    assert {r['car'] for r in result['rows']} == {'COBRA'}
    assert all(r['source_planes'] and r['header_raw_hex'] for r in result['rows'])
    texture = result['pass4_texture']
    assert texture['classification'] == 'not a car texture' and texture['car_texture_index'] is None
    assert (texture['TBP0'], texture['PSM'], texture['width'], texture['height']) == (0x29c0, 10, 256, 128)
    assert texture['preceding_render_target_draws'] == 905
    assert texture['last_render_target_draw_before_sampling']['transfer'] < texture['first_sample_transfer']
    assert not result['flag_rule']['sufficient_by_header_flags_alone']
    assert not result['render_fidelity_complete'] and len(result['claim_limits']) >= 4
    assert png == check.IMAGE.read_bytes()
    controls = check.controls(inputs)
    assert [c['reason'].split(':')[0] for c in controls] == ['wrong Header', 'wrong texture']
    result['controls'] = controls
    assert json.loads(check.OUT.read_text()) == result
    # Eligible Headers are necessary even when the saved pointer declaration agrees.
    invalid = copy.deepcopy(inputs)
    row = result['rows'][0]
    invalid['cars'][row['car']][1][row['header_index']]['flags'] &= ~0x10
    try:
        check.derive(invalid)
    except check.JoinError as error:
        assert 'Header pass eligibility flag missing' in str(error)
    else:
        raise AssertionError('missing source eligibility flag accepted')
    # Independent GSTables fixture: x=33,y=17 has block16S[2][2]=24,
    # column16[1][1]=6. GS Expand16To32 uses shifts, not 255/31 expansion.
    gs = bytearray(425 + 4194304 + 84)
    struct.pack_into('<I', gs, 0, 9)
    struct.pack_into('<H', gs, 425 + (0x29c0 + 24) * 256 + 6 * 2, 1 | 2 << 5 | 3 << 10)
    image, metadata = check.target_image(gs, texture)
    rgba = bytearray(256 * 128 * 4)
    rgba[3::4] = bytes([255]) * (256 * 128)
    at = (17 * 256 + 33) * 4
    rgba[at:at + 4] = bytes([8, 16, 24, 255])
    assert image == check.png_bytes(256, 128, bytes(rgba))
    assert metadata['preview_rgba_sha256'] == check.common.sha256(rgba)
    # The file pin fires before a changed captured image can be re-exported.
    with tempfile.NamedTemporaryFile() as altered:
        altered.write(inputs['gs'][:-1] + bytes([inputs['gs'][-1] ^ 1]))
        altered.flush()
        original = check.GS
        try:
            check.GS = Path(altered.name)
            try:
                check.load_inputs()
            except check.JoinError as error:
                assert 'retained GS memory differs from capture pin' in str(error)
            else:
                raise AssertionError('changed GS capture accepted')
        finally:
            check.GS = original
    # A missing capture is a named skip in the aggregate checks, and a one-line
    # error for direct verification, rather than an uncaught file traceback.
    original, argv = check.GS, sys.argv
    try:
        sys.argv = ['verify_pass_source_join.py', '--available']
        assert check.main() == 0
        check.GS = check.ROOT / '.scratch/issue21-does-not-exist-GS.bin'
        assert check.main() == 1
        try:
            check.load_inputs()
        except SystemExit as error:
            assert 'runtime input missing: issue21-does-not-exist-GS.bin' in str(error)
            assert '\n' not in str(error)
        else:
            raise AssertionError('missing GS capture accepted')
    finally:
        check.GS, sys.argv = original, argv
    print('PASS test_pass_source_join: 100 draws, wrong-Header/wrong-texture reasons, flag, swizzle and GS-pin controls')


if __name__ == '__main__':
    main()
