#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import urllib.request


README_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/README.md"
LINE_RE = re.compile(r"- \[\*\*(?P<name>.+?)\*\*\]\(https://getdesign\.md/(?P<slug>.+?)/design-md\) - (?P<desc>.+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List design references available from the awesome-design-md catalog."
    )
    parser.add_argument(
        "--query",
        help="Filter results by slug, name, or description.",
    )
    return parser.parse_args()


def fetch_readme() -> str:
    with urllib.request.urlopen(README_URL) as response:
        return response.read().decode("utf-8")


def main() -> int:
    args = parse_args()
    query = args.query.lower() if args.query else None

    try:
        readme = fetch_readme()
    except Exception as exc:
        print(f"Failed to fetch catalog: {exc}", file=sys.stderr)
        return 1

    rows: list[tuple[str, str, str]] = []
    for line in readme.splitlines():
        match = LINE_RE.match(line.strip())
        if not match:
            continue

        name = match.group("name")
        slug = match.group("slug")
        desc = match.group("desc")
        if query:
            haystack = f"{slug} {name} {desc}".lower()
            if query not in haystack:
                continue
        rows.append((slug, name, desc))

    if not rows:
        print("No matching design references found.", file=sys.stderr)
        return 1

    width = max(len(slug) for slug, _, _ in rows)
    for slug, name, desc in rows:
        print(f"{slug.ljust(width)}  {name}  {desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
