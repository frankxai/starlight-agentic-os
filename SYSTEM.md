# Starlight Agentic OS — System

## Purpose

Maintain auditable lifecycle truth for every agent pack Frank runs, improves,
indexes, or publishes.

## Authority Map

| Concern | Authority |
| --- | --- |
| Pack lifecycle and publication state | `registry.yaml` in this repository |
| Pack implementation | The pack's owning repository |
| Cross-pack evaluation methods | `frankxai/starlight-evals` |
| Design and motion quality | `frankxai/starlight-design-intelligence` |
| Fleet policy | `frankxai/starlight-agent-config` |
| Machine and portfolio operations | `frankxai/agentic-ops-hub` |
| Starlight protocol and product canon | `frankxai/Starlight-Intelligence-System` |

## Lifecycle

```text
installed → improved → indexed → registered
```

- **Installed** means present and working in at least one supported harness.
- **Improved** means the declared version and exact pack bytes have passed the
  pack's quality suite and have an independent certification receipt.
- **Indexed** means the current version is discoverable through a verified
  router or catalog.
- **Registered** means an external registry record was inspected and recorded.

No later state implies an earlier state unless the registry explicitly records
both.

## Runtime

The repository ships one executable component: `mcp-server/`, the local-first
`starlight-skill-index` router.

- Default transport for one operator: stdio.
- Shared local transport: streamable HTTP on `127.0.0.1:8631/mcp`.
- Default retrieval: committed catalog fallback.
- Optional retrieval: Postgres + pgvector when explicitly configured.
- Public exposure: prohibited without an authenticated proxy and a separate
  security review.

## Data

- Persistent authority: Git.
- Catalog data: public repository metadata and skill frontmatter/body indexes.
- PII: prohibited.
- Secrets: prohibited in repository content, receipts, logs, and examples.

## Promotion

Repository changes require CI and independent verification. Public package or
registry publication additionally requires named-human approval. Roll back by
reverting the bounded commit or restoring the last certified version.
