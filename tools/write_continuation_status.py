#!/usr/bin/env python3
"""Write the machine-readable status of the 2026-10-05 retained-packet continuation (hashes of receipts/tools, source freshness, runtime state)."""
import static_inputs
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = static_inputs.bundle_path()
OUT = ROOT / 'research/evidence/continuation/continuation-2026-10-05-status.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sh(*cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd).stdout.strip()


def main():
    receipts = ['research/evidence/packet-continuation/' + n for n in (
        'retained-packet-blocks.json', 'retained-blocks-gsdump-join.json', 'retained-ring-gsdump-alignment.json', 'adc-cull-rule-test.json', 'retained-material-alpha-join.json')]
    receipts.append('research/evidence/ptg-continuation/menu98-sprite-ptg-join.json')
    receipts.append('research/evidence/carselection-2026-10-05/bridge-three-screens.json')
    for label in ('slot101-live-backup', 'slot102-car1-ford49', 'slot103-car5-tbirdconv', 'slot104-car4-fortyninec'):
        receipts.append('research/evidence/continuation/runtime/linux/%s-state-identity.json' % label)
    tools = ['tools/' + n for n in ('gsdump.py', 'validate_retained_packet_blocks.py', 'join_retained_blocks_to_gsdump.py', 'trace_retained_ring_to_gsdump.py',
                                     'analyze_adc_cull_rule.py', 'trace_retained_material_alpha.py', 'join_menu98_sprites_to_ptg.py', 'test_retained_packet_evidence.py',
                                     'jev_mcp_call.py', 'run_jev_retained_review.py', 'write_continuation_status.py', 'unpack_runtime_state.py',
                                     'battery_d1.py', 'battery_d1_fix.py', 'battery_d2.py', 'scan_slot102_selectors.py', 'diff_slot102_103.py', 'triangulate_highlight.py')]
    jev = sorted((ROOT / 'research/evidence/packet-continuation/jev-retained').glob('*.json'))
    status = {
        'scope': 'Status of the retained display-list and menu98 PTG continuation; not a whole-recovery completion gate.',
        'render_fidelity_complete': False,
        'static_inputs': {'bundle_identity': json.loads((SRC / 'bundle-identity.json').read_text()),
                          'typed_inventory_sha256': sha(static_inputs.typed_export() / 'inventory.json')},
        'canonical_index_sha256': sha(ROOT / 'ford-racing-2/recovered/index.json'),
        'runtime': {'container': sh('docker', 'ps', '--filter', 'name=fr2-recovery-headless', '--format', '{{.ID}} {{.Status}}'),
                    'pine_identity': sh('docker', 'exec', 'fr2-recovery-headless', 'python3', '/data/pine_control.py', 'identity'),
                    'port': sh('docker', 'port', 'fr2-recovery-headless'),
                    'actions_this_continuation': 'ordinary car-selection capture: hidden-browser key delivery proven (Space toggled PINE status 1->0), slot 98 loaded, Cross opened VEHICLE detail panel, 3 labeled screens saved to slots 102/103/104 with unpacked members; slot 100 untouched, live race restored from slot 101 and left paused; ~21 observed key presses'},
        'receipts': {r: sha(ROOT / r) for r in receipts},
        'tools': {t: sha(ROOT / t) for t in tools},
        'jev_receipts': {p.name: sha(p) for p in jev},
        'handoff_lead_dispositions': {
            'ten aligned 0x6c058000 markers in five paired copies': 'reproduced at the same addresses; strict parse, pinned hashes, unique byte and positional joins, controls',
            'counts 63/62/64/41/37, headers 320-324, param8 0xa4 x4 and 0x60, third 0xffff x4 and 20': 'reproduced',
            'eight 0x6c048003 blocks': 'reproduced at the same addresses; they are FUN_0021ba50 A+D packets',
            'A+D fields PRIM 0x4c / ALPHA 0x44': 'partly wrong: 0x4c is the A+D address of FRAME_1; ALPHA_1 data is 0x44; PRIM is not written by 0021ba50',
            'no GS-transfer join for the 0x6c048003 blocks': 'content join established: eight dump A+D triples with identical FRAME_1/ALPHA_1/TEST_1 data; not an execution proof',
            'unsaved Jev retained_candidate 0.95/0.96': 'not reproducible (request not persisted); superseded by deterministic receipts',
            '00128e88 -> 0021ba50 direct chain': 'still unsupported: 00128e88 is called by 001288b0; 0021ba50 by 0021c3e0, which is called by 0021bf28 and 00128218'},
        'open': ['execution trace of CPU/DMA/VIF/VU1 for the dumped frame', 'VU1 microprogram branch for culling and RGB of passes 4-5', 'glass part naming and whether header 261 is drawn in other states',
                 'numeric selector to human livery label bridge (partial: 3 ordinary-capture label pairs at DEFAULT; isolated per-screen selector word still open)', 'ordinary car/livery selection capture (partial: cars 1/5/4 labeled screens in slots 102/103/104; livery-variant cycling not attempted)', 'ChallGlo blend model', '158 unmatched retained descriptors and descriptors outside the six loaded cars'],
    }
    OUT.write_text(json.dumps(status, indent=1) + '\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
