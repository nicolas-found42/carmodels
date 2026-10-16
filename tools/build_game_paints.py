#!/usr/bin/env python3
"""Collect native paint values from the current source and editable GLBs, without changing them."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dealership/public/game-paints.json'


def glb_document(path):
    """Read bounded JSON only, checking container size before considering metadata."""
    with path.open('rb') as stream:
        header = stream.read(20)
        if len(header) != 20:
            raise ValueError('truncated paint GLB')
        magic, version, size, length, kind = struct.unpack('<5I', header)
        if (magic != 0x46546C67 or version != 2 or size != path.stat().st_size
                or kind != 0x4E4F534A or length % 4 or not 0 < length <= min(size - 20, 64 * 1024 * 1024)):
            raise ValueError('invalid paint GLB header')
        return json.loads(stream.read(length))


def collect(entries):
    colors, assets = {}, []
    for game, identity, path in sorted(entries, key=lambda row: (row[0], row[1])):
        doc = glb_document(path)
        data = doc.get('extras', {}).get('gamePaint')
        if data is None:
            continue
        if (not isinstance(data, dict) or data.get('schema') != 1
                or not isinstance(data.get('channels'), list) or not isinstance(data.get('colors'), list)):
            raise ValueError('invalid native paint metadata: ' + identity)
        # Pin the complete carrier, including textures and geometry, not a model-written description.
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assets.append({'game': game, 'file': identity, 'sha256': digest,
                       'channels': [channel['id'] for channel in data['channels']]})
        for value in data['colors']:
            if (not isinstance(value, dict)
                    or any(not isinstance(value.get(key), str) or not value[key].strip() for key in ('id', 'name', 'source'))
                    or not isinstance(value.get('rgb'), list) or len(value['rgb']) != 3
                    or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 1
                           for v in value['rgb'])):
                raise ValueError('invalid native paint colour: ' + identity)
            row = {key: value[key] for key in ('id', 'name', 'source', 'rgb')}
            row['game'] = game
            key = (game, value['source'], value['id'])
            if key in colors and colors[key] != row:
                raise ValueError('conflicting native paint identity: ' + repr(key))
            colors[key] = row
    return {'schema': 1, 'colors': [colors[key] for key in sorted(colors)], 'assets': assets}


def inputs(root=ROOT):
    root = Path(root)
    base = root / 'dealership'
    entries = []
    for row in json.loads((base / 'public/models.json').read_text())['cars']:
        name = row['file']
        if not name.endswith('.glb'):
            continue
        path = base / 'public' / name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(base.resolve()):
            raise ValueError('paint source path escapes catalog')
        entries.append((row['game'], 'public/' + name, path))
    for row in json.loads((base / 'dealership/catalog.json').read_text()):
        if row.get('displayMode') == 'native-package':
            continue
        code = row['code']
        if not code or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in code):
            raise ValueError('invalid paint dealership identity')
        path = base / 'dealership/models' / (code + '.glb')
        entries.append((row.get('game', 'ford-racing-2'), 'dealership/models/' + code + '.glb', path))
    return entries


def build(root=ROOT, output=OUTPUT, check=False):
    root, output = Path(root), Path(output)
    destination = output.resolve()
    public = (root / 'dealership/public').resolve()
    protected = [(root / name).resolve() for name in ('games', 'dealership/dealership')]
    if (any(destination == path or destination.is_relative_to(path) for path in protected)
            or destination.is_relative_to(public) and destination != public / 'game-paints.json'):
        raise ValueError('paint output must not replace source or editable inputs')
    result = collect(inputs(root))
    text = json.dumps(result, indent=1, ensure_ascii=False) + '\n'
    if check:
        if not output.is_file() or output.read_text() != text:
            raise ValueError('Game paint library is stale; run python3 tools/build_game_paints.py')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + '.tmp')
        try:
            temporary.write_text(text)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        result = build(check=args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print(f'PASS game paint library: {len(result["colors"])} source-backed colours, {len(result["assets"])} carriers')
