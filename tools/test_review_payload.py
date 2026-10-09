"""Raw rename/untracked diffs, budget controls and fail-closed review resolution."""
import json
from pathlib import Path
import tempfile
import unittest

from review_payload import digest, prepare, raw_diffs, review_status, snapshot


class ReviewPayloadTests(unittest.TestCase):
    def test_raw_scope_and_bounded_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'old.py').write_text('def f():\n    return 1\n')
            baseline = snapshot(root, ['old.py', 'new.py', 'untracked.py'])
            (root / 'old.py').rename(root / 'new.py')
            (root / 'new.py').write_text('def f():\n    return 2\n')
            (root / 'untracked.py').write_text('print("new")\n')
            diffs = raw_diffs(baseline, root)
            self.assertTrue(any('--- a/old.py\n+++ b/new.py' in d and '-    return 1' in d for d in diffs))
            self.assertTrue(any('+++ b/untracked.py' in d for d in diffs))
            checks = root / 'checks'; checks.mkdir()
            (checks / 'test.log').write_text('full beginning\nfull ending\n')
            (checks / 'results.json').write_text(json.dumps({'schema': 1, 'exit_code': 0, 'checks':
                [{'name': 'test', 'command': ['test'], 'status': 'pass', 'exit_code': 0, 'log': 'test.log'}]}))
            bundle = prepare(baseline, root, 'Change return and add file', checks, ['one', 'two', 'three'], root / 'review')
            self.assertEqual([c['tool'] for c in bundle['calls']], ['jev_review', 'jev_verify', 'jev_verify'])
            self.assertIn('full beginning\nfull ending', bundle['calls'][1]['args']['evidence'][1]['text'])
            self.assertEqual(review_status(bundle, 'implementer')['status'], 'blocked', 'missing receipts cannot pass')
            with self.assertRaisesRegex(ValueError, 'previous judgments'):
                prepare(baseline, root, 'request', checks, [], root / 'review')
            (root / 'untracked.py').write_text('x' * 2000)
            with self.assertRaisesRegex(ValueError, 'never truncate'):
                prepare(baseline, root, 'request', checks, [], root / 'too-big', max_diff_chars=1000)

    def test_escalation_requires_independent_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'review.json'
            calls = [{'tool': 'jev_review', 'args': {}, 'out': str(path)}]
            bundle = {'calls': calls, 'bundle_sha256': digest(calls)}
            result = {'tool': 'jev_review', 'action': 'escalate', 'safe_to_apply': 0.58,
                      'scores': {k: {'score': 1, 'confidence': 0.3} for k in ['correctness', 'spec_match', 'test_gap', 'blast_radius']}}
            path.write_text(json.dumps({'args': {}, 'result': result}))
            self.assertEqual(review_status(bundle, 'author')['status'], 'needs_independent_review')
            resolution = {'bundle_sha256': bundle['bundle_sha256'], 'reviewer': 'author', 'verdict': 'approve', 'rationale': 'reviewed'}
            with self.assertRaisesRegex(ValueError, 'independent'):
                review_status(bundle, 'author', resolution)
            resolution['reviewer'] = 'another-reviewer'
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'accepted')
            path.write_text(json.dumps({'args': {'different_request': True}, 'result': result}))
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked', 'stale receipts cannot resolve this bundle')
            path.write_text(json.dumps({'tool': 'jev_review', 'action': 'auto'}))
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked', 'malformed scores cannot be approved')
            result['safe_to_apply'] = float('nan')
            path.write_text(json.dumps({'args': {}, 'result': result}))
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked')
            path.write_text(json.dumps({'isError': True, 'content': [{'text': 'max_tokens_exceeded'}]}))
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked')

    def test_actual_per_claim_verify_output_and_invalid_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'verify.json'
            calls = [{'tool': 'jev_verify', 'args': {'claims': ['claim']}, 'out': str(path)}]
            bundle = {'calls': calls, 'bundle_sha256': digest(calls)}
            result = {'tool': 'jev_verify', 'results': [
                {'claim': 'claim', 'verdict': 'verified', 'confidence': 0.76, 'action': 'review'}]}
            def save():
                path.write_text(json.dumps({'args': calls[0]['args'], 'result': result}))
            save()
            self.assertEqual(review_status(bundle, 'author')['status'], 'needs_independent_review')
            resolution = {'bundle_sha256': bundle['bundle_sha256'], 'reviewer': 'reviewer',
                          'verdict': 'approve', 'rationale': 'independently verified'}
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'accepted')
            result['results'][0].update(confidence=0.99, action='auto')
            save()
            self.assertEqual(review_status(bundle, 'author')['status'], 'accepted')
            for change in [{'verdict': 'contradicted'}, {'action': 'unknown'}, {'confidence': -1}, {'claim': 'other'}]:
                original = dict(result['results'][0])
                result['results'][0].update(change)
                save()
                self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked')
                result['results'][0] = original
            del result['results'][0]['action']
            save()
            self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked')

    def test_contradicted_or_missing_claims_block_even_with_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'verify.json'
            calls = [{'tool': 'jev_verify', 'args': {'claims': ['claim']}, 'out': str(path)}]
            bundle = {'calls': calls, 'bundle_sha256': digest(calls)}
            resolution = {'bundle_sha256': bundle['bundle_sha256'], 'reviewer': 'reviewer', 'verdict': 'approve', 'rationale': 'reviewed'}
            for results in [[], [{'claim': 'claim', 'verdict': 'contradicted', 'action': 'auto', 'confidence': 1}]]:
                path.write_text(json.dumps({'args': calls[0]['args'], 'result': {'tool': 'jev_verify', 'action': 'auto', 'results': results}}))
                self.assertEqual(review_status(bundle, 'author', resolution)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
