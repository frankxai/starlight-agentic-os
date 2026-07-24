#!/usr/bin/env python3
"""Normalize gen_catalog raw output into the day-one catalog.json.

- Derives repo / pack / origin from each entry's recorded absolute path.
- Folds the duplicate plugin copies (inline / cache / data / repos / marketplaces)
  into one marketplace identity, then dedups by (repo, pack, name).
- Strips body_path (absolute host paths must not enter the public repo).
Deterministic; no network. One-off helper, kept in-repo for reproducibility.
"""
import json, re, sys
from pathlib import Path

RAW = Path("catalog.raw.json")
OUT = Path("catalog.json")

# repo dir substring -> (repo, pack, origin) for the first-party repos
REPO_MAP = [
    ("/agentic-creator-os/", "agentic-creator-os", "agentic-creator-os", "original"),
    ("/arcanea/", "arcanea", "arcanea", "original"),
    ("/frankx/.claude/", "frankx", "frankx", "original"),
    ("/starlight-intelligence-system/", "starlight-intelligence-system", "starlight-intelligence-system", "original"),
    ("/starlight-gravity-engine/", "starlight-gravity-engine", "starlight-gravity-engine", "original"),
]

# marketplace token -> origin (Frank's vs vendored)
PLUGIN_ORIGIN = {
    "agentic-creator-skills": "original",
    "frankx-app-forge": "original",
    "app-studio-team": "original",
    "superpowers": "absorbed",
    "claude-plugins-official": "absorbed",
    "anthropics": "absorbed",
    "vercel": "absorbed",
    "playwright": "absorbed",
    "serena": "absorbed",
    "context7": "absorbed",
    "ralph-loop": "absorbed",
    "typescript-lsp": "absorbed",
    "pdf-viewer": "absorbed",
}


def plugin_marketplace(p: str) -> str:
    """Best-effort marketplace/plugin identity from a plugins/ path."""
    for tok in PLUGIN_ORIGIN:
        if tok in p:
            return tok
    # fall back to the segment after plugins/<bucket>/
    m = re.search(r"/plugins/(?:marketplaces|cache|data|repos)/([^/]+)/", p)
    if m:
        return re.sub(r"-(inline|claude-plugins-official|marketplace)$", "", m.group(1))
    return "plugins-misc"


def classify(entry):
    bp = str(entry.get("body_path") or "").replace("\\", "/").lower()
    for sub, repo, pack, origin in REPO_MAP:
        if sub in bp:
            return repo, pack, origin
    if "/.claude/plugins/" in bp:
        mk = plugin_marketplace(bp)
        return "plugins", mk, PLUGIN_ORIGIN.get(mk, "absorbed")
    return entry.get("repo") or "unknown", entry.get("pack") or None, entry.get("origin") or "local"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    seen, out = set(), []
    for e in raw:
        repo, pack, origin = classify(e)
        name = e.get("name") or ""
        key = (repo, pack, name.lower())
        if key in seen:
            continue
        seen.add(key)
        base = f"{pack}:{name}" if pack else name
        out.append({
            "id": base,
            "name": name,
            "description": e.get("description") or "",
            "pack": pack,
            "repo": repo,
            "path": e.get("path") or "",
            "origin": origin,
            "maturity": e.get("maturity") or "unknown",
        })
    # unique ids
    used = {}
    for o in out:
        b = o["id"]
        if b in used:
            used[b] += 1
            o["id"] = f"{b}-{used[b]}"
        else:
            used[b] = 0
    out.sort(key=lambda x: x["id"])
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # stats
    from collections import Counter
    by_repo = Counter(o["repo"] for o in out)
    by_origin = Counter(o["origin"] for o in out)
    print(f"catalog.json: {len(out)} skills (deduped from {len(raw)} raw)")
    print("by repo:", dict(by_repo))
    print("by origin:", dict(by_origin))


if __name__ == "__main__":
    sys.exit(main())
