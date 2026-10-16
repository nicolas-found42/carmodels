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
from import_mc3_catalogs import (GAME, LIMITS as NATIVE_LIMITS, PROFILE as NATIVE_PROFILE,
                                 native_model, regular, source_package)
from mc3_model import PROFILE, sha


def preview_data(row, source):
    """Validate one converter output before either showcase imports it."""
    code = row.get('code')
    if (not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code)
            or row.get('file') != code+'.glb' or row.get('source_profile') != PROFILE):
        raise ValueError('invalid preview identity/profile')
    path = Path(source)/row['file']
    regular(path)
    data = path.read_bytes()
    if len(data) != row['bytes'] or sha(data) != row['sha256']:
        raise ValueError('preview hash/size differs')
    doc, _ = read_glb(data)
    if doc.get('extras', {}).get('car') != code or doc['extras'].get('source_profile') != PROFILE:
        raise ValueError('preview GLB identity/profile differs')
    if doc['extras'].get('records') != row.get('records'):
        raise ValueError('preview records differ from GLB')
    if (type(row.get('triangle_count')) is not int or row['triangle_count'] <= 0
            or bake_car('MC3_'+code.upper(), data, source_mode=False)['triangleCount'] != row['triangle_count']):
        raise ValueError('preview triangle declaration differs')
    limits = row.get('claim_limits')
    if not isinstance(limits, list) or any(not isinstance(value, str) for value in limits):
        raise ValueError('preview claim limits invalid')
    return data


def source_preview(row, source):
    """Validate a source GLB and its separately retained original DAT."""
    code, package = row.get('code'), row.get('native_package')
    conversion = row.get('preview_conversion')
    if (not isinstance(code, str) or not re.fullmatch(r'vp_[a-z0-9_]+', code)
            or row.get('file') != f'previews/{code}.glb' or row.get('asset_kind') != 'glb'
            or row.get('source_profile') != PROFILE or row.get('source_variant') != 'native'
            or row.get('display_name') != code or not isinstance(package, dict)
            or package.get('profile') != NATIVE_PROFILE or not isinstance(conversion, dict)):
        raise ValueError('invalid MC3 source preview identity/profile')
    native = dict(code=code, file=package.get('file'), bytes=package.get('bytes'),
                  sha256=package.get('sha256'), records=[], display_name=code,
                  source_profile=package['profile'], source_variant='native',
                  asset_kind='native-package', native_members=package.get('members'), claim_limits=NATIVE_LIMITS)
    source_package(native, source)
    expected = {**conversion, 'file': code+'.glb'}
    for key in ('code', 'bytes', 'sha256', 'records', 'claim_limits', 'source_profile'):
        if row.get(key) != conversion.get(key):
            if key == 'records':
                raise ValueError('source preview records differ from conversion')
            if key in ('sha256', 'bytes'):
                raise ValueError('source preview hash/size differs from conversion')
            raise ValueError('source preview metadata differs from conversion')
    # The preview lives in a child directory; converter filenames remain flat.
    return preview_data(expected, Path(source)/'previews')


def publish_source_previews(source=DEFAULT, destination=ROOT/'dealership/public'/GAME, refresh=False):
    """Publish conversions while retaining every native DAT byte and source identity.

    Validate the complete current edition before staging any replacement. An
    existing changed GLB is rejected, and replacement of a verified prior
    conversion requires an explicit refresh. Editable dealership files are not
    inputs or outputs of this operation.
    """
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if (source.resolve().is_relative_to(destination.resolve())
            or destination.resolve().is_relative_to(source.resolve())):
        raise ValueError('source previews and public destination must be separate')
    for path in (source, source/'index.json', destination, destination/'index.json', destination/'previews'):
        regular(path)
    index_path = destination/'index.json'
    current = json.loads(index_path.read_text())
    rows = json.loads((source/'index.json').read_text())['cars']
    codes = [row['code'] for row in rows]
    previous = {row['code']: row for row in current['cars']}
    if (not codes or len(codes) != len(set(codes)) or len(previous) != len(current['cars'])
            or set(previous) != set(codes)):
        raise ValueError('source preview vehicle coverage differs')
    payloads, published = [], []
    for row in rows:
        data = preview_data(row, source)
        code = row['code']
        old = previous[code]
        if old.get('asset_kind') == 'native-package':
            source_package(old, destination)
            package = {'file': old['file'], 'bytes': old['bytes'], 'sha256': old['sha256'],
                       'members': old['native_members'], 'profile': old['source_profile']}
        else:
            source_preview(old, destination)
            package = copy.deepcopy(old['native_package'])
        target = destination/'previews'/f'{code}.glb'
        regular(target)
        existing = target.read_bytes() if target.exists() else None
        updated = dict(code=code, file=f'previews/{code}.glb', bytes=len(data), sha256=sha(data),
                       records=row['records'], display_name=code, source_profile=PROFILE,
                       source_variant='native', asset_kind='glb', claim_limits=row['claim_limits'],
                       native_package=package, preview_conversion=copy.deepcopy(row))
        if old == updated and existing == data:
            published.append(old)
            continue
        if old.get('asset_kind') == 'glb' and not refresh:
            raise ValueError('existing source preview differs; explicit refresh required')
        if old.get('asset_kind') != 'glb' and existing is not None:
            raise ValueError('uncatalogued source preview already exists')
        published.append(updated)
        payloads.append((target, data, existing))
    if not payloads:
        return 0
    before = index_path.read_bytes()
    previews_existed = (destination/'previews').exists()
    with tempfile.TemporaryDirectory(prefix='.mc3-source-previews-', dir=destination.parent) as temp:
        stage = Path(temp)
        for target, data, _ in payloads:
            (stage/target.name).write_bytes(data)
        # Index-level native-only prose must not contradict converted rows.
        updated_index = {**current, 'cars': published}
        updated_index.pop('claim_limits', None)
        (stage/'index.json').write_text(json.dumps(updated_index, indent=1)+'\n')
        (destination/'previews').mkdir(exist_ok=True)
        moved = []
        try:
            for target, _, existing in payloads:
                (stage/target.name).replace(target)
                moved.append((target, existing))
            (stage/'index.json').replace(index_path)
        except BaseException:
            index_path.write_bytes(before)
            for target, existing in moved:
                if existing is None:
                    target.unlink()
                else:
                    target.write_bytes(existing)
            if not previews_existed:
                (destination/'previews').rmdir()
            raise
    return len(payloads)


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
        path = source/row['file']
        data = preview_data(row, source)
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
    p.add_argument('--publish-source', type=Path, help='Publish source showcase GLBs here while retaining its native DATs')
    p.add_argument('--refresh-source', action='store_true', help='Replace only a validated prior source preview edition')
    a = p.parse_args()
    if a.publish_source:
        print(f'Published {publish_source_previews(a.source, a.publish_source, a.refresh_source)} MC3 source previews; native DATs retained')
    else:
        if a.refresh_source:
            p.error('--refresh-source requires --publish-source')
        print(f'Imported {import_previews(a.source, a.destination, a.refresh_unedited)} independent MC3 dealership previews')
