"""Stranding detection: dirty worktrees whose branch tip already reached the base branch."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_stranded_worktrees as subject


class StrandedTests(unittest.TestCase):
    def entries(self):
        return [(Path('/tmp/agent-worktree'), 'feature/old-worktree'),
                (Path('/tmp/another'), 'feature/active')]

    def test_dirty_merged_worktree_without_pull_request_is_reported_as_hidden(self):
        findings = subject.stranded(self.entries(), Path('/repo'), prs=lambda b, r: [],
                                    is_dirty=lambda p: True, is_merged=lambda b, r, base: True)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f['hidden'] for f in findings))
        self.assertEqual(findings[0]['branch'], 'feature/old-worktree')
        self.assertEqual(findings[0]['pullRequests'], [])

    def test_dirty_merged_worktree_with_pull_request_is_reported_but_not_hidden(self):
        findings = subject.stranded(self.entries(), Path('/repo'), prs=lambda b, r: [12],
                                    is_dirty=lambda p: True, is_merged=lambda b, r, base: True)
        self.assertEqual(len(findings), 2)
        self.assertFalse(any(f['hidden'] for f in findings))
        self.assertEqual(findings[0]['pullRequests'], [12])

    def test_unavailable_pull_request_lookup_is_reported_as_hidden_not_fatal(self):
        findings = subject.stranded(self.entries(), Path('/repo'), prs=lambda b, r: None,
                                    is_dirty=lambda p: True, is_merged=lambda b, r, base: True)
        self.assertTrue(all(f['hidden'] for f in findings))

    def test_clean_or_unmerged_worktrees_are_not_reported(self):
        for is_dirty, is_merged in [(lambda p: False, lambda b, r, base: True),
                                    (lambda p: True, lambda b, r, base: False)]:
            findings = subject.stranded(self.entries(), Path('/repo'), prs=lambda b, r: [],
                                        is_dirty=is_dirty, is_merged=is_merged)
            self.assertEqual(findings, [])

    def test_base_branch_worktree_is_never_reported(self):
        findings = subject.stranded([(Path('/repo'), subject.BASE)], Path('/repo'), prs=lambda b, r: [],
                                    is_dirty=lambda p: True, is_merged=lambda b, r, base: True)
        self.assertEqual(findings, [])

    def test_real_repository_worktrees_parse(self):
        entries = subject.worktrees(subject.ROOT)
        self.assertTrue(entries)
        for path, branch in entries:
            self.assertIsInstance(path, Path)
            self.assertTrue(path.is_absolute())
            self.assertNotIn('refs/heads/', branch)
            self.assertTrue(branch)
        # The base branch must exist as a ref; it need not be the checked-out one.
        self.assertEqual(subject.run(['git', 'rev-parse', '--verify', subject.BASE], subject.ROOT).returncode, 0)

    def test_base_tip_is_an_ancestor_of_itself(self):
        self.assertTrue(subject.merged(subject.BASE, subject.ROOT))

    def test_cli_reports_clean_repository_without_findings(self):
        # Exercises the command path with a fake worktree list so no real worktree is judged.
        completed = subprocess.CompletedProcess([], 0, stdout='', stderr='')
        with patch.object(subject, 'worktrees', return_value=[]), \
             patch.object(subject.subprocess, 'run', return_value=completed), \
             patch.object(sys, 'argv', ['audit_stranded_worktrees.py', '--json']):
            self.assertEqual(subject.main(), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
