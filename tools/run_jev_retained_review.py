#!/usr/bin/env python3
"""Run the twelve Jev capabilities over the retained-packet / menu98 PTG continuation and persist each receipt.

Jev advises only: byte comparisons, counts and hashes in the receipts come from the deterministic validators.
Usage: run_jev_retained_review.py STAGE   (stage1 | stage2 | stage3)
"""
import static_inputs
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import jev_mcp_call as J

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'research/evidence'
OUT = EV / 'packet-continuation/jev-retained'
EXPORT = static_inputs.bundle_path() / '.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po/decompilation/functions'
SCRATCH = Path('/private/tmp/claude-502/-Users-Nicolas-Documents-github-hermes-projects-carmodels/38d3722a-26ef-4e1f-9b59-4d16c19bd36e/scratchpad')

GS_REGS = """PS2 GS register ids used as the A+D address byte of a packed A+D qword (standard GS register map):
0x00 PRIM, 0x01 RGBAQ, 0x02 ST, 0x03 UV, 0x04 XYZF2, 0x05 XYZ2, 0x06 TEX0_1, 0x08 CLAMP_1, 0x14 TEX1_1, 0x18 XYOFFSET_1,
0x40 SCISSOR_1, 0x42 ALPHA_1, 0x44 DIMX, 0x45 DTHE, 0x46 COLCLAMP, 0x47 TEST_1, 0x4c FRAME_1, 0x4e ZBUF_1, 0x50 BITBLTBUF, 0x51 TRXPOS, 0x52 TRXREG, 0x53 TRXDIR.
In a packed A+D qword the low 64 bits are the DATA and the next byte is the register ADDRESS."""


def rd(p):
    return Path(p).read_text()


def save(name, tool, args):
    r = J.call(tool, args)
    res = r.get('result', r)
    if 'content' in res:
        try:
            res = json.loads(res['content'][0]['text'])
        except Exception:
            pass
    rec = {'jev_tool': tool, 'args': args, 'result': res}
    rec['result_sha256'] = hashlib.sha256(json.dumps(res, sort_keys=True).encode()).hexdigest()
    target = OUT / f'{name}.json'
    n = 2
    while target.exists():
        target = OUT / f'{name}-run{n}.json'; n += 1
    target.write_text(json.dumps(rec, indent=1))
    print(name, tool, json.dumps(res)[:600])
    return res


