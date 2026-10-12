"""Independent exact checks over final Jev Browser capture manifests and image bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument('--phase', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists(), 'Preserve earlier evidence'
base = Path('.scratch/mcla-assembly-fix')
source_path = Path('dealership/public/midnight-club-los-angeles/index.json')
dealer_path = Path('dealership/public/dealership/cars.json')
source = {r['code']: r for r in json.loads(source_path.read_text())['cars']}
dealer = {r['code']: r for r in json.loads(dealer_path.read_text())
          if r.get('game') == 'midnight-club-los-angeles'}
expected = set(source)
assert len(expected) == len(dealer) == 106
result = {'assertion_script_sha256': sha(__file__), 'phase': args.phase,
          'expected_native_catalog_codes': sorted(expected), 'views': {}}
for view in ('source', 'dealership'):
    directory = base / (args.phase + '-' + view)
    capture_path = directory / 'capture.json'
    capture = json.loads(capture_path.read_text())
    records = capture['records']
    assert not capture['failures']
    assert len(records) == 106 and len({r['code'] for r in records}) == 106
    assert {r['code'] for r in records} == expected
    assert len({r[k] for r in records for k in ('rear', 'front')}) == 212
    assert capture['source_index_sha256'] == sha(source_path)
    assert capture['dealership_catalog_sha256'] == sha(dealer_path)
    for file, digest in capture['viewerPins'].items():
        assert sha(Path('dealership') / file) == digest
    verified = []
    for r in records:
        src = source[r['code']]
        ds = dealer['MCLA_' + r['code'].upper()]
        src_file = Path('dealership/public/midnight-club-los-angeles') / src['file']
        ds_file = Path('dealership') / ds['model']['source']['glb']
        digest = sha(src_file)
        assert src_file.read_bytes() == ds_file.read_bytes()
        assert digest == src['sha256'] == ds['model']['source']['sha256']
        assert digest == r['sourceHash'] == r['dealerHash'] == r['network']['sha256']
        assert r['network']['status'] == 200
        readback = r['readback']
        assert not readback['error'] and not r['pageErrors']
        assert r['depthBits'] == 24 and 'Metal' in r['renderer']
        expected_id = ('midnight-club-los-angeles/' + r['code'] if view == 'source'
                       else 'MCLA_' + r['code'].upper())
        assert readback['id'] == expected_id
        if view == 'source':
            assert readback['status'].startswith(r['code'] + ' · Scene 0')
            assert readback['download'].endswith('/' + r['code'] + '.glb')
        else:
            assert readback['status'] == 'loaded' and readback['autoRotate'] is False
            assert readback['download'].endswith('/MCLA_' + r['code'].upper() + '.glb')
        images = []
        for key in ('rear', 'front'):
            file = Path(r[key])
            data = file.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n'
            width, height = struct.unpack('>II', data[16:24])
            assert width > 500 and height > 500
            images.append({'file': str(file), 'sha256': sha(file), 'bytes': len(data),
                           'width': width, 'height': height})
        verified.append({'code': r['code'], 'selected_id': expected_id,
                         'glb_sha256': digest, 'network_status': 200,
                         'viewer_error': '', 'page_errors': [],
                         'depth_bits': 24, 'renderer': r['renderer'], 'images': images})
    result['views'][view] = {'capture_sha256': sha(capture_path),
                            'viewer_pins': capture['viewerPins'],
                            'catalog_pins': {'source': sha(source_path), 'dealership': sha(dealer_path)},
                            'unique_models': 106, 'verified_image_count': 212,
                            'all_assertions_passed': True, 'records': verified}
assert {r['code']: r['glb_sha256'] for r in result['views']['source']['records']} == {
    r['code']: r['glb_sha256'] for r in result['views']['dealership']['records']}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print('ASSERTIONS PASS: 106 unique source IDs; 106 unique dealership IDs; '
      '212 loaded model/page records; 424 distinct image files with PNG headers, dimensions and hashes; '
      'every actual source, dealership, catalog and HTTP-response GLB hash equal; '
      'zero recorded viewer/page errors; current catalog and viewer pins; Metal backend and 24 depth bits.')
