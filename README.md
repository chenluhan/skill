# skill

Source repository for Codex skills, agent prompts, design specs, and local git automation.

## Structure

- `.agents/skills/`: canonical skill source for cross-client compatibility
- `.claude/skills/`: Claude Code compatibility entry points, symlinked to `.agents/skills/`
- `agents/`: future agent source and prompt assets
- `docs/superpowers/specs/`: design docs
- `scripts/`: repo automation and maintenance scripts
- `notes/`: local scratch space, ignored by git

## Usage

- If a client supports the open Agent Skills layout, read from `.agents/skills/`
- If a client follows Claude Code project conventions, use `.claude/skills/`
- Do not edit the symlinked `.claude/skills/` copies directly; edit the canonical files under `.agents/skills/`

## Git

- Local changes can be auto-committed by `scripts/git-autosync.sh`
- Remote sync is handled by `scripts/git-autosync-remote.sh`
