#!/bin/zsh

set -euo pipefail

repo_root="${0:A:h:h}"
cd "$repo_root"

git rev-parse --is-inside-work-tree >/dev/null

"$repo_root/scripts/git-autosync.sh"

current_branch="$(git branch --show-current)"
upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"

if [[ -z "$current_branch" || -z "$upstream_ref" ]]; then
  echo "Skipped: branch or upstream is not configured."
  exit 0
fi

ahead_count="$(git rev-list --count "${upstream_ref}..HEAD")"

if [[ "$ahead_count" == "0" ]]; then
  echo "Skipped: no remote sync needed."
  exit 0
fi

if git push origin "$current_branch"; then
  echo "Remote sync completed."
else
  echo "Failed: remote sync requires valid GitHub credentials for origin."
  exit 1
fi
