# skill

Distribution repository for local Codex skills, agent prompts, design specs, and git automation.

## Structure

- `.agents/skills/`: mirrored repo copy of local skills for cross-client distribution
- `.claude/skills/`: generated Claude Code compatibility symlinks to `.agents/skills/`
- `catalog/`: skill taxonomy and generated inventory
- `agents/`: future agent source and prompt assets
- `docs/superpowers/specs/`: design docs
- `scripts/`: mirror, catalog, and git automation scripts
- `notes/`: local scratch space, ignored by git

## Workflow

- Authoring still happens in local runtime folders such as `~/.codex/skills/` and `~/.agents/skills/`
- `scripts/sync-skill-repo.sh` mirrors those local skills into this repo, rebuilds the catalog, then commits and pushes if needed
- Auto-sync only stages skill-distribution paths; unrelated repo edits are left untouched
- The repo is the distribution surface for other clients; local runtime directories remain the editing surface until you deliberately switch to a repo-first workflow

## Usage

- If a client supports the open Agent Skills layout, read from `.agents/skills/`
- If a client follows Claude Code project conventions, use `.claude/skills/`
- Do not edit `.claude/skills/` directly; it is generated from `.agents/skills/`

## Git

- Local repo-only changes can be committed by `scripts/git-autosync.sh`
- Remote sync is handled by `scripts/git-autosync-remote.sh`
- End-to-end skill mirroring plus git sync runs via `scripts/sync-skill-repo.sh`