def digest():
    r = json.loads((EV / 'packet-continuation/retained-packet-blocks.json').read_text())
    g = json.loads((EV / 'packet-continuation/retained-blocks-gsdump-join.json').read_text())
    ring = json.loads((EV / 'packet-continuation/retained-ring-gsdump-alignment.json').read_text())
    p = json.loads((EV / 'ptg-continuation/menu98-sprite-ptg-join.json').read_text())
    c = {x['capture']: x for x in r['captures']}['race95']
    lines = []
    lines.append('SCOPE: every join below compares saved EE memory with a separate GSDump capture; none traces execution, so retained buffers are NOT claimed to prove that any function executed or produced any transfer, and render fidelity stays incomplete.')
    lines.append('RETAINED BLOCKS (race95 EE image, sha256 eacbcb2e8304957e35e784a927c4c17206ccef363c24eea6c1f6887f00f58355):')
    lines.append(f"- {c['raw_marker_counts']['0x6c058000']} aligned 0x6c058000 markers; every one parsed by the strict FUN_00128e88 layout parser with zero rejects; counts {[b['count'] for b in c['a_blocks'][:5]]} in two ring pages.")
    lines.append('- Each block REF pointer set is byte-equal to exactly one source header across all 35 car models and positionally equals COBRA file base 0x143b500 + plane offset: headers ' + str([b['join']['byte_equal_candidates'][0]['header'] for b in c['a_blocks'][:5]]) + '.')
    lines.append('- Pair copies differ only in word indices 18, 27, 39 and 48 (double-buffer unpack address 0x2c8/0x208 and VIF BASE 0x3aa/0x388); the fifth pair also differs at 51 and 60.')
    lines.append(f"- Controls rejected: {json.dumps(c['controls'])[:700]}")
    lines.append(f"- {c['raw_marker_counts']['0x6c048003']} aligned 0x6c048003 blocks parse as the FUN_0021ba50 A+D layout: GIF tag 0x1000000000008003, FRAME_1 data 0xff000000000a0050, ALPHA_1 data 0x44, TEST_1 data 0x50000.")
    lines.append('RETAINED BLOCK TO GSDUMP (race94 gs dump sha256 fe3cad80...):')
    for a in g['a_block_to_dump_tag'][:5]:
        lines.append(f"- block {a['marker']} header {a['car']}:{a['header']} count {a['count']} prim {a['prim']} matches GIF transfers {a['dump_tags_matching_count_prim_ADC']} on count, prim and ADC==source W; headers sharing count and W sequence across all cars: {a['all_car_headers_with_same_count_and_W_sequence']}.")
    lines.append(f"- header 324 UV: max abs error {list(g['a_block_to_dump_tag'][4]['uv_max_abs_error_by_dump_tag'].values())[0]:.2e}; one-unit UV mutation rejected: {g['a_block_to_dump_tag'][4]['uv_one_unit_mutation_rejected']}; but {len(g['a_block_to_dump_tag'][4]['uv_other_adc_candidates_matching_uv_1e-6'])} other cars have a header with the same W sequence and UV plane.")
    lines.append(f"- dump has exactly {g['dump_ad_triples']} A+D triples (FRAME_1, ALPHA_1, TEST_1) and retained memory has {g['b_blocks_retained']} FUN_0021ba50-shaped blocks; content key sets equal: {g['b_key_sets_equal']}.")
    lines.append('- following geometry transfers: ' + json.dumps(g['ad_triple_following_geometry']))
    al = ring['alignment']
    lines.append(f"RING ALIGNMENT: complete DMA chain {ring['chain']['start']}..{ring['chain']['end']} status {ring['chain']['status']} with {ring['chain']['elements']} elements; {ring['retained_draw_descriptors']} draw descriptors ({ring['kinds']}); {al['matched_tags']} aligned to dump tags in {al['blocks']} blocks (longest {al['longest_block']}); {al['pairs_with_source_W_plane']} aligned pairs have a source W plane: ADC equals W in {al['adc_equals_source_W']}, is a superset of W in {al['adc_superset_of_source_W']}, subset violations {al['adc_subset_violations_retained_idx_transfer']}.")
    lines.append('ALIGNMENT CONTROLS: ' + json.dumps(al['controls']))
    seven = [d for d in ring['draws'] if d.get('nloop') == 7 and d.get('source_headers')]
    lines.append('- seven-vertex retained call(s) with COBRA source header: ' + json.dumps([{k: d[k] for k in ('chain_addr', 'arm', 'pass_id', 'prim', 'ptr6', 'ptr4', 'source_headers', 'vec4_u32', 'effective_flags') if k in d} for d in seven][:3]))
    lines.append('MENU98 PTG: ' + json.dumps({'uploads_32x32_psmct32': p['dump']['uploads_32x32_psmct32']}) + f" fitted mapping {p['fitted_mapping_fb_to_screenshot']}; families {json.dumps({k: {a: (round(b, 1) if isinstance(b, float) else b) for a, b in v.items() if a in ('sprites', 'mean_abs_rgb_error', 'shifted_controls', 'swapped_tile_control')} for k, v in p['family_scores'].items()})}")
    lines.append('MATRIX groups: ' + json.dumps({k.rsplit('/', 1)[1]: [round(x, 1) for x in v['screenshot_bbox_px']] for k, v in p['per_ptg_groups'].items() if '/MATRIX/' in k}))
    return '\n'.join(lines)


