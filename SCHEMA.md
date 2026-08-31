# Starlight Agentic OS — Schemas

## Registry

`registry.yaml` is the canonical pack registry.

Required pack fields:

- `name`, `repo`, `version`, `license`, `source_url`, `origin`, `summary`
- `status.install`: `todo | partial | done`
- `status.improve`: `todo | in-progress | done | deprecate-candidate`
- `status.indexed`: `todo | in-progress | done`
- `status.registered`: verified external registry identifiers only
- `provenance.checksum`: `sha256:<hex>` when `improve: done`
- `provenance.certification`: repository-relative receipt path when
  `improve: done`

## Pack Certification

Receipts conform to `starlight.pack_certification.v1` and live at:

```text
certifications/<pack>/<version>.json
```

The receipt binds:

- pack and version;
- owning repository and artifact root;
- source commit;
- stable SHA-256 directory digest, file count, and byte count;
- exact test commands and outcomes;
- maker and independent verifier;
- verification timestamp and verdict.

The certification commit must be later than the source commit. No pack bytes may
change between the certified source commit and the receipt head.

## MCP Manifest

`mcp-server/server.json` follows the official dated MCP Registry schema. Package
publication and registry registration are separate states:

- the complete official Draft 7 schema is vendored at
  `schemas/mcp-server-2025-12-11.schema.json`;
- `scripts/validate_repo.py` validates every manifest field against that pinned
  schema before applying repository-specific identity checks;
- a valid manifest is not a published package;
- a published package is not a registered MCP server;
- a registry record is recorded only after external inspection.

## Cross-Repository Contracts

This repository references, but does not redefine:

- `starlight.repo_profile.v2`
- `starlight.operation_receipt.v1`
- `starlight.run_receipt.v1`
- design release evidence from `starlight-design-intelligence`

## Ecosystem drift

Official plugin/MCP/marketplace sources live in
`registry/ecosystem-drift/watchlist.json`. The collector
(`scripts/ecosystem_drift_collect.py`) is deterministic and no-LLM. It writes
local state under the Hermes cache, not git. A digest change is evidence of
source movement, not an adoption or publication decision. Material events open
or update one `[ecosystem-drift]` GitHub issue; they do not create repositories
or rewrite PRs. See `docs/ECOSYSTEM-DRIFT.md`.
