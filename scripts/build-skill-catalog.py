#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


def load_categories(path: Path) -> tuple[dict[str, str], dict[str, str], list[str]]:
    raw = json.loads(path.read_text())
    skill_to_category: dict[str, str] = {}
    labels: dict[str, str] = {}
    order: list[str] = []
    for category_id, meta in raw.items():
        labels[category_id] = meta["label"]
        order.append(category_id)
        for skill in meta["skills"]:
            skill_to_category[skill] = category_id
    return skill_to_category, labels, order


def parse_description(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    for index, line in enumerate(lines):
        if re.match(r"^description:\s*[|>]\s*$", line):
            block: list[str] = []
            for block_line in lines[index + 1:]:
                if block_line.startswith("  "):
                    stripped = block_line.strip()
                    if stripped:
                        block.append(stripped)
                    continue
                if not block_line.strip():
                    continue
                break
            if block:
                return " ".join(block)

    match = re.search(r'^description:\s*"?(.*?)"?\s*$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def source_label(path: Path) -> str:
    path_str = str(path)
    if "/.agents/skills/" in path_str:
        return "agents-local"
    if "/.codex/skills/" in path_str:
        if path.is_symlink():
            return "codex-local (symlink)"
        return "codex-local"
    return "repo-only"


def relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    repo_skills_dir = repo_root / ".agents" / "skills"
    codex_dir = Path.home() / ".codex" / "skills"
    agents_dir = Path.home() / ".agents" / "skills"

    skill_to_category, labels, category_order = load_categories(repo_root / "catalog" / "skill-categories.json")

    local_sources: dict[str, Path] = {}

    for base in (codex_dir, agents_dir):
        if not base.exists():
            continue
        for skill_dir in sorted(base.iterdir()):
            if skill_dir.name == ".system":
                continue
            if skill_dir.is_dir():
                local_sources[skill_dir.name] = skill_dir

    repo_skills = sorted(p.name for p in repo_skills_dir.iterdir() if p.is_dir())
    all_skill_names = sorted(set(local_sources) | set(repo_skills))

    by_category: dict[str, list[dict[str, str]]] = {category_id: [] for category_id in category_order}
    uncategorized: list[dict[str, str]] = []

    for name in all_skill_names:
        repo_skill_dir = repo_skills_dir / name
        local_path = local_sources.get(name)
        active_path = local_path or repo_skill_dir
        skill_file = repo_skill_dir / "SKILL.md" if (repo_skill_dir / "SKILL.md").exists() else active_path / "SKILL.md"
        description = parse_description(skill_file) if skill_file.exists() else ""
        local_real = local_path.resolve() if local_path else None

        item = {
            "name": name,
            "source": source_label(local_path) if local_path else "repo-only",
            "local_path": relative(local_real, Path.home()) if local_real else "-",
            "repo_path": relative(repo_skill_dir, repo_root) if repo_skill_dir.exists() else "-",
            "status": "mirrored" if repo_skill_dir.exists() else "local-only",
            "description": description or "-"
        }

        category_id = skill_to_category.get(name)
        if category_id:
            by_category[category_id].append(item)
        else:
            uncategorized.append(item)

    lines: list[str] = []
    lines.append("# Skills Index")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total tracked skills: {len(all_skill_names)}")
    lines.append(f"- Local Codex/Agent sources detected: {len(local_sources)}")
    lines.append(f"- Mirrored into repo: {len(repo_skills)}")
    lines.append("- Excluded from mirror: `.system`")
    lines.append("")

    for category_id in category_order:
        entries = by_category[category_id]
        if not entries:
            continue
        lines.append(f"## {labels[category_id]}")
        lines.append("")
        lines.append("| Skill | Source | Status | Repo Path | Description |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in sorted(entries, key=lambda entry: entry["name"]):
            lines.append(
                f"| `{item['name']}` | `{item['source']}` | `{item['status']}` | `{item['repo_path']}` | {item['description']} |"
            )
        lines.append("")

    if uncategorized:
        lines.append("## Uncategorized")
        lines.append("")
        lines.append("| Skill | Source | Status | Repo Path | Description |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in sorted(uncategorized, key=lambda entry: entry["name"]):
            lines.append(
                f"| `{item['name']}` | `{item['source']}` | `{item['status']}` | `{item['repo_path']}` | {item['description']} |"
            )
        lines.append("")

    output_path = repo_root / "catalog" / "skills-index.md"
    content = "\n".join(lines) + "\n"
    if output_path.exists() and output_path.read_text(encoding="utf-8") == content:
        return
    output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