def stage1():
    # 1 screen: external TypeSafe documentation text before it influences the plan
    doc = subprocess.run(['curl', '-sS', '-m', '30', 'https://docs.typesafe.ai/model-jaggedness/jev-1.13.md'], capture_output=True, text=True).stdout[:6000]
    save('01-screen-typesafe-jaggedness', 'jev_screen', {'text': doc, 'purpose': 'Decide how to phrase semantic judgments for the Ford Racing 2 recovery evidence review; the text is third-party documentation of the judgment model.'})
    # 3 compare: older prose claim vs the newer deterministic reading
    old = ('A third helper, 0021c3e0, chooses ALPHA 0x44 in the direct untextured branch when effective bit 0x20 is clear and passes it to 0021ba50, '
           'which writes fixed PRIM 0x4c and that ALPHA value.')
    new = ('FUN_0021ba50 writes one GIF A+D packet: GIF tag 0x1000000000008003 then three A+D pairs, FRAME_1 (address 0x4c, data built from FBP/FBW/PSM globals and the FBMSK argument), '
           'ALPHA_1 (address 0x42, data = its second argument, 0x44 in the retained blocks) and TEST_1 (address 0x47). It does not write PRIM; the 0x4c value is a register address.')
    save('03-compare-0021ba50-prose', 'jev_compare', {'passage_a': old, 'passage_b': new, 'aspects': ['what 0x4c denotes', 'ALPHA value passed', 'whether PRIM is written by FUN_0021ba50'], 'purpose': 'Reconcile earlier research prose with the decompiled function and retained A+D blocks.'})
    # 4 find: which function emits FRAME/ALPHA/TEST A+D pairs
    cands = []
    for fn in ('0021ba50', '0021bb48', '00128e88', '0021c3e0', '001288b0', '0021b850'):
        t = rd(EXPORT / f'{fn}.c')
        cands.append({'id': fn, 'text': t[:1900]})
    save('04-find-ad-packet-emitter', 'jev_find', {'query': 'function that writes a GIF packet of A+D register pairs setting FRAME_1, ALPHA_1 and TEST_1', 'candidates': cands, 'top_k': 3})
    # 5 rerank: next evidence to pursue for the ADC / cull rule
    cand = [
        {'id': 'live_vu1_trace', 'text': 'Attach a PCSX2 debugger or VU1 trace to capture the active micro-program counter and TOP-relative qword inputs while a COBRA strip is transformed.'},
        {'id': 'backface_cull_regression', 'text': 'Fit the extra ADC bits set beyond the source W lane against triangle orientation computed from projected vertices, using the aligned retained-descriptor to GSDump pairs.'},
        {'id': 'car_select_capture', 'text': 'Navigate the headless emulator through ordinary menus to a car and livery selection screen and capture its draw packets.'},
        {'id': 'livery_label_bridge', 'text': 'Trace source CARDATA valid-livery filenames and FUN_001a8b30 to map numeric texture selectors to human livery labels.'},
        {'id': 'glass_semantics', 'text': 'Decide the semantic part name and blend meaning of the duplicate seven-vertex alpha-102 COBRA headers using retained call flags and the pointer that selects header 149.'},
        {'id': 'rebuild_index_only', 'text': 'Rebuild the canonical asset index and rerun Khronos and Blender validators without any new export change.'}]
    save('05-rerank-next-evidence', 'jev_rerank', {'query': 'Which next work most directly closes the open material, normal and ADC rendering joins for the recovered original car models, given that retained descriptors are now aligned with executed GIF transfers?', 'candidates': cand})
    # 6 classify evidence statements by strength
    items = [
        {'id': 's1', 'text': 'All ten 0x6c058000 markers parse strictly and each referenced six-byte and four-byte plane is byte-equal to exactly one source header.'},
        {'id': 's2', 'text': 'GIF transfers 406 to 409 carry the same vertex counts, PRIM values and ADC sequences as the retained blocks for COBRA headers 320 to 323.'},
        {'id': 's3', 'text': 'The retained buffers prove that FUN_00128e88 ran during the dumped frame and produced transfer 406.'},
        {'id': 's4', 'text': 'Header 149 rather than header 261 is the producer of the seven-vertex alpha-102 packet.'},
        {'id': 's5', 'text': 'A one-bit flip of a referenced plane byte leaves zero byte-equal source headers.'},
        {'id': 's6', 'text': 'The extra ADC bits beyond the source W lane are the result of back-face culling in the VU1 program.'},
        {'id': 's7', 'text': 'Uploads of 32x32 PSMT8 tiles in the menu98 dump are exact substrings of GRAPHICS/GAME/MATRIX PTG files.'},
        {'id': 's8', 'text': 'The human livery label for numeric texture selector 2 of the Cobra is established.'}]
    classes = [
        {'id': 'deterministic_byte_fact', 'description': 'A statement fully established by an exact byte comparison, count or hash that code reproduced, including negative controls.'},
        {'id': 'bounded_content_join', 'description': 'A statement that two captures carry matching structured content (counts, sequences, positions) without proving that one produced the other.'},
        {'id': 'execution_claim_unproven', 'description': 'A statement that a specific code path executed or produced a specific output, which needs a live trace to prove.'},
        {'id': 'semantic_unresolved', 'description': 'A statement assigning meaning, naming or an exact rule that no current evidence settles.'},
        {'id': 'manual_review', 'description': 'Genuinely ambiguous statements that need a person to decide.'}]
    save('06-classify-evidence-strength', 'jev_classify', {'items': items, 'classes': classes, 'purpose': 'Label each continuation claim by the strength of the evidence that currently supports it.', 'context': 'Retained EE buffers were captured in separate savestates from the GSDump; code compared bytes but nothing traced execution.'})


