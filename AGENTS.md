# Starlight Agentic OS — Repository Contract

This repository is the command center for the agent-pack program. It owns the
pack registry, lifecycle state, portable-pack convention, skill index, and the
`starlight-skill-index` MCP artifact.

## Ownership boundaries

- `registry.yaml` owns pack inventory and lifecycle state.
- `starlight-agent-config` owns cross-repository release policy.
- `starlight-evals` owns shared evaluation receipts and evaluation infrastructure.
- `Starlight-Intelligence-System` owns protocol, canon, and governance doctrine.
- `agentic-ops` / `agentic-ops-hub` own portfolio execution state.
- Each pack repository owns its implementation, version, tests, and release.

Do not duplicate those responsibilities here. This repository aggregates
evidence; it does not declare another repository healthy by assertion.

## Truth precedence

When sources disagree, use this order:

1. executed test or production receipt;
2. machine-readable registry or generated artifact;
3. current implementation;
4. documentation;
5. roadmap or proposal.

`authored`, `configured`, `scaffolded`, and `planned` are not synonyms for
`executed`, `verified`, `published`, or `registered`.

Lifecycle states advance one step at a time:

`installed → improved → indexed → registered`

Set a state to `done` only when its evidence is inspectable and its owning
repository still matches that evidence.

`index/catalog.json` is a staging inventory. Presence there does not make a pack
`indexed: done`; production-index status requires `improve: done` first.

`improve: done` requires a non-null provenance checksum and inspectable
`improve_receipts` for `eval`, `safety`, and `observability`. Every receipt is an
object whose `ref` identifies a repository-contained regular file and whose
`sha256` matches the file's bytes. Remote URLs, missing files, directories,
authored configs, passing smoke tests, bare strings, or a narrative note alone
are not completion receipts.

## Required verification

Before opening or updating a pull request, run:

```bash
python scripts/verify_repo.py
python scripts/validate_server_json.py
python mcp-server/test_server.py
python index/test_scan_skill_frontmatter.py
python scripts/test_verify_repo_contract.py
python -m compileall -q index mcp-server scripts
python scripts/sync_mcp_assets.py --check
python -m build --wheel --sdist mcp-server
python scripts/test_built_distribution.py
```

`scripts/verify_repo.py` is the repository-wide gate. It verifies registry
schema and lifecycle values, generated README freshness, catalog and scan
integrity, public-path hygiene, official MCP server-schema validity,
MCP version/provenance alignment, and declared repository paths.

## Security findings

The routing-visible portion of a skill is a supply-chain boundary.

- Unallowlisted high-severity scanner findings block release.
- An exception must bind the skill id, rule, and SHA-256 of the exact evidence.
- A changed finding invalidates the exception.
- Stale or duplicate exceptions fail verification.
- Never reduce scanner severity or broaden a pattern to make CI green.

## Public claims and publication

- Do not advertise a package, repository, registry entry, domain, integration,
  or hosted capability unless an anonymous user can inspect or use it.
- Keep private repositories and unpublished packages out of public install paths.
- Publishing to external registries, changing domains, sending messages, or
  enrolling audiences remains a named human gate.
- Generated status blocks must be regenerated from their source; never edit them
  by hand.

## Change discipline

- Work on a branch; do not push unreviewed program changes directly to `main`.
- Preserve unrelated changes and keep mechanical normalization separate from
  semantic changes.
- Do not add another agent framework, registry, memory system, or observability
  sink without replacing or explicitly subordinating an existing one.
- A public release requires a maker, an independent verifier, exact commit and
  CI receipts, and a rollback path.
