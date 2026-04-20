#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
repo_skills_dir="$repo_root/.agents/skills"
claude_skills_dir="$repo_root/.claude/skills"

mkdir -p "$repo_skills_dir" "$claude_skills_dir"

if ! command -v rsync >/dev/null 2>&1; then
  echo "Missing dependency: rsync"
  exit 1
fi

seen_file="$(mktemp)"
trap 'rm -f "$seen_file"' EXIT

sync_from_root() {
  local source_root="$1"
  local label="$2"

  [[ -d "$source_root" ]] || return 0

  for skill_path in "$source_root"/*; do
    [[ -e "$skill_path" ]] || continue
    [[ -d "$skill_path" ]] || continue

    local skill_name
    skill_name="$(basename "$skill_path")"

    if [[ "$skill_name" == ".system" ]]; then
      continue
    fi

    local target="$repo_skills_dir/$skill_name"
    rm -rf "$target"
    mkdir -p "$target"
    rsync -aL --delete --exclude '.DS_Store' "$skill_path"/ "$target"/
    printf '%s\n' "$skill_name" >> "$seen_file"
    echo "Mirrored [$label] $skill_name"
  done
}

sync_from_root "$HOME/.codex/skills" "codex"
sync_from_root "$HOME/.agents/skills" "agents"

for existing in "$repo_skills_dir"/*; do
  [[ -e "$existing" ]] || continue
  skill_name="$(basename "$existing")"
  if ! grep -Fxq "$skill_name" "$seen_file"; then
    rm -rf "$existing"
    echo "Removed stale repo skill $skill_name"
  fi
done

find "$claude_skills_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

for skill_dir in "$repo_skills_dir"/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name="$(basename "$skill_dir")"
  ln -s "../../.agents/skills/$skill_name" "$claude_skills_dir/$skill_name"
done

python3 "$repo_root/scripts/build-skill-catalog.py"
