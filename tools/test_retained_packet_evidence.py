#!/usr/bin/env python3
"""Regenerate and assert the retained-packet, GSDump-join and menu98 PTG receipts (deterministic; no model calls)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'research/evidence'
HERE = Path(__file__).parent


def run(name):
    r = subprocess.run([sys.executable, str(HERE / name)], capture_output=True, text=True, cwd=HERE)
    assert r.returncode == 0, (name, r.stderr[-2000:])


def main():
    for n in ('validate_retained_packet_blocks.py', 'join_retained_blocks_to_gsdump.py', 'trace_retained_ring_to_gsdump.py', 'analyze_adc_cull_rule.py', 'trace_retained_material_alpha.py', 'join_menu98_sprites_to_ptg.py'):
        run(n)
    r = json.loads((EV / 'packet-continuation/retained-packet-blocks.json').read_text())
    caps = {c['capture']: c for c in r['captures']}
    c = caps['race95']
    assert c['raw_marker_counts'] == {'0x6c058000': 10, '0x6c048003': 8} and not c['a_rejects'] and not c['b_rejects']
    assert [b['count'] for b in c['a_blocks']] == [63, 62, 64, 41, 37] * 2
    assert [b['join']['byte_equal_candidates'][0]['header'] for b in c['a_blocks']] == [320, 321, 322, 323, 324] * 2
    assert all(len(b['join']['byte_equal_candidates']) == 1 and b['join']['positional_candidates_at_base'] for b in c['a_blocks'])
    assert [b['param8_mask'] for b in c['a_blocks'][:5]] == [0xa4, 0xa4, 0xa4, 0xa4, 0x60]
    assert all('rejected' in v for v in c['controls']['word_corruption'].values())
    assert c['controls']['plane_bit_flip_six']['byte_equal_candidates'] == 0 and not c['controls']['other_car_six_plane_contains_probe']['cars_with_match']
    assert all(p['differing_word_indices'][:3] == [18, 27, 39] and p['same_pointers'] for p in r['race95_pairs'])
    g = json.loads((EV / 'packet-continuation/retained-blocks-gsdump-join.json').read_text())
    assert [a['dump_tags_matching_count_prim_ADC'] for a in g['a_block_to_dump_tag'][:4]] == [[406, 6483], [407, 6484], [408, 6485], [409, 6486]]
    assert g['a_block_to_dump_tag'][4]['dump_tags_matching_count_prim_ADC'] == [411, 6488] and g['a_block_to_dump_tag'][4]['all_car_headers_with_same_count_and_W_sequence'] == 32
    assert g['b_key_sets_equal'] and g['b_blocks_retained'] == g['dump_ad_triples'] == 8
    ring = json.loads((EV / 'packet-continuation/retained-ring-gsdump-alignment.json').read_text())
    assert ring['chain']['status'] == 'END' and ring['retained_draw_descriptors'] == 1497
    al = ring['alignment']
    assert al['matched_tags'] >= 1300 and al['adc_superset_of_source_W'] == al['pairs_with_source_W_plane'] - len(al['adc_subset_violations_retained_idx_transfer'])
    assert len(al['adc_subset_violations_retained_idx_transfer']) <= 1
    ctl = al['controls']
    assert ctl['reversed_dump_sequence']['matched_tags'] * 5 < al['matched_tags'] and ctl['shuffled_dump_sequence']['longest_block'] * 20 < al['longest_block']
    assert ctl['adc_rotated_one_vertex_superset_pairs'] * 10 < al['adc_superset_of_source_W']
    adc = json.loads((EV / 'packet-continuation/adc-cull-rule-test.json').read_text())
    rule = adc['rule_gated_by_pass_id']
    assert rule['held_out']['accuracy_over_W0_vertices'] >= 0.99 and rule['held_out']['vertices'] > 10000
    for k in ('control_without_pass_gate', 'control_mirrored_sign', 'control_shuffled_orientation'):
        assert rule[k]['accuracy_over_W0_vertices'] < 0.8, k
    assert adc['held_out']['P(ADC=1 | W=0, front-facing)'] < 0.01 < 0.5 < adc['held_out']['P(ADC=1 | W=0, back-facing)']
    mat = json.loads((EV / 'packet-continuation/retained-material-alpha-join.json').read_text())
    for k in ('1', '2'):
        assert mat['by_pass_id'][k]['alpha_lanes_all_equal_vec4_w'] == mat['by_pass_id'][k]['aligned_draws'] > 500
    assert mat['by_pass_id']['4']['alpha_lanes_all_equal_vec4_w'] == 0
    assert mat['pass2_vec4_equals_source_base_color_rgba_unscaled'] == {'draws': 108, 'vec4_equals_base_color_rgba': 108}
    assert {tuple(x['source_headers'][0]) for x in mat['seven_vertex_retained_calls_with_cobra_pointer']} == {('COBRA', 149)}
    assert mat['duplicate_headers']['material_words_equal'] and len({x['ptr6'] for x in mat['seven_vertex_retained_calls_with_cobra_pointer']}) == 1
    assert len(g['a_block_to_dump_tag'][4]['uv_other_adc_candidates_matching_uv_1e-6']) == 29
    p = json.loads((EV / 'ptg-continuation/menu98-sprite-ptg-join.json').read_text())
    fam = p['family_scores']
    for key in ('GRAPHICS/GAME/CHALL|psmct32', 'GRAPHICS/GAME/MATRIX|psmt8_clut'):
        f = fam[key]
        assert f['mean_abs_rgb_error'] * 2 < min(f['shifted_controls'].values()) and f['mean_abs_rgb_error'] * 2 < f['swapped_tile_control'], key
    assert sorted(k.rsplit('/', 1)[1] for k in p['per_ptg_groups'] if '/MATRIX/' in k) == ['49couped.ptg;1', 'fordgtd.ptg;1', 'fortyd.ptg;1', 'must68d.ptg;1', 'tbird22d.ptg;1', 'tbirdd.ptg;1']
    assert all(v['clut_matches_ptg_palette_all'] for k, v in p['per_ptg_groups'].items() if '/MATRIX/' in k)
    print('RETAINED PACKET EVIDENCE OK')


if __name__ == '__main__':
    main()
