#!/usr/bin/env python3
"""Evaluate a library_filter implementation on frozen labeled cases against the real catalogs.

usage: eval_filter.py MODULE_PATH CASES.json OUT.json [--offline]
--offline uses a client that raises, measuring what works without SDK/key/provider.
"""
import concurrent.futures as cf, importlib.util, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
module_path, cases_path, out_path = sys.argv[1:4]
offline = '--offline' in sys.argv
spec = importlib.util.spec_from_file_location('impl', module_path)
impl = importlib.util.module_from_spec(spec); spec.loader.exec_module(impl)
catalogs = {'dealership': json.loads((ROOT / 'dealership/public/dealership/cars.json').read_text()),
            'source': json.loads((ROOT / 'dealership/public/models.json').read_text())['cars']}
cases = json.loads(Path(cases_path).read_text())

class Down:
    def system_one(self, **kw):
        raise RuntimeError('provider unavailable (offline evaluation)')
    def __enter__(self): return self
    def __exit__(self, *a): return False

def run(case):
    started = time.monotonic()
    if offline:
        receipt = impl.interpret(case['query'], catalogs[case['catalog']], Down(), catalog=case['catalog'])
    else:
        receipt = impl.live_interpret(case['query'], catalogs[case['catalog']], catalog=case['catalog'])
    return case, receipt, time.monotonic() - started

started = time.monotonic()
with cf.ThreadPoolExecutor(4) as pool:
    rows = list(pool.map(run, cases))
out, m = [], {'cases': len(rows), 'supported': 0, 'applied': 0, 'applied_correct': 0, 'wrongly_applied': 0,
              'supported_applied': 0, 'correct_action': 0, 'errors': 0, 'by_source': {},
              'input_tokens': 0, 'output_tokens': 0, 'cost': 0.0, 'provider_calls': 0}
for case, receipt, seconds in rows:
    exp = case['expected']
    filters = receipt.get('filters') if receipt.get('status') == 'ok' else None
    label = None
    if filters:
        label = filters['game'] if filters['game'] == 'all' or not filters.get('variant') else f"{filters['game']}:{filters['variant']}"
    supported = any(e != 'no_match' for e in exp)
    must_apply = 'no_match' not in exp
    applied = filters is not None
    correct = (label in exp) if applied else ('no_match' in exp)
    m['supported'] += must_apply
    m['applied'] += applied
    m['applied_correct'] += applied and label in exp
    m['wrongly_applied'] += applied and label not in exp
    m['supported_applied'] += must_apply and applied and label in exp
    m['correct_action'] += correct
    m['errors'] += receipt.get('status') == 'error'
    src = receipt.get('decided_by', 'model' if receipt.get('usage') else 'none')
    m['by_source'][src] = m['by_source'].get(src, 0) + 1
    usage = receipt.get('usage') or {}
    if usage:
        m['provider_calls'] += 1
        m['input_tokens'] += usage.get('input_tokens', 0); m['output_tokens'] += usage.get('output_tokens', 0)
        m['cost'] += usage.get('cost') or 0
    out.append({'id': case['id'], 'query': case['query'], 'catalog': case['catalog'], 'expected': exp,
                'status': receipt.get('status'), 'applied_label': label, 'correct_action': correct,
                'decided_by': src, 'signals': receipt.get('signals'), 'usage': usage or None,
                'message': receipt.get('message'), 'seconds': round(seconds, 4)})
m['elapsed_seconds'] = round(time.monotonic() - started, 3)
m['latency_max'] = max(r['seconds'] for r in out); m['latency_mean'] = round(sum(r['seconds'] for r in out) / len(out), 4)
Path(out_path).write_text(json.dumps({'module': module_path, 'cases_file': cases_path, 'offline': offline,
                                      'metrics': m, 'rows': out}, indent=1) + '\n')
print(json.dumps(m))
