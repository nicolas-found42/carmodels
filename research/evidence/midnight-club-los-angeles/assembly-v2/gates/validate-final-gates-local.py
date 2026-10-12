import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, 'tools')
from review_payload import digest, unwrap

BASE = Path('.scratch/mcla-assembly-fix/final-gates')
AUTHORS = {'decoder-valid-input': 'decoder_fix', 'camera': 'root', 'exporter': 'root',
           'helper-bounded-evidence': 'catalog_upgrade', 'refresh': 'catalog_upgrade', 'documentation': 'root'}
records = []
for name, author in AUTHORS.items():
    folder = BASE / name
    bundle = json.loads((folder / 'bundle.json').read_text())
    assert digest(bundle['calls']) == bundle['bundle_sha256'], ('bundle changed', name)
    for file, sha in bundle['file_pins'].items():
        assert hashlib.sha256(Path(file).read_bytes()).hexdigest() == sha, ('stale product', name, file)
    receipt = json.loads((folder / 'gate.json').read_text())
    assert len(bundle['calls']) == 1 and bundle['calls'][0]['tool'] == 'jev_gate', ('invalid call scope', name)
    args = bundle['calls'][0]['args']
    assert receipt['args'] == args, ('receipt args differ from bundle', name)
    gate = unwrap(receipt)
    assert gate['tool'] == 'jev_gate', ('wrong judgment tool', name)
    assert gate['action'] in ['auto', 'review', 'escalate'], ('invalid gate action', name)
    assert gate['review']['action'] in ['auto', 'review', 'escalate'], ('invalid review action', name)
    assert [x['path'] for x in gate['review']['files']] == [x['path'] for x in args['files']], ('review file coverage differs', name)
    assert [x['claim'] for x in gate['verification']['results']] == args['claims'], ('claim coverage differs', name)
    assert gate['verification']['summary']['verified'] == len(args['claims']), ('claim count differs', name)
    for row in gate['review']['files']:
        assert math.isfinite(row['safe_to_apply']) and 0 <= row['safe_to_apply'] <= 1, ('invalid safety probability', name)
        for rubric in row['scores'].values():
            assert math.isfinite(rubric['confidence']) and 0 <= rubric['confidence'] <= 1, ('invalid rubric confidence', name)
            assert all(math.isfinite(x) and 0 <= x <= 1 for x in rubric['probabilities'].values()), ('invalid rubric distribution', name)
    for claim in gate['verification']['results']:
        assert claim['action'] in ['auto', 'review', 'escalate'], ('invalid claim action', name)
        assert math.isfinite(claim['confidence']) and 0 <= claim['confidence'] <= 1, ('invalid claim confidence', name)
        assert all(math.isfinite(x) and 0 <= x <= 1 for x in claim['probabilities'].values()), ('invalid claim distribution', name)
    assert not gate.get('truncated'), ('truncated judgment input', name)
    summary = gate['verification']['summary']
    assert summary['contradicted'] == summary['unsupported'] == summary['invalid_response'] == 0, ('blocked verification', name, summary)
    assert all(c['verdict'] == 'verified' for c in gate['verification']['results']), ('claim is not verified', name)
    resolution = json.loads((folder / 'independent-resolution.json').read_text())
    assert resolution['bundle_sha256'] == bundle['bundle_sha256'] and resolution['verdict'] == 'approve', ('unresolved review', name)
    assert not resolution['reviewer'].startswith(author), ('implementer resolved own review', name)
    assert resolution.get('rationale'), ('missing rationale', name)
    records.append({'scope': name, 'bundle_sha256': bundle['bundle_sha256'], 'original_action': gate['action'],
                    'composite': gate['review']['composite'], 'safe_to_apply': gate['review']['safe_to_apply'],
                    'verification': gate['verification'], 'usage': gate.get('usage'),
                    'independent_reviewer': resolution['reviewer'], 'disposition': 'accepted by bound independent review',
                    'gate_sha256': hashlib.sha256((folder/'gate.json').read_bytes()).hexdigest(),
                    'resolution_sha256': hashlib.sha256((folder/'independent-resolution.json').read_bytes()).hexdigest()})
result = {'scopes': records, 'status': 'accepted', 'claim_limits': ['No original Jev escalation or scores were replaced.', 'Operational decoder/helper input failures and the prior contradicted capture claim are excluded from accepted completion claims, with original receipts retained.', 'Generated assets are separately verified by executable source/corpus/preservation/browser hash assertions.']}
(BASE/'final-disposition.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS six complete final raw-diff scopes; current file pins; verified claims; independently resolved valid review escalations.')
