#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

"$repo_root/scripts/mirror-local-skills.sh"

cd "$repo_root"
git rev-parse --is-inside-work-tree >/dev/null

git_user_name="$(git config --get user.name || true)"
git_user_email="$(git config --get user.email || true)"

if [[ -z "$git_user_name" || -z "$git_user_email" ]]; then
  echo "Skipped: git user.name or user.email is not configured."
  exit 0
fi

if ! git diff --cached --quiet --exit-code; then
  echo "Blocked: staged changes already exist, so scoped auto-sync will not continue."
  exit 0
fi

paths=(
  ".agents/skills"
  ".claude/skills"
  "catalog"
  ".gitignore"
  "README.md"
  "agent.md"
  "scripts/build-skill-catalog.py"
  "scripts/mirror-local-skills.sh"
  "scripts/sync-skill-repo.sh"
)

git add -A -- "${paths[@]}"

if git diff --cached --quiet --exit-code; then
  echo "Skipped: scoped skill repository state is clean."
  exit 0
fi

timestamp="$(date '+%Y-%m-%d %H:%M:%S %z')"
commit_message="chore: auto sync ${timestamp}"
git commit -m "$commit_message" >/dev/null

current_branch="$(git branch --show-current)"
upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"

if [[ -z "$current_branch" || -z "$upstream_ref" ]]; then
  echo "Skipped: branch or upstream is not configured."
  exit 0
fi

push_output=""
if push_output="$(git push origin "$current_branch" 2>&1)"; then
  commit_hash="$(git rev-parse --short HEAD)"
  echo "Created commit: ${commit_hash}"
  git show --stat --oneline --format=short HEAD
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