def stage1b():
    ba = rd(EXPORT / '0021ba50.c')
    # 2 noul: calibrated propositions about what 0x4c is in FUN_0021ba50
    ctx = GS_REGS + '\n\nFUN_0021ba50 decompilation:\n' + ba
    save('02-noul-0021ba50-constants', 'jev_noul', {
        'propositions': [
            'In FUN_0021ba50, the constant 0x4c stored in puVar1[3] is the A+D register address of FRAME_1, not a PRIM register value.',
            'In FUN_0021ba50, the constant 0x4c stored in puVar1[3] is a PRIM register value written by this function.',
            'In FUN_0021ba50, the value param_2 is written as the data of the ALPHA_1 A+D pair whose address byte is 0x42.',
            'FUN_0021ba50 writes the GS PRIM register.',
            'In FUN_0021ba50, the constant 0x47 stored in puVar1[7] is the A+D register address of TEST_1.'],
        'context': ctx, 'auto_accept': 0.85})


def stage2():
    ev = digest()
    (OUT / 'evidence-digest.txt').write_text(ev)
    # 7 decide: next steps
    save('07-decide-next-step', 'jev_decide', {
        'decision': 'Which single next work item should this continuation pursue after reproducing the retained packet receipts?',
        'evidence': ev[:11000],
        'priorities': 'Keep PCSX2 and the game headless with no desktop focus theft; do not edit the shared source checkout; prefer deterministic evidence over narrative; keep render_fidelity_complete false until supported; do not claim execution without a trace.',
        'candidates': [
            {'id': 'adc_cull_regression', 'description': 'Use the 1,217 aligned retained-to-dump pairs to derive and test the rule for ADC bits set beyond the source W lane, with held-out pairs and negative controls.'},
            {'id': 'ordinary_car_select_capture', 'description': 'Drive the headless emulator by key events to an ordinary car and livery selection screen and capture it.'},
            {'id': 'document_and_gate', 'description': 'Write the three new receipts into the research notes, rerun validators and stop.'},
            {'id': 'gather_more_evidence', 'description': 'Ask for a live VU1 trace before doing anything else.'}],
        'requirements': ['The chosen item must be doable now without modifying the shared source checkout or launching a native desktop window.'],
        'escape_hatches': True})
    # 8 verify: claims vs digest
    claims = [
        'All ten 0x6c058000 blocks in the race95 image are fully parsed with zero rejects and each joins uniquely to COBRA headers 320 to 324 by bytes and by position.',
        'GIF transfers 406 to 409 and 6483 to 6486 match retained blocks for COBRA headers 320 to 323 by count, PRIM and ADC sequence, and those four headers are the only headers across all 35 cars with those count and W sequences.',
        'The header-324 retained block is uniquely identified as COBRA by the GSDump alone.',
        'The eight 0x6c048003 retained blocks have the same FRAME_1, ALPHA_1 and TEST_1 contents as the eight A+D triples in the GSDump.',
        'The retained buffers prove that FUN_00128e88 executed and produced GIF transfer 406.',
        'The aligned retained descriptor to GSDump pairs show ADC is a superset of the source W lane in all but one pair.',
        'The six visible car thumbnails of the menu98 screenshot are the six MATRIX PTGs 49couped, must68d, tbirdd, fortyd, tbird22d and fordgtd.',
        'The ChallGlo glow sprites are explained by the opaque-texel modulate colour model.']
    save('08-verify-continuation-claims', 'jev_verify', {'claims': claims, 'evidence': ev[:30000], 'auto_accept': 0.8})


