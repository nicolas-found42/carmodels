#!/usr/bin/env python3
"""Upgrade existing native MC3 dealer identities with independent editable previews."""
import argparse
import copy
import json
from pathlib import Path
import re
import tempfile

from bake_models import ROOT, bake_car, read_glb
from export_mc3_models import DEFAULT
from import_mc3_catalogs import GAME, LIMITS as NATIVE_LIMITS, native_model, regular
from mc3_model import PROFILE, sha


def import_previews(source=DEFAULT, destination=ROOT/'dealership/dealership', refresh_unedited=False):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if source.resolve().is_relative_to(destination.resolve()) or destination.resolve().is_relative_to(source.resolve()):
        raise ValueError('source previews and editable destination must be separate')
    regular(source);regular(destination)
    catalog_path, origins_path = destination/'catalog.json', destination/'origins.json'
    regular(catalog_path);regular(origins_path);regular(destination/'models')
    catalog = json.loads(catalog_path.read_text());origins = json.loads(origins_path.read_text())
    existing = {e['code']: e for e in catalog}
    provenance = {e['code']: e for e in origins['cars']}
    if len(existing) != len(catalog) or len(provenance) != len(origins['cars']):
        raise ValueError('dealership identities duplicated')
    regular(source/'index.json')
    rows = json.loads((source/'index.json').read_text())['cars']
    if not isinstance(rows, list) or not rows:
        raise ValueError('preview index empty')
    seen, payloads = set(), []
    for row in rows:
        identifier = row['code']
        if (not re.fullmatch(r'vp_[a-z0-9_]+', identifier) or row['file'] != identifier+'.glb'
                or row['source_profile'] != PROFILE or identifier in seen):
            raise ValueError('invalid preview identity/profile')
        seen.add(identifier)
        path = source/row['file'];regular(path)
        data = path.read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('preview hash/size differs')
        doc, _ = read_glb(data)
        if doc.get('extras', {}).get('car') != identifier or doc['extras'].get('source_profile') != PROFILE:
            raise ValueError('preview GLB identity/profile differs')
        baked = bake_car('MC3_'+identifier.upper(), data, source_mode=False)
        if baked['triangleCount'] != row['triangle_count'] or not row['triangle_count']:
            raise ValueError('preview triangle declaration differs')
        code = 'MC3_'+identifier.upper()
        old = existing.get(code);origin = provenance.get(code)
        if not old or old.get('game') != GAME or old.get('sourceCode') != identifier or not origin:
            raise ValueError('preview requires matching existing native dealership identity')
        native_model({**old, 'displayMode': 'native-package'}, destination)
        initial = origin['initialSource']
        if initial.get('code') != identifier or initial.get('sha256') != old['nativePackage']['sha256']:
            raise ValueError('native source provenance differs')
        target = destination/'models'/f'{code}.glb';regular(target)
        previous = target.read_bytes() if target.exists() else None
        if previous is not None:
            latest = origin.get('latestSource', {})
            if latest.get('profile') != PROFILE or latest.get('code') != identifier:
                raise ValueError('existing model lacks matching preview provenance')
            # Updates are opt-in and only replace a byte-identical imported copy.
            if not refresh_unedited or sha(previous) != latest.get('sha256'):
                continue
        elif old.get('displayMode') != 'native-package':
            raise ValueError('converted dealership model is missing')
        limits = row['claim_limits']
        if not isinstance(limits, list) or any(not isinstance(x, str) for x in limits):
            raise ValueError('preview claim limits invalid')
        former_limits = origin.get('previewConversion', {}).get('claim_limits', [])
        standard = [*NATIVE_LIMITS, *former_limits, 'Independent editable preview; original native package retained.']
        custom = [x for x in old.get('claimLimits', []) if x not in standard]
        old.update(displayMode='textured-glb', claimLimits=list(dict.fromkeys([
            'Independent editable preview; original native package retained.', *limits, *custom])))
        latest = {'game': GAME, 'code': identifier, 'glb': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else row['file'],
                                  'sha256': row['sha256'], 'profile': PROFILE}
        if previous == data and origin.get('latestSource') == latest and origin.get('previewConversion') == row:
            continue
        origin['latestSource'] = latest
        origin['previewConversion'] = copy.deepcopy(row)
        payloads.append((target, data, previous))
    if not payloads:
        return 0
    before_catalog, before_origins = catalog_path.read_bytes(), origins_path.read_bytes()
    destination.joinpath('models').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.mc3-preview-import-', dir=destination.parent) as temp:
        stage = Path(temp)
        for target, data, _ in payloads:
            (stage/target.name).write_bytes(data)
        (stage/'catalog.json').write_text(json.dumps(catalog, indent=1)+'\n')
        (stage/'origins.json').write_text(json.dumps(origins, indent=1)+'\n')
        moved = []
        try:
            for target, _, previous in payloads:
                (stage/target.name).replace(target);moved.append((target, previous))
            (stage/'origins.json').replace(origins_path)
            (stage/'catalog.json').replace(catalog_path)
        except BaseException:
            catalog_path.write_bytes(before_catalog);origins_path.write_bytes(before_origins)
            for target, previous in moved:
                if previous is None:
                    target.unlink()
                else:
                    target.write_bytes(previous)
            raise
    return len(payloads)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=DEFAULT)
    p.add_argument('--destination', type=Path, default=ROOT/'dealership/dealership')
    p.add_argument('--refresh-unedited', action='store_true', help='Refresh only copies matching their recorded import hash; preserve edited models')
    a = p.parse_args()
    print(f'Imported {import_previews(a.source, a.destination, a.refresh_unedited)} independent MC3 dealership previews')
