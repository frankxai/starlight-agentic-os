#!/usr/bin/env python3
"""
syndicate.py — publish a pack to the operator registries, then write the result
back into registry.yaml (the SSOT). STUB: contract defined, network calls TODO.

The publish/write-back contract this script MUST honor:

  1. INPUT      : a pack name present in registry.yaml.
  2. PRECONDS   : pack.status.improve == "done"  (never syndicate un-hardened packs)
                  AND pack.version is a clean semver tag that exists in the repo.
                  AND .mcp/server.json validates against the official schema.
  3. PUBLISH    : for each target registry not already in status.registered:
                    - official-mcp-registry : `mcp-publisher publish` (GitHub-OIDC namespace)
                    - glama / smithery / mcp.so / pulsemcp : syndication API / PR
                    - claude-code-marketplace : append to marketplace.json, commit
                    - awesome-lists : open a PR to the relevant list
  4. IDEMPOTENT : re-running is a no-op for registries already recorded.
  5. WRITE-BACK : append each newly-published registry id to pack.status.registered
                  in registry.yaml, bump provenance.last_reviewed, then invoke
                  gen_readme.py so the README matrix reflects the new state.
  6. AUDIT      : every publish emits one JSONL line to ./syndication-log.jsonl
                  {ts, pack, version, registry, result, url}  (append-only, mirrors
                  the hermes/SIS ledger pattern — the log is the truth, not the API).

Nothing here mutates a registry yet. Wire step 3 per REGISTER-EVERYWHERE.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML not installed.")

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry.yaml"

TARGETS = [
    "official-mcp-registry",
    "glama",
    "smithery",
    "mcp.so",
    "pulsemcp",
    "claude-code-marketplace",
    "awesome-lists",
    "hol-aggregator",
]


def load() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def find(data: dict, name: str) -> dict | None:
    return next((p for p in data.get("packs", []) if p["name"] == name), None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Syndicate a pack to operator registries (STUB).")
    ap.add_argument("pack", help="pack name as listed in registry.yaml")
    ap.add_argument("--dry-run", action="store_true", help="print plan, publish nothing")
    args = ap.parse_args()

    data = load()
    pack = find(data, args.pack)
    if pack is None:
        sys.exit(f"pack '{args.pack}' not found in registry.yaml")

    if pack["status"].get("improve") != "done":
        sys.exit(
            f"REFUSED: '{args.pack}' improve status is "
            f"'{pack['status'].get('improve')}', not 'done'. "
            "Only hardened packs may be syndicated (see contract precondition 2)."
        )

    already = set(pack["status"].get("registered") or [])
    todo = [t for t in TARGETS if t not in already]

    print(f"[plan] pack={args.pack} version={pack['version']}")
    print(f"[plan] already registered: {sorted(already) or '(none)'}")
    print(f"[plan] would publish to  : {todo or '(all done)'}")

    if args.dry_run or not todo:
        return 0

    # TODO(Phase E): implement publish steps 3-6 per REGISTER-EVERYWHERE.md,
    # then write status.registered back into registry.yaml and call gen_readme.py.
    print("[stub] publish + write-back not yet implemented — see REGISTER-EVERYWHERE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