def stage2b():
    ev = (OUT / 'evidence-digest.txt').read_text()
    # 9 extract: fields from the digest, regex proposes, Jev selects
    doc = ev
    fields = [
        {'id': 'ring_aligned_tags', 'pattern': r'\d{3,4}(?= aligned to dump tags)', 'description': 'the number of retained draw descriptors aligned to GSDump tags'},
        {'id': 'header_324_other_car_matches', 'pattern': r'(?<=but )\d+(?= other cars)', 'description': 'how many other cars have a header with the same W sequence and UV plane as header 324'},
        {'id': 'adc_superset_count', 'pattern': r'(?<=is a superset of W in )\d+', 'description': 'the number of aligned pairs where ADC is a superset of the source W lane'},
        {'id': 'cobra_file_base', 'pattern': r'(?<=COBRA file base )0x[0-9a-f]+', 'description': 'the EE address of the COBRA model file base'}]
    ex = save('09b-extract-digest-fields-tight-patterns', 'jev_extract', {'document': doc, 'fields': fields, 'purpose': 'Pull numeric receipt facts verbatim for a summary.'})
    # 10 audit: extracted values vs the full receipt source text
    recs = []
    for f in (ex.get('fields') or ex.get('results') or []):
        fid = f.get('id') or f.get('field')
        val = f.get('value')
        recs.append({'id': fid, 'request': next(x['description'] for x in fields if x['id'] == fid), 'value': val or ''})
    src = ev
    save('10b-audit-extracted-values-tight-patterns', 'jev_audit', {'source': src, 'records': recs or [{'id': 'none', 'request': 'none', 'value': ''}], 'wrong_at': 0.7})




def _diff(names):
    out = ''
    for n in names:
        t = (ROOT / 'tools' / n).read_text()
        out += f'--- /dev/null\n+++ b/tools/{n}\n@@ -0,0 +1,{t.count(chr(10))} @@\n' + ''.join('+' + l + '\n' for l in t.splitlines())
    return out


def stage3():
    tests = subprocess.run([sys.executable, str(ROOT / 'tools/test_retained_packet_evidence.py')], capture_output=True, text=True, cwd=ROOT / 'tools')
    tests_text = (tests.stdout + tests.stderr)[-3000:]
    # review: the three analysis scripts
    req_a = ('Measure, from executed GIF packets aligned with retained display-list descriptors, (1) the rule behind ADC bits beyond the source W lane, (2) colour-vector/alpha-lane joins, and (3) '
             'the menu98 sprite-to-PTG join with a fitted screenshot mapping validated on held-out data and controls. Do not claim a VU1 recovery or final blend equivalence.')
    save('11-review-analysis-scripts', 'jev_review', {'request': req_a, 'diff': _diff(['analyze_adc_cull_rule.py', 'trace_retained_material_alpha.py', 'join_menu98_sprites_to_ptg.py', 'gsdump.py'])[:49000], 'tests': tests_text})


def stage3b():
    tests = subprocess.run([sys.executable, str(ROOT / 'tools/test_retained_packet_evidence.py')], capture_output=True, text=True, cwd=ROOT / 'tools')
    tests_text = (tests.stdout + tests.stderr)[-3000:]
    # gate: validators plus completion claims with the evidence digest
    request = ('Reproduce the unsaved retained-packet lead as deterministic receipts: strict parsers for FUN_00128e88 and FUN_0021ba50 blocks in saved EE memory with pinned hashes, '
               'all-35-car source-plane controls and corruption controls, a join to the executed GSDump, and a whole-chain alignment. Do not claim execution; keep render fidelity incomplete.')
    diff = _diff(['validate_retained_packet_blocks.py', 'join_retained_blocks_to_gsdump.py', 'trace_retained_ring_to_gsdump.py', 'test_retained_packet_evidence.py'])
    ev = (OUT / 'evidence-digest.txt').read_text()
    claims = ['The new validators parse and cross-check the ten 0x6c058000 and eight 0x6c048003 retained blocks and the regression test passes.',
              'The receipts claim a content join and alignment to the GSDump but do not claim that retained buffers prove execution.',
              'Corruption and other-car controls reject mutated blocks and wrong source joins.']
    save('12-gate-packet-validators', 'jev_gate', {'request': request, 'diff': diff[:49000], 'claims': claims, 'evidence': ev[:60000] + '\n\nTEST RUN OUTPUT:\n' + tests_text, 'tests': tests_text})


if __name__ == '__main__':
    {'stage1': stage1, 'stage1b': stage1b, 'stage2': stage2, 'stage2b': stage2b, 'stage3': stage3, 'stage3b': stage3b}[sys.argv[1]]()
