#!/usr/bin/env python3
"""Report worktrees whose uncommitted work cannot reach main through their branch.

A worktree is stranded when it is dirty **and** its branch tip is already an ancestor
of the base branch: the branch has nothing left to merge, so whatever is uncommitted
in that directory can never arrive through a pull request on it. That is how finished,
independently reviewed work previously sat unreviewed for days in an agent worktree
whose branch had already been merged — no check in the repository noticed.

Reports only. It never modifies the repository, never removes a worktree, and never
touches a branch. `gh` is used for pull-request context and its absence is reported
rather than fatal.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'main'


def run(command, cwd=None):
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def worktrees(root):
    """(path, branch) for every registered worktree; detached heads are skipped."""
    entries, path = [], None
    for line in run(['git', 'worktree', 'list', '--porcelain'], root).stdout.splitlines():
        if line.startswith('worktree '):
            path = line[len('worktree '):]
        elif line.startswith('branch ') and path:
            entries.append((Path(path), line[len('branch '):].removeprefix('refs/heads/')))
    return entries


def dirty(path):
    return bool(run(['git', '-C', str(path), 'status', '--porcelain']).stdout.strip())


def merged(branch, root, base=BASE):
    return run(['git', 'merge-base', '--is-ancestor', branch, base], root).returncode == 0


def pull_requests(branch, root):
    """Pull-request numbers for a branch, in any state. None when gh is unavailable."""
    if shutil.which('gh') is None:
        return None
    result = run(['gh', 'pr', 'list', '--head', branch, '--state', 'all',
                  '--json', 'number', '--jq', '.[].number'], root)
    if result.returncode:
        return None
    return [int(line) for line in result.stdout.split() if line.isdigit()]


def stranded(entries, root, base=BASE, prs=pull_requests, is_dirty=dirty, is_merged=merged):
    """Worktrees whose dirty files cannot reach the base branch, with PR context.

    `hidden` marks the severe case: no pull request exists at all, so the work is
    invisible outside that directory.
    """
    findings = []
    for path, branch in entries:
        if branch == base or not is_dirty(path) or not is_merged(branch, root, base):
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
    findings = stranded(worktrees(ROOT), ROOT, args.base)
    if args.json:
        print(json.dumps(findings, indent=2))
    elif not findings:
        print(f'No stranded worktrees: every dirty worktree has unmerged work on its branch '
              f'(base {args.base}).')
    else:
        for entry in findings:
            state = 'no pull request' if entry['hidden'] else f"PR {entry['pullRequests']} (no commits to merge)"
            print(f"stranded: {entry['worktree']} [{entry['branch']}] — dirty, tip already in "
                  f"{args.base}, {state}")
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
