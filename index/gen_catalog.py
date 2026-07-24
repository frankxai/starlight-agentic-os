#!/usr/bin/env python3
"""gen_catalog.py — Starlight Agentic OS, Phase D.

Walk one or more repository roots, find every ``SKILL.md``, parse its YAML
frontmatter (``name``, ``description``, and any extra metadata), and emit a
``catalog.json`` that ``build_index.py`` / ``scan_skill_frontmatter.py`` consume.

The catalog is an array of objects shaped like::

    {
      "id": "frankx-creator-os:content-strategy",
      "name": "content-strategy",
      "description": "...",
      "pack": "frankx-creator-os",
      "repo": "starlight-skills",
      "path": "skills/content-strategy/SKILL.md",
      "origin": "local",
      "maturity": "stable",
      "body_path": "C:/.../skills/content-strategy/SKILL.md"
    }

Design notes
------------
* Cross-platform via ``pathlib`` only. ``path`` is emitted as a POSIX-style
  relative path (stable across OSes); ``body_path`` is the absolute on-disk
  path so ``build_index.py`` can read the body regardless of CWD.
* ``id`` is ``"{pack}:{name}"`` when a pack is known, else just ``name``; a
  numeric suffix is appended on collision so ids stay unique and deterministic.
* Deterministic: results are sorted by id.

Usage
-----
    python gen_catalog.py --roots ./skills ../other-repo/skills \
        --out catalog.json --origin local --default-maturity stable
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None  # fall back to the minimal parser below


# --------------------------------------------------------------------------- #
# Frontmatter parsing
# --------------------------------------------------------------------------- #
def parse_frontmatter(md_text: str) -> Dict[str, object]:
    """Return the YAML frontmatter block of a markdown file as a dict.

    Recognizes a leading ``---`` ... ``---`` fence. Uses PyYAML when available,
    otherwise a minimal ``key: value`` fallback so the tool still runs without
    the dependency.
    """
    if not md_text.startswith("---"):
        return {}
    # Find the closing fence (a line that is exactly '---').
    lines = md_text.splitlines()
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    block = "\n".join(lines[1:end_idx])

    if yaml is not None:
        try:
            data = yaml.safe_load(block)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError:
            return {}

    # Minimal fallback parser.
    out: Dict[str, object] = {}
    for line in block.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition(":")
            out[key.strip().lower()] = val.strip().strip("'\"")
    return out


# --------------------------------------------------------------------------- #
# Catalog construction
# --------------------------------------------------------------------------- #
def _infer_pack(skill_md: Path, root: Path) -> Optional[str]:
    """Best-effort pack name: the top-level directory under ``root``."""
    try:
        rel = skill_md.relative_to(root)
    except ValueError:
        return None
    parts = rel.parts
    # rel is like (<pack>/.../<skill>/SKILL.md); take the first component if it
    # is not itself the skill dir.
    if len(parts) >= 3:
        return parts[0]
    return root.name or None


def _unique_id(base: str, used: Dict[str, int]) -> str:
    if base not in used:
        used[base] = 0
        return base
    used[base] += 1
    return f"{base}-{used[base]}"


def build_catalog(
    roots: Sequence[Path],
    origin: str,
    default_maturity: str,
    repo: Optional[str],
) -> List[Dict[str, object]]:
    """Walk ``roots`` and produce a deterministic list of catalog entries."""
    entries: List[Dict[str, object]] = []
    used_ids: Dict[str, int] = {}

    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            print(f"warning: root does not exist: {root}", file=sys.stderr)
            continue
        for skill_md in sorted(root.rglob("SKILL.md")):
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                print(f"warning: cannot read {skill_md}: {exc}", file=sys.stderr)
                continue

            fm = parse_frontmatter(text)
            name = str(fm.get("name") or skill_md.parent.name)
            pack = str(fm.get("pack") or _infer_pack(skill_md, root) or "")
            base_id = f"{pack}:{name}" if pack else name

            entries.append(
                {
                    "id": _unique_id(base_id, used_ids),
                    "name": name,
                    "description": str(fm.get("description") or ""),
                    "pack": pack or None,
                    "repo": str(fm.get("repo") or repo or root.name),
                    # POSIX-style relative path for portability.
                    "path": skill_md.relative_to(root).as_posix(),
                    "origin": str(fm.get("origin") or origin),
                    "maturity": str(fm.get("maturity") or default_maturity),
                    # Absolute path so build_index can always read the body.
                    "body_path": str(skill_md),
                }
            )

    entries.sort(key=lambda e: str(e["id"]))
    return entries


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate catalog.json from SKILL.md trees.")
    p.add_argument(
        "--roots",
        nargs="+",
        type=Path,
        required=True,
        help="One or more repo roots to walk for SKILL.md files.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("catalog.json"),
        help="Output path (default: ./catalog.json).",
    )
    p.add_argument("--origin", default="local", help="Default provenance tag.")
    p.add_argument(
        "--default-maturity",
        default="unknown",
        help="Maturity when frontmatter omits it.",
    )
    p.add_argument("--repo", default=None, help="Default repo name when frontmatter omits it.")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    entries = build_catalog(args.roots, args.origin, args.default_maturity, args.repo)
    args.out.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(entries)} skills to {args.out}")
    if yaml is None:
        print(
            "note: PyYAML not installed — used the minimal frontmatter parser. "
            "Install pyyaml for robust parsing.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
