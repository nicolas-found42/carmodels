"""Stranding detection: dirty worktrees whose branch tip already reached the base branch.

These tests build their own throwaway repositories with real branches and worktrees, so
they pass in a detached checkout such as pull-request CI and never depend on the state
of the repository running them.
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_stranded_worktrees as subject


def git(*args, cwd):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(f'git {args} failed in {cwd}: {result.stderr}')
    return result.stdout


class RepositoryFixture:
    """A base branch, one merged branch and one active branch, each in its own worktree."""

    def __init__(self, root):
        resolved = Path(root).resolve()
        self.root = resolved / 'repo'
        self.root.mkdir()
        git('init', '-q', '-b', 'main', cwd=self.root)
        git('config', 'user.email', 'tests@example.invalid', cwd=self.root)
        git('config', 'user.name', 'audit tests', cwd=self.root)
        (self.root / 'file.txt').write_text('base\n')
        git('add', 'file.txt', cwd=self.root)
        git('commit', '-q', '-m', 'base', cwd=self.root)
        # merged: same tip as main, so it has nothing left to merge
        git('branch', 'feature/merged', cwd=self.root)
        # active: one commit main does not have
        git('checkout', '-q', '-b', 'feature/active', cwd=self.root)
        (self.root / 'file.txt').write_text('active\n')
        git('commit', '-q', '-am', 'active work', cwd=self.root)
        git('checkout', '-q', 'main', cwd=self.root)
        self.merged = resolved / 'wt-merged'
        self.active = resolved / 'wt-active'
        git('worktree', 'add', '-q', str(self.merged), 'feature/merged', cwd=self.root)
        git('worktree', 'add', '-q', str(self.active), 'feature/active', cwd=self.root)

    def write(self, worktree, name='scratch.txt', text='uncommitted\n'):
        (Path(worktree) / name).write_text(text)


class StrandedTests(unittest.TestCase):
    def test_detects_dirty_merged_worktree_and_ignores_active_one(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            fixture.write(fixture.merged)
            fixture.write(fixture.active)
            entries = subject.worktrees(fixture.root)
            self.assertIn(('feature/merged', str(fixture.merged)),
                          [(b, str(p)) for p, b in entries])
            findings = subject.stranded(entries, fixture.root, prs=lambda b, r: [])
            self.assertEqual([f['branch'] for f in findings], ['feature/merged'])
            self.assertTrue(findings[0]['hidden'])
            self.assertEqual(findings[0]['pullRequests'], [])

    def test_clean_merged_worktree_is_not_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            fixture.write(fixture.active)  # only the active worktree is dirty
            findings = subject.stranded(subject.worktrees(fixture.root), fixture.root,
                                        prs=lambda b, r: [])
            self.assertEqual(findings, [])

    def test_known_pull_request_is_reported_but_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            fixture.write(fixture.merged)
            findings = subject.stranded(subject.worktrees(fixture.root), fixture.root,
                                        prs=lambda b, r: [12])
            self.assertEqual(len(findings), 1)
            self.assertFalse(findings[0]['hidden'])
            self.assertEqual(findings[0]['pullRequests'], [12])

    def test_unknown_pull_request_lookup_is_hidden_not_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            fixture.write(fixture.merged)
            findings = subject.stranded(subject.worktrees(fixture.root), fixture.root,
                                        prs=lambda b, r: None)
            self.assertTrue(findings[0]['hidden'])

    def test_detached_worktree_parses_without_a_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            detached = Path(temp).resolve() / 'wt-detached'
            git('worktree', 'add', '-q', '--detach', str(detached), cwd=fixture.root)
            entries = {str(p): b for p, b in subject.worktrees(fixture.root)}
            self.assertIn(str(detached), entries)
            self.assertIsNone(entries[str(detached)])

    def test_missing_base_branch_is_an_error_not_an_all_clear(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            with self.assertRaises(subject.AuditError):
                subject.base_exists(fixture.root, 'no-such-branch')

    def test_unknown_ref_during_ancestry_check_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            with self.assertRaises(subject.AuditError):
                subject.merged('feature/merged', fixture.root, 'no-such-branch')

    def test_not_an_ancestor_is_false_not_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            self.assertFalse(subject.merged('feature/active', fixture.root))
            self.assertTrue(subject.merged('feature/merged', fixture.root))

    def test_failed_worktree_enumeration_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(subject.AuditError):
                subject.worktrees(Path(temp))  # not a repository

    def test_failed_status_check_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(subject.AuditError):
                subject.dirty(Path(temp))  # not a repository

    def run_cli(self, *argv):
        """main() with its console output captured, so test logs stay readable."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with patch.object(sys, 'argv', ['audit_stranded_worktrees.py', *argv]):
                return subject.main()

    def test_cli_exits_two_on_an_unknown_base(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            with patch.object(subject, 'ROOT', fixture.root):
                self.assertEqual(self.run_cli('--base', 'nope'), 2)

    def test_cli_reports_a_stranded_worktree_and_an_all_clear(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = RepositoryFixture(temp)
            fixture.write(fixture.merged)
            with patch.object(subject, 'ROOT', fixture.root), patch.object(
                    subject, 'pull_requests', lambda b, r: []):
                self.assertEqual(self.run_cli('--json'), 1)
            (Path(fixture.merged) / 'scratch.txt').unlink()
            with patch.object(subject, 'ROOT', fixture.root), patch.object(
                    subject, 'pull_requests', lambda b, r: []):
                self.assertEqual(self.run_cli('--json'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
