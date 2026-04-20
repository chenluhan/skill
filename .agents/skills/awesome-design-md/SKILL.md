---
name: awesome-design-md
description: Use when the user wants to install, choose, or apply a DESIGN.md from getdesign.md or the VoltAgent awesome-design-md catalog, especially before building a UI that should match a known public product or brand style.
---

# Awesome Design MD

## Overview

This skill adds a `DESIGN.md` to the current project by wrapping `npx getdesign@latest add <slug>`.
Use it when the user wants a UI to inherit the visual language of a known site such as Vercel, Apple, Stripe, Linear, BMW, or similar public references.

## Quick Start

If the user already named a design reference:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/add_design_md.py vercel --cwd /absolute/project/path
```

If the user has not named a reference, list options first:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/list_catalog.py
```

Then recommend 2-3 slugs with reasoning tied to the user's product, not just visual taste.

## Workflow

1. Check whether the project root already has `DESIGN.md`.
2. If it already exists, read it before changing anything.
3. If the user wants a new style, either overwrite intentionally with `--force` or install to another filename first for comparison.
4. After install, read the generated `DESIGN.md` and use it as a hard design constraint for UI work.
5. Explain the user impact in plain language: what style was chosen, why it fits, and what it will change in the product surface.

## Selection Rules

- For developer tools or admin products, default to `vercel`, `linear`, `warp`, `posthog`, or `supabase`.
- For premium or luxury products, default to `apple`, `bmw`, `ferrari`, `bugatti`, or `lamborghini`.
- For trust-heavy fintech or payments flows, default to `stripe`, `wise`, `coinbase`, or `mastercard`.
- For editorial or content-led experiences, default to `notion`, `wired`, `theverge`, or `clay`.
- For consumer media or entertainment, default to `spotify`, `playstation`, `runwayml`, or `pinterest`.

Use `/Users/apple/.codex/skills/awesome-design-md/references/selection-guide.md` when you need a quick mapping from product type to candidate styles.

## Commands

- Install into the project root:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/add_design_md.py <slug> --cwd /absolute/project/path
```

- Install to a custom filename for side-by-side comparison:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/add_design_md.py <slug> --cwd /absolute/project/path --out DESIGN.<slug>.md
```

- Overwrite an existing file intentionally:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/add_design_md.py <slug> --cwd /absolute/project/path --force
```

- List the upstream catalog:

```bash
python3 /Users/apple/.codex/skills/awesome-design-md/scripts/list_catalog.py
```

## Notes

- The upstream GitHub repo is not itself a Codex skill. It is only a catalog that points to `getdesign.md`.
- The real install path is the `getdesign` CLI, not cloning the repo.
- After installing `DESIGN.md`, treat it like `AGENTS.md` for visual direction: follow it unless the user asks to diverge.
