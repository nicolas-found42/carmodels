"""Prepare bounded raw-patch reviews and separate evidence-verification batches; record escalation."""
import argparse
import difflib
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(root, paths):
    files = {}
    for name in paths:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Review paths must be relative to the repository')
        target = Path(root) / path
        files[str(path)] = target.read_text() if target.exists() else None
    return {'schema': 1, 'files': files}


def raw_diffs(baseline, root):
    if baseline.get('schema') != 1 or not baseline.get('files'):
        raise ValueError('Invalid or empty review baseline')
    before = baseline['files']
    after = snapshot(root, list(before))['files']
    # Detect renames within the explicit task scope, including originally untracked files.
    deleted = [n for n in before if before[n] is not None and after[n] is None]
    added = [n for n in before if before[n] is None and after[n] is not None]
    renames = {}
    for old in deleted:
        candidates = [(difflib.SequenceMatcher(None, before[old], after[new]).ratio(), new) for new in added]
        if candidates:
            score, new = max(candidates)
            if score > 0.6:
                renames[old] = new
                added.remove(new)
    diffs = []
    for old in sorted(before):
        if old in renames.values():
            continue
        new = renames.get(old, old)
        text = ''.join(difflib.unified_diff((before[old] or '').splitlines(True), (after[new] or '').splitlines(True),
                       fromfile='a/' + old if before[old] is not None else '/dev/null',
                       tofile='b/' + new if after[new] is not None else '/dev/null'))
        if text:
            diffs.append(text)
    return diffs


def prepare(baseline, root, request, checks_dir, claims, output, max_diff_chars=24000):
    if not 1000 <= max_diff_chars <= 50000:
        raise ValueError('Diff cap must be between 1000 and 50000 characters')
    if not request.strip() or len(request) > 4000:
        raise ValueError('Request must be nonempty and at most 4000 characters')
    if any(not c.strip() or len(c) > 2000 for c in claims):
        raise ValueError('Each claim must be nonempty and at most 2000 characters')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('Review output must be empty; previous judgments are preserved')
    groups, current = [], ''
    for diff in raw_diffs(baseline, root):
        if len(diff) > max_diff_chars:
            raise ValueError('A raw file diff exceeds the cap; narrow the change, never truncate hunks')
        if current and len(current) + len(diff) > max_diff_chars:
            groups.append(current); current = ''
        current += diff
    if current:
        groups.append(current)
    if not groups:
        raise ValueError('No patch changes in the review scope')
    checks_dir = Path(checks_dir)
    receipt = json.loads((checks_dir / 'results.json').read_text())
    if receipt.get('schema') != 1 or not receipt.get('checks'):
        raise ValueError('Invalid or empty check manifest')
    evidence = [{'id': 'check-manifest', 'text': json.dumps(receipt, indent=2)}]
    # Full logs are independent of the exit summary. Bundle them without dropping their tails.
    logs = []
    for row in receipt['checks']:
        log = Path(row['log'])
        if log.is_absolute() or '..' in log.parts:
            raise ValueError('Check log must belong to the evidence directory')
        logs.append(f"COMMAND {row['command']}\nSTATUS {row['status']} EXIT {row['exit_code']}\n" + (checks_dir / log).read_text())
    evidence.append({'id': 'full-check-logs', 'text': '\n'.join(logs)})
    if sum(len(e['text']) for e in evidence) > 190000:
        raise ValueError('Evidence exceeds the budget; select a relevant check subset')
    summary = json.dumps(receipt)
    calls = [{'tool': 'jev_review', 'args': {'request': request, 'diff': diff, 'tests': summary},
              'out': str(output / f'review-{i:03}.json')} for i, diff in enumerate(groups, 1)]
    for i in range(0, len(claims), 2):
        calls.append({'tool': 'jev_verify', 'args': {'claims': claims[i:i + 2], 'evidence': evidence},
                      'out': str(output / f'verify-{i // 2 + 1:03}.json')})
    bundle = {'schema': 1, 'bundle_sha256': digest(calls), 'paths': sorted(baseline['files']),
              'calls': calls, 'policy': 'Every patch review and evidence claim must be resolved; verification never approves a patch.',
              'claim_limits': ['Explicit text-file task scope only; binaries/generated assets need separate checks.',
                               'Preparing this bundle does not call Jev or approve changes.']}
    (output / 'calls.json').write_text(json.dumps(calls, indent=2) + '\n')
    (output / 'bundle.json').write_text(json.dumps(bundle, indent=2) + '\n')
    return bundle


