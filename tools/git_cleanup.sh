#!/usr/bin/env bash
# Run after a PR merges: fast-forward main, then delete merged branches locally and on origin.
#
#   tools/git_cleanup.sh            # clean up
#   tools/git_cleanup.sh --dry-run  # print what would happen
#
# A branch counts as merged only when a MERGED pull request's head commit equals the branch tip,
# or the branch tip is already in origin/main and its upstream is gone. Branches that gained
# commits after their PR merged, and branches with no PR yet, are never touched.
# Worktrees holding a merged branch are removed only when clean (no --force).
set -euo pipefail

BASE=main
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

command -v gh >/dev/null || { echo "gh CLI is required" >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)"

run() {
  if [ "$DRY" = 1 ]; then echo "would: $*"; else echo "+ $*"; "$@"; fi
}

merged_pr_tip() { # $1 branch name, $2 commit sha
  gh pr list --head "$1" --state merged --limit 20 --json headRefOid --jq '.[].headRefOid' | grep -qx "$2"
}

local_is_merged() { # $1 local branch
  local tip upstream_gone
  tip=$(git rev-parse "refs/heads/$1")
  if merged_pr_tip "$1" "$tip"; then return 0; fi
  upstream_gone=$(git for-each-ref --format='%(upstream:track)' "refs/heads/$1")
  [ "$upstream_gone" = "[gone]" ] && git merge-base --is-ancestor "$tip" "origin/$BASE"
}

worktree_of() { # $1 branch -> path of the worktree that has it checked out, if any
  git worktree list --porcelain | awk -v b="refs/heads/$1" '
    /^worktree /{p=substr($0,10)} $0=="branch " b {print p}'
}

git fetch --prune origin

current=$(git branch --show-current)
primary=$(git worktree list --porcelain | awk 'NR==1{print substr($0,10)}')
if [ "$current" != "$BASE" ] && [ -n "$current" ] && local_is_merged "$current"; then
  echo "current branch $current is merged; switching to $BASE"
  run git switch "$BASE"
  [ "$DRY" = 1 ] || current=$BASE
fi

if [ "$current" = "$BASE" ]; then
  run git merge --ff-only "origin/$BASE"
else
  run git fetch origin "$BASE:$BASE" || echo "warn: could not fast-forward local $BASE here" >&2
fi

for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  [ "$b" = "$BASE" ] && continue
  [ "$b" = "$current" ] && continue
  local_is_merged "$b" || continue
  wt=$(worktree_of "$b")
  if [ -n "$wt" ] && [ "$wt" = "$primary" ]; then
    echo "skip $b: checked out in the main working tree $wt; run this script from there" >&2
    continue
  fi
  if [ -n "$wt" ]; then
    run git worktree remove "$wt" || { echo "skip $b: worktree $wt is not clean" >&2; continue; }
  fi
  run git branch -D "$b"
done

for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin); do
  b=${ref#origin/}
  case "$b" in origin|HEAD|"$BASE") continue ;; esac
  if merged_pr_tip "$b" "$(git rev-parse "refs/remotes/$ref")"; then
    run git push origin --delete "$b"
  fi
done

echo "cleanup done"
