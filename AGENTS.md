# Repository Instructions

`starlight-agentic-os` is the portfolio command center for agent-pack lifecycle
truth. It does not own the packs, fleet runtime, design system, or product
surfaces it tracks.

## Read First

Before changing architecture, lifecycle status, publishing, or certification,
read:

- `SYSTEM.md`
- `SCHEMA.md`
- `SKILLS.md`
- `RUNBOOK.md`
- `TESTING.md`
- `SECURITY.md`

## Invariants

- `registry.yaml` is the lifecycle source of truth.
- A pack moves only through `install → improve → indexed → registered`.
- `improve: done` requires a committed certification receipt for the exact pack
  bytes and version.
- `registered` contains only externally verified registry records. A workflow
  plan, manifest, package build, or dry run is not registration.
- Publishing and syndication paths fail closed. Never leave a green workflow
  that only echoes a TODO or ignores an error.
- Claims in generated README status must be derivable from committed evidence.
- Keep portable contracts vendor-neutral: `AGENTS.md`, `SKILL.md`, and MCP.
- Never expose the local skill router beyond loopback without authentication.

## Repository Boundaries

- `starlight-agentic-os`: pack registry, lifecycle, portable convention, router,
  and publication preflight.
- `starlight-design-intelligence`: brand packs, UI/UX, imagery, motion, and web
  release evidence.
- `starlight-agent-config`: fleet policy and agent configuration.
- `starlight-evals`: cross-pack evaluation methodology and receipts.
- `Starlight-Intelligence-System`: protocol and product canon.
- `agentic-ops-hub`: machine and portfolio operating state.

Do not duplicate those authorities here.

## Required Checks

Run before handoff:

```bash
python3 scripts/validate_repo.py
python3 mcp-server/test_server.py
python3 index/test_scan_skill_frontmatter.py
python3 -m unittest discover -s tests -p 'test_*.py'
bash portable/verify-portability.sh portable/packs/acos-meta
python3 scripts/verify_certifications.py --all
python3 scripts/gen_readme.py --check
python3 scripts/sync_mcp_assets.py --check
python3 -m build --wheel --sdist mcp-server
python3 scripts/test_built_distribution.py
python3 -m compileall -q index mcp-server portable scripts
```

## Change Discipline

- Work on a bounded branch from current `main`.
- Preserve unrelated work and do not force-push shared branches.
- Version behavior changes. The version is the evaluation contract.
- Record exact commands and outcomes in certifications; do not backfill a
  passing receipt from memory.
- Keep maker, verifier, and named human approval distinct for public releases.

## Human Gates

Named-human approval is required for public package publication, registry
publication, secrets, permissions, billing, spend, DNS, destructive operations,
external messages, and changes to the core brand identity.

## Design Routing

When a task includes UI, UX, motion, imagery, or a public surface, route through
`frankxai/starlight-design-intelligence`. This repository may enforce that
contract, but it must not invent a second design authority.
