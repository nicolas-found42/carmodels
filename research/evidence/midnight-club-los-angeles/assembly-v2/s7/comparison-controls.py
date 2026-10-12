"""Scratch-only corruptions prove the corpus comparator rejects its material failure modes."""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path('tools').resolve()))
from bake_models import read_glb
from gt4_glb import Builder

import importlib.util
path = Path('.scratch/mcla-assembly-fix/s7-cleanup-independent/compare-corpus.py')
spec = importlib.util.spec_from_file_location('corpus_comparer', path)
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)

after = Path(sys.argv[1]).resolve()
assert len(sys.argv) == 3, 'pass accepted after GLB directory and a NEW control receipt directory'
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=False)
baseline = json.loads((compare.BASE/'before-manifest.json').read_text())['records']
target = after/(compare.TARGET_CODE+'.glb')
native_doc, blob = read_glb(target.read_bytes())
node_index = next(i for i, n in enumerate(native_doc['nodes']) if n['name'] == compare.TARGET_NODE)
primitive = native_doc['meshes'][native_doc['nodes'][node_index]['mesh']]['primitives'][1]
controls = []
expected_reason = {
    'unrelated_bytes': 'unrelated model bytes changed',
    'target_pose': compare.TARGET_NODE,
    'target_binding': compare.TARGET_NODE,
    'target_uv': 'non-position/normal target array changed',
    'target_uint16': 'preview triangle indices must be UInt32',
    'receipt_source': 'S7 repair receipt source SHA256 differs',
}
with tempfile.TemporaryDirectory(prefix='comparison-controls-', dir=compare.BASE) as folder:
    tmp = Path(folder)
    for row in baseline:
        (tmp/(row['code']+'.glb')).symlink_to(after/(row['code']+'.glb'))
    for name in ('unrelated_bytes', 'target_pose', 'target_binding', 'target_uv', 'target_uint16', 'receipt_source'):
        doc = copy.deepcopy(native_doc)
        binary = bytearray(blob)
        destination = tmp/(('va_350z_04' if name == 'unrelated_bytes' else compare.TARGET_CODE)+'.glb')
        destination.unlink()
        if name == 'unrelated_bytes':
            destination.write_bytes((after/'va_350z_04.glb').read_bytes()+b'TAMPER')
        else:
            if name == 'target_pose':
                doc['nodes'][node_index]['matrix'][12] += .001
            elif name == 'target_binding':
                doc['nodes'][node_index]['extras']['nativeBoneIndex'] = 99
            elif name == 'receipt_source':
                doc['extras']['preview_geometry_repairs'][0]['source_sha256'] = '0'*64
            elif name == 'target_uint16':
                doc['accessors'][primitive['indices']]['componentType'] = 5123
            elif name == 'target_uv':
                at = doc['accessors'][primitive['attributes']['TEXCOORD_0']]
                view = doc['bufferViews'][at['bufferView']]
                begin = view.get('byteOffset', 0)+at.get('byteOffset', 0)
                binary[begin] ^= 1
            builder = Builder()
            builder.doc, builder.blob = doc, binary
            destination.write_bytes(builder.finish())
        try:
            compare.compare(tmp, write_receipt=False)
        except AssertionError as error:
            assert expected_reason[name] in str(error), ('control failed for unintended reason', name, str(error))
            controls.append({'case': name, 'rejected': True, 'assertion': str(error),
                             'expected_reason': expected_reason[name], 'expected_reason_matched': True})
        else:
            raise AssertionError(('comparator accepted corruption', name))
        destination.unlink()
        destination.symlink_to(after/destination.name)
assert len(controls) == 6
(output/'comparison-controls.json').write_text(json.dumps(controls, indent=2)+'\n')
print('PASS six scratch-only corpus corruptions rejected:', ', '.join(r['case'] for r in controls))
