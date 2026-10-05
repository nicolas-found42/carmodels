#!/usr/bin/env python3
"""Regression checks for the pinned 100-draw comparison and its corruption controls."""
import copy
import json
import struct

import verify_vu_handler_dump as check


def main():
    inputs = check.load_inputs()
    result = check.derive(inputs)
    s4, s5 = result['by_pass_word']['4'], result['by_pass_word']['5']
    assert (s4['draws'], s4['vertices'], s5['draws'], s5['vertices']) == (37, 2189, 63, 3666)
    assert s4['rgb_from_raw_float_alpha_draws'] == 37
    assert s5['rgba_from_retained_dm5_draws'] == 63
    assert (s5['t_exact_draws'], s5['t_exact_vertices'], s5['t_one_ulp_vertices'], s5['t_max_ulp']) == (54, 3387, 279, 1)
    assert s5['paused_dm5_mismatching_draws'] == 63
    assert s5['t_without_colour_factor_failing_vertices'] == 512
    assert len(result['rows']) == 100 and not result['render_fidelity_complete']
    assert result['claim_limits']
    controls = check.controls(inputs)
    assert len(controls) == 8 and all(c['rejected'] for c in controls)
    # An absent matrix packet must fail rather than borrowing arbitrary paused memory.
    absent = copy.deepcopy(inputs)
    absent['uploads'] = []
    try:
        check.derive(absent)
    except check.ComparisonError as error:
        assert 'matrix upload missing' in str(error)
    else:
        raise AssertionError('absent per-draw input accepted')
    # Non-finite packet input must not reach integer conversion or disappear in rounding.
    try:
        check.real(struct.unpack('<I', struct.pack('<f', float('inf')))[0])
    except check.ComparisonError as error:
        assert 'non-finite' in str(error)
    else:
        raise AssertionError('non-finite input accepted')
    result['controls'] = controls
    assert json.loads(check.OUT.read_text()) == result
    print('PASS test_vu_handler_dump: 100 draws, eight intended corruption failures, absent-input and non-finite checks')


if __name__ == '__main__':
    main()
