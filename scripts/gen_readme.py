#!/usr/bin/env python3
"""
gen_readme.py — regenerate the README status matrix from registry.yaml (the SSOT).

Reads   : registry.yaml
Writes  : README.md   (replaces the block between the STATUS-MATRIX markers)
Emits   : a markdown table + Shields.io summary badges, one row per pack.

Usage:
    python scripts/gen_readme.py            # rewrite README.md in place
    python scripts/gen_readme.py --check    # non-zero exit if README is stale (CI gate)

Dependency: PyYAML (verified present: 6.0.3). No network calls; badges are static
Shields URLs rendered by GitHub, not fetched here.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML not installed. `pip install pyyaml` (registry parsing needs it).")

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"
README = ROOT / "README.md"
START = "<!-- STATUS-MATRIX:START -->"
END = "<!-- STATUS-MATRIX:END -->"

# Lifecycle cell rendering: state value -> glyph
INSTALL = {"done": "✅", "partial": "🟡", "todo": "⬜"}
IMPROVE = {"done": "✅", "in-progress": "🟡", "todo": "⬜", "deprecate-candidate": "⚠️ dep"}
INDEXED = {"done": "✅", "todo": "⬜"}


def badge(label: str, value: str, color: str) -> str:
    label = label.replace("-", "--").replace(" ", "_")
    value = str(value).replace("-", "--").replace(" ", "_").replace("/", "%2F")
    return f"![{label}](https://img.shields.io/badge/{label}-{value}-{color})"


def cell(mapping: dict, value, default="⬜") -> str:
    return mapping.get(value, default)


def registered_cell(reg) -> str:
    if not reg:
        return "⬜ none"
    return "✅ " + ", ".join(reg)


def build_matrix(data: dict) -> str:
    packs = data.get("packs", [])
    n = len(packs)

    # summary counters
    install_done = sum(1 for p in packs if p["status"].get("install") == "done")
    improve_done = sum(1 for p in packs if p["status"].get("improve") == "done")
    indexed_done = sum(1 for p in packs if p["status"].get("indexed") == "done")
    registered_done = sum(1 for p in packs if p["status"].get("registered"))
    deprecate = sum(1 for p in packs if p["status"].get("improve") == "deprecate-candidate")

    badges = " ".join([
        badge("packs", n, "blue"),
        badge("install", f"{install_done}/{n}", "brightgreen" if install_done else "lightgrey"),
        badge("improve", f"{improve_done}/{n}", "green" if improve_done else "orange"),
        badge("indexed", f"{indexed_done}/{n}", "green" if indexed_done else "orange"),
        badge("registered", f"{registered_done}/{n}", "green" if registered_done else "orange"),
        badge("deprecate", deprecate, "yellow" if deprecate else "lightgrey"),
    ])

    lines = [
        badges,
        "",
        "| Pack | Origin | Ver | Install | Improve | Indexed | Registered |",
        "|---|---|---|:--:|:--:|:--:|---|",
    ]
    for p in packs:
        s = p["status"]
        lines.append(
            f"| `{p['name']}` | {p['origin']} | {p['version']} | "
            f"{cell(INSTALL, s.get('install'))} | "
            f"{cell(IMPROVE, s.get('improve'))} | "
            f"{cell(INDEXED, s.get('indexed'))} | "
            f"{registered_cell(s.get('registered'))} |"
        )
    lines += [
        "",
        f"_Legend: ✅ done · 🟡 partial/in-progress · ⬜ todo · ⚠️ dep = deprecate-candidate. "
        f"{n} packs · {install_done} installed · {deprecate} flagged for deprecation. "
        f"Generated from `registry.yaml` by `scripts/gen_readme.py` — do not edit by hand._",
    ]
    return "\n".join(lines)


def main() -> int:
    check = "--check" in sys.argv
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    matrix = build_matrix(data)

    readme = README.read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        sys.exit(f"README markers missing: expected {START} ... {END}")
    pre = readme.split(START)[0]
    post = readme.split(END)[1]
    new = f"{pre}{START}\n{matrix}\n{END}{post}"

    if check:
        if new != readme:
            print("README status matrix is STALE — run: python scripts/gen_readme.py")
            return 1
        print("README status matrix is up to date.")
        return 0

    README.write_text(new, encoding="utf-8")
    print(f"README matrix regenerated from {len(data.get('packs', []))} packs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
