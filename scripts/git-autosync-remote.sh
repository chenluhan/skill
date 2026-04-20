#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
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

push_output=""
if push_output="$(git push origin "$current_branch" 2>&1)"; then
  echo "Remote sync completed."
  exit 0
fi

if echo "$push_output" | grep -Eq "Could not resolve host|Name or service not known|Temporary failure in name resolution|Failed to connect|Connection timed out|Network is unreachable"; then
  echo "Blocked: network/DNS prevents pushing to origin."
  echo "$push_output"
  exit 0
fi

if echo "$push_output" | grep -Eq "Authentication failed|could not read Username|Permission denied|HTTP Basic: Access denied|fatal: Authentication"; then
  echo "Blocked: origin push requires GitHub credentials."
  echo "$push_output"
  exit 0
fi

echo "Failed: origin push did not succeed."
echo "$push_output"
exit 1