def unwrap(value):
    value = value.get('result', value)
    if value.get('isError') or 'error' in value:
        raise ValueError('Judge operational failure')
    if 'content' in value:
        value = json.loads(value['content'][0]['text'])
    return value


def probability(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def review_status(bundle, implementer, resolution=None):
    if digest(bundle['calls']) != bundle['bundle_sha256']:
        raise ValueError('Review bundle digest differs')
    unresolved, blocked = [], []
    for call in bundle['calls']:
        path = Path(call['out'])
        try:
            receipt = json.loads(path.read_text())
            if receipt.get('args') != call['args']:
                raise ValueError('Judge receipt arguments differ from this bundle')
            result = unwrap(receipt)
            if result.get('tool') != call['tool'] or result.get('action') not in ['auto', 'review', 'escalate']:
                raise ValueError('Unknown or malformed judge result')
            if call['tool'] == 'jev_verify':
                results = result.get('results', [])
                if len(results) != len(call['args']['claims']) or any(r.get('claim') != c or r.get('verdict') not in ['verified', 'unsupported', 'contradicted'] for r, c in zip(results, call['args']['claims'])):
                    raise ValueError('Verification results do not account for every claim')
                if result['action'] == 'auto' and any(r.get('verdict') != 'verified' or r.get('action') != 'auto' for r in results):
                    raise ValueError('Auto verification contains unresolved claims')
                if any(not probability(r.get('confidence')) for r in results):
                    raise ValueError('Verification confidence is missing or invalid')
            else:
                scores = result.get('scores', {})
                if not probability(result.get('safe_to_apply')) or set(scores) != {'correctness', 'spec_match', 'test_gap', 'blast_radius'} or any(not probability(s.get('confidence')) for s in scores.values()):
                    raise ValueError('Patch review scores are missing or invalid')
            if any(r.get('verdict') == 'contradicted' for r in result.get('results', [])):
                blocked.append(str(path))
            elif result['action'] != 'auto':
                unresolved.append({'receipt': str(path), 'action': result['action'],
                                   'scores': result.get('scores'), 'safe_to_apply': result.get('safe_to_apply')})
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            blocked.append(str(path))
    if resolution:
        if resolution.get('bundle_sha256') != bundle['bundle_sha256'] or not resolution.get('reviewer') or resolution['reviewer'] == implementer or not resolution.get('rationale'):
            raise ValueError('Resolution requires an independent reviewer, matching bundle digest and rationale')
        if resolution.get('verdict') == 'approve' and not blocked:
            unresolved = []
    return {'status': 'blocked' if blocked else 'needs_independent_review' if unresolved else 'accepted',
            'blocked': blocked, 'unresolved': unresolved,
            'claim_limits': ['Resolution records a reviewer decision; it is not identity authentication.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    snap = sub.add_parser('snapshot')
    snap.add_argument('--paths', nargs='+', required=True)
    snap.add_argument('--output', type=Path, required=True)
    build = sub.add_parser('build')
    build.add_argument('--baseline', type=Path, required=True)
    build.add_argument('--request-file', type=Path, required=True)
    build.add_argument('--checks-dir', type=Path, required=True)
    build.add_argument('--claim', action='append', default=[])
    build.add_argument('--output-dir', type=Path, required=True)
    build.add_argument('--max-diff-chars', type=int, default=24000)
    status = sub.add_parser('status')
    status.add_argument('--bundle', type=Path, required=True)
    status.add_argument('--implementer', required=True)
    status.add_argument('--resolution', type=Path)
    args = parser.parse_args()
    try:
        if args.mode == 'snapshot':
            value = snapshot(ROOT, args.paths)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x') as stream:
                stream.write(json.dumps(value, indent=2) + '\n')
        elif args.mode == 'build':
            value = prepare(json.loads(args.baseline.read_text()), ROOT, args.request_file.read_text(), args.checks_dir,
                            args.claim, args.output_dir, args.max_diff_chars)
            print(f"Prepared {len(value['calls'])} bounded calls; bundle {value['bundle_sha256']}")
        else:
            resolution = json.loads(args.resolution.read_text()) if args.resolution else None
            value = review_status(json.loads(args.bundle.read_text()), args.implementer, resolution)
            print(json.dumps(value, indent=2))
            return 0 if value['status'] == 'accepted' else 2
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
