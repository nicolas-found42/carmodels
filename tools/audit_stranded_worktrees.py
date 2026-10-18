#!/usr/bin/env python3
"""Report worktrees whose uncommitted work cannot reach main through their branch.

A worktree is stranded when it is dirty **and** its branch tip is already an ancestor
of the base branch: the branch has nothing left to merge, so whatever is uncommitted
in that directory can never arrive through a pull request on it. That is how finished,
independently reviewed work previously sat unreviewed for days in an agent worktree
whose branch had already been merged — no check in the repository noticed.

Reports only. It never modifies the repository, never removes a worktree, and never
touches a branch. Every git failure is fatal rather than an empty result: an audit
that cannot read the repository must not report an all-clear.

Exit status: 0 nothing stranded, 1 something is stranded, 2 the audit could not be
trusted (a git call failed, or the base branch does not exist).
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'main'


class AuditError(RuntimeError):
    """A git call failed, so no conclusion can be drawn from this run."""


def run(command, cwd=None):
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def worktrees(root):
    """(path, branch) for every registered worktree; branch is None when detached."""
    result = run(['git', 'worktree', 'list', '--porcelain'], root)
    if result.returncode:
        raise AuditError(f"git worktree list failed: {result.stderr.strip() or result.returncode}")
    entries, path, branch = [], None, None
    for line in result.stdout.splitlines() + ['']:
        if line.startswith('worktree '):
            path, branch = Path(line[len('worktree '):]), None
        elif line.startswith('branch '):
            branch = line[len('branch '):].removeprefix('refs/heads/')
        elif line.startswith('detached') and path is not None:
            branch = None
        elif not line.strip() and path is not None:
            entries.append((path, branch))
            path, branch = None, None
    return entries


def dirty(path):
    result = run(['git', '-C', str(path), 'status', '--porcelain'])
    if result.returncode:
        raise AuditError(f"git status failed in {path}: {result.stderr.strip() or result.returncode}")
    return bool(result.stdout.strip())


def merged(branch, root, base=BASE):
    """True when the branch tip is already an ancestor of the base branch.

    Exit 1 is git's ordinary "not an ancestor" answer. Any other non-zero code is a
    failure (an unknown ref, say) and must not be read as "nothing to report".
    """
    result = run(['git', 'merge-base', '--is-ancestor', branch, base], root)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise AuditError(f'git merge-base --is-ancestor {branch} {base} failed: '
                     f'{result.stderr.strip() or result.returncode}')


def base_exists(root, base=BASE):
    result = run(['git', 'rev-parse', '--verify', '--quiet', f'{base}^{{commit}}'], root)
    if result.returncode:
        raise AuditError(f'base branch {base!r} does not exist in {root}')
    return True


def pull_requests(branch, root):
    """Pull-request numbers for a branch, in any state. None when unknown.

    Unknown is reported as hidden rather than as an all-clear, so a missing or failing
    gh can only over-report, never hide work.
    """
    if shutil.which('gh') is None:
        return None
    result = run(['gh', 'pr', 'list', '--head', branch, '--state', 'all',
                  '--json', 'number', '--jq', '.[].number'], root)
    if result.returncode:
        return None
    return [int(line) for line in result.stdout.split() if line.isdigit()]


def stranded(entries, root, base=BASE, prs=pull_requests, is_dirty=dirty, is_merged=merged):
    """Worktrees whose dirty files cannot reach the base branch, with PR context.

    `hidden` marks the severe case: no pull request is known to exist, so the work is
    invisible outside that directory.
    """
    findings = []
    for path, branch in entries:
        if branch is None or branch == base:
            continue
        if not is_dirty(path) or not is_merged(branch, root, base):
            continue
        numbers = prs(branch, root)
        findings.append({'worktree': str(path), 'branch': branch, 'pullRequests': numbers,
                         'hidden': not numbers})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true', help='emit machine-readable findings')
    parser.add_argument('--base', default=BASE)
    args = parser.parse_args()
    try:
        base_exists(ROOT, args.base)
        findings = stranded(worktrees(ROOT), ROOT, args.base)
    except AuditError as error:
        print(f'audit failed: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(findings, indent=2))
    elif not findings:
        print(f'No stranded worktrees: every dirty worktree has unmerged work on its branch '
              f'(base {args.base}).')
    else:
        for entry in findings:
            state = ('no pull request' if entry['hidden']
                     else f"PR {entry['pullRequests']} (no commits to merge)")
            print(f"stranded: {entry['worktree']} [{entry['branch']}] — dirty, tip already in "
                  f"{args.base}, {state}")
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
