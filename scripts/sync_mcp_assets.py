#!/usr/bin/env python3
"""Synchronize canonical index assets into the self-contained MCP package."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ASSETS = (
    (ROOT / "index/catalog.json", ROOT / "mcp-server/catalog.json"),
    (
        ROOT / "index/scan_skill_frontmatter.py",
        ROOT / "mcp-server/scan_skill_frontmatter.py",
    ),
    (
        ROOT / "index/security-allowlist.json",
        ROOT / "mcp-server/security-allowlist.json",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize generated MCP package assets from their canonical sources."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any package asset is missing or stale; do not write.",
    )
    args = parser.parse_args()

    stale: list[str] = []
    for source, target in ASSETS:
        if not source.is_file():
            print(f"BLOCK canonical asset missing: {source.relative_to(ROOT)}", file=sys.stderr)
            return 1
        if target.is_file() and target.read_bytes() == source.read_bytes():
            print(f"PASS {target.relative_to(ROOT)}")
            continue
        stale.append(str(target.relative_to(ROOT)))
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            print(
                f"SYNC {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}"
            )

    if args.check and stale:
        print(
            "BLOCK stale generated MCP package assets: " + ", ".join(stale),
            file=sys.stderr,
        )
        return 1
    if not stale:
        print(f"MCP package assets: PASS ({len(ASSETS)}/{len(ASSETS)})")
    elif not args.check:
        print(f"MCP package assets: SYNCHRONIZED ({len(stale)} updated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
