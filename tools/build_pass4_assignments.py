#!/usr/bin/env python3
"""Derive the recovered inspector's candidate pass-4 shading table from the committed receipts.

The table names the source Headers the pass-source join found with an aligned pass-4 draw, the
sampled view render target and its retained preview. It carries no new claim: every field is copied
from research/evidence/vu-dispatch/pass-source-join.json and the preview it pins, so the inspector's
"Game shading (candidate)" control can identify a pass-4 Header offline.

    python3 tools/build_pass4_assignments.py           # write the table and the preview copy
    python3 tools/build_pass4_assignments.py --check   # verify both are current
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'research/evidence/vu-dispatch/pass-source-join.json'
PREVIEW = ROOT / 'research/evidence/vu-dispatch/pass4-retained-target.png'
OUTPUT = ROOT / 'dealership/public/game-shading-pass4.json'
PREVIEW_OUTPUT = ROOT / 'dealership/public/pass4-retained-target.png'
SCHEMA = 'fr2-game-shading-pass4/v1'
RECEIPT_SCHEMA = 'fr2-pass-source-join/v1'
PASS4_DRAWS = 37
FR2_GAME = 'ford-racing-2'
RULE = ('Header bit 0x10 maps to effective bit 0x80; a pass-4 draw requires '
        '(effective_flags & 0x88) == 0x80 and its per-draw global enable. The rows below are the '
        '37 aligned pass-4 draws of the pass-source join, not a proven live dispatch.')


class DerivationError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise DerivationError(message)


def text(value, label):
    need(isinstance(value, str) and value, 'missing %s' % label)
    return value


def number(value, label):
    need(isinstance(value, int) and not isinstance(value, bool) and value >= 0, 'invalid %s' % label)
    return value


def derive(receipt_bytes, preview_bytes):
    need(len(receipt_bytes) and len(preview_bytes), 'a source input is empty')
    receipt = json.loads(receipt_bytes)
    need(receipt.get('schema') == RECEIPT_SCHEMA, 'pass-source-join schema differs')
    rows = [row for row in receipt['rows'] if row.get('pass_word') == 4]
    need(len(rows) == PASS4_DRAWS, 'expected %d pass-4 draws, found %d' % (PASS4_DRAWS, len(rows)))
    cars = {}
    for row in rows:
        code = text(row.get('car'), 'row car')
        offset = number(row.get('header_offset'), 'header offset')
        entry = cars.setdefault(code, {'offsets': [], 'headers': [], 'vertices': 0})
        need(offset not in entry['offsets'], 'duplicate Header offset in ' + code)
        entry['offsets'].append(offset)
        entry['headers'].append({'index': number(row.get('header_index'), 'header index'), 'offset': offset,
                                 'flags': number(row.get('header_flags'), 'header flags')})
        entry['vertices'] += number(row.get('vertices'), 'vertex count')
    texture = receipt['pass4_texture']
    need(texture.get('identity') == 'view-render-target-0', 'sampled texture identity differs')
    digest = hashlib.sha256(preview_bytes).hexdigest()
    need(digest == texture.get('png_sha256'), 'retained preview differs from the receipt pin')
    return {
        'schema': SCHEMA,
        'label': 'candidate',
        'source': {'receipt': str(RECEIPT.relative_to(ROOT)), 'receipt_sha256': hashlib.sha256(receipt_bytes).hexdigest(),
                   'pass4_draws': len(rows), 'rule': RULE},
        'texture': {'identity': texture['identity'], 'file': 'public/pass4-retained-target.png',
                    'source_png': str(PREVIEW.relative_to(ROOT)), 'sha256': digest,
                    'width': number(texture['width'], 'texture width'), 'height': number(texture['height'], 'texture height'),
                    'psm': number(texture['PSM'], 'texture format'), 'tbp0': number(texture['TBP0'], 'texture base'),
                    'tbw': number(texture['TBW'], 'texture buffer width')},
        'cars': [{'code': code, 'game': FR2_GAME, 'label': 'candidate', 'vertices': entry['vertices'],
                  'headers': sorted(entry['headers'], key=lambda header: (header['index'], header['offset']))}
                 for code, entry in sorted(cars.items())],
        'claim_limits': ['A static decode and a content join, not a captured frame: the receipt marks the Handler rule '
                         'as conditional on runtime enable and context, so a Header here is eligible, not proven drawn.',
                         'Only the cars with an aligned pass-4 draw are listed; any other car or part renders unchanged.',
                         'The preview is capture-time GS memory at the sampled address (view-render-target-0), not the '
                         'post-render contents at the aligned draw. It is a stand-in for the sampled texture.',
                         'The eye position and the 3x3 matrix are not in the receipt; the inspector uses the camera as the '
                         'eye and a view-derived matrix, and labels the result candidate.'],
    }, preview_bytes


def build(root=ROOT, output=OUTPUT, preview_output=PREVIEW_OUTPUT, check=False):
    root, output, preview_output = Path(root), Path(output), Path(preview_output)
    need(output.resolve().parent == (root / 'dealership/public').resolve(), 'table output must stay under dealership/public')
    need(preview_output.resolve().parent == output.resolve().parent, 'preview output must stay beside the table')
    table, preview = derive((root / RECEIPT.relative_to(ROOT)).read_bytes(), (root / PREVIEW.relative_to(ROOT)).read_bytes())
    text_bytes = (json.dumps(table, indent=1, ensure_ascii=False) + '\n').encode()
    if check:
        need(output.is_file() and output.read_bytes() == text_bytes,
             'the pass-4 assignment table is stale; run python3 tools/build_pass4_assignments.py')
        need(preview_output.is_file() and preview_output.read_bytes() == preview,
             'the copied retained preview is stale; run python3 tools/build_pass4_assignments.py')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text_bytes)
        preview_output.write_bytes(preview)
    return table


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    try:
        result = build(check=arguments.check)
    except (DerivationError, OSError, KeyError) as error:
        sys.exit('PASS4 ASSIGNMENTS FAILED: ' + str(error))
    print('PASS pass-4 assignments: %d candidates on %s (%d Headers)'
          % (result['source']['pass4_draws'], ', '.join(car['code'] for car in result['cars']),
             sum(len(car['headers']) for car in result['cars'])))
