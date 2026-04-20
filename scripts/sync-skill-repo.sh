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

commit_hash="$(git rev-parse --short HEAD)"
echo "Created commit: ${commit_hash}"
git show --stat --oneline --format=short HEAD

publish_output=""
if publish_output="$(python3 "$repo_root/scripts/publish-scoped-head.py" 2>&1)"; then
  echo "Published remote commit: ${publish_output}"
  echo "Remote sync completed."
  exit 0
fi

if echo "$publish_output" | grep -Eq "Could not resolve host|Name or service not known|Temporary failure in name resolution|Failed to connect|Connection timed out|Network is unreachable"; then
  echo "Blocked: network/DNS prevents publishing to origin."
  echo "$publish_output"
  exit 0
fi

if echo "$publish_output" | grep -Eq "HTTP 401|HTTP 403|Authentication failed|could not read Username|Permission denied|HTTP Basic: Access denied|fatal: Authentication"; then
  echo "Blocked: origin publish requires GitHub credentials."
  echo "$publish_output"
  exit 0
fi

echo "Failed: origin publish did not succeed."
echo "$publish_output"
exit 1
