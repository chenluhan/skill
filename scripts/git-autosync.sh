#!/bin/zsh

set -euo pipefail

repo_root="${0:A:h:h}"
cd "$repo_root"

git rev-parse --is-inside-work-tree >/dev/null

git_user_name="$(git config --get user.name || true)"
git_user_email="$(git config --get user.email || true)"

if [[ -z "$git_user_name" || -z "$git_user_email" ]]; then
  echo "Skipped: git user.name or user.email is not configured."
  exit 0
fi

git add -A

if git diff --cached --quiet --exit-code; then
  echo "Skipped: repository is clean."
  exit 0
fi

timestamp="$(date '+%Y-%m-%d %H:%M:%S %z')"
commit_message="chore: auto sync ${timestamp}"

git commit -m "$commit_message" >/dev/null

commit_hash="$(git rev-parse --short HEAD)"
changed_files="$(git show --stat --oneline --format=short HEAD)"

echo "Created commit: ${commit_hash}"
echo "$changed_files"
