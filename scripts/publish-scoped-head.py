#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path


def run(*args: str, input_text: str | None = None) -> str:
    return subprocess.check_output(args, text=True, input=input_text).strip()


def run_bytes(*args: str) -> bytes:
    return subprocess.check_output(args)


def repo_slug(repo_root: Path) -> str:
    remote = run("git", "-C", str(repo_root), "remote", "get-url", "origin")
    remote = remote.removesuffix(".git")
    if remote.startswith("https://github.com/"):
        return remote.removeprefix("https://github.com/")
    raise RuntimeError(f"Unsupported origin remote: {remote}")


def head_metadata(repo_root: Path) -> dict[str, str]:
    fields = run(
        "git",
        "-C",
        str(repo_root),
        "show",
        "-s",
        "--format=%B%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        "HEAD",
    ).split("\0")
    return {
        "message": fields[0].rstrip("\n"),
        "author_name": fields[1],
        "author_email": fields[2],
        "author_date": fields[3],
        "committer_name": fields[4],
        "committer_email": fields[5],
        "committer_date": fields[6],
    }


def changed_paths(repo_root: Path) -> list[tuple[str, str]]:
    output = run(
        "git",
        "-C",
        str(repo_root),
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        "HEAD^",
        "HEAD",
    )
    items: list[tuple[str, str]] = []
    for line in output.splitlines():
        status, path = line.split("\t", 1)
        items.append((status, path))
    return items


def ls_tree_mode(repo_root: Path, rev: str, path: str) -> str:
    line = run("git", "-C", str(repo_root), "ls-tree", rev, path)
    return line.split()[0]


def create_blob(repo: str, content: bytes) -> str:
    payload = {
        "content": base64.b64encode(content).decode("ascii"),
        "encoding": "base64",
    }
    return json.loads(
        run("gh", "api", f"repos/{repo}/git/blobs", "--method", "POST", "--input", "-", input_text=json.dumps(payload))
    )["sha"]


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    repo = repo_slug(repo_root)
    meta = head_metadata(repo_root)
    remote_head = run("gh", "api", f"repos/{repo}/git/ref/heads/main", "--jq", ".object.sha")
    remote_tree = run("gh", "api", f"repos/{repo}/git/commits/{remote_head}", "--jq", ".tree.sha")

    tree_entries: list[dict[str, object]] = []
    for status, path in changed_paths(repo_root):
        if status == "D":
            old_mode = ls_tree_mode(repo_root, "HEAD^", path)
            tree_entries.append({"path": path, "mode": old_mode, "type": "blob", "sha": None})
            continue

        mode = ls_tree_mode(repo_root, "HEAD", path)
        file_path = repo_root / path

        if mode == "120000":
            tree_entries.append(
                {"path": path, "mode": "120000", "type": "blob", "content": file_path.readlink().as_posix()}
            )
            continue

        blob_sha = create_blob(repo, run_bytes("git", "-C", str(repo_root), "show", f"HEAD:{path}"))
        tree_entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob_sha})

    if not tree_entries:
        print("Skipped: no changed files in HEAD.")
        return

    tree_payload = {"base_tree": remote_tree, "tree": tree_entries}
    new_tree = json.loads(
        run("gh", "api", f"repos/{repo}/git/trees", "--method", "POST", "--input", "-", input_text=json.dumps(tree_payload))
    )["sha"]

    commit_payload = {
        "message": meta["message"],
        "tree": new_tree,
        "parents": [remote_head],
        "author": {
            "name": meta["author_name"],
            "email": meta["author_email"],
            "date": meta["author_date"],
        },
        "committer": {
            "name": meta["committer_name"],
            "email": meta["committer_email"],
            "date": meta["committer_date"],
        },
    }
    new_commit = json.loads(
        run("gh", "api", f"repos/{repo}/git/commits", "--method", "POST", "--input", "-", input_text=json.dumps(commit_payload))
    )["sha"]

    run("gh", "api", f"repos/{repo}/git/refs/heads/main", "--method", "PATCH", "-f", f"sha={new_commit}", "-F", "force=false")
    print(new_commit)


if __name__ == "__main__":
    main()
