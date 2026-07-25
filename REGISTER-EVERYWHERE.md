# Register Everywhere — the operator-registry checklist + publish automation

A pack is not *shipped* until other operators can discover it. This is the checklist and the
publish/write-back contract. [`scripts/syndicate.py`](scripts/syndicate.py) currently validates
only the lifecycle preconditions and prints a dry-run plan. Tag existence, official-schema
validation, external publication, and write-back are not implemented. No publication workflow
exists yet.

> **Precondition (non-negotiable):** only packs with `status.improve: done` and
> `status.indexed: done` may be registered. We never publish an un-hardened pack or skip the
> production-discovery receipt.

---

## The six channels

### 1. Official MCP Registry
- Publish `server.json` via **`mcp-publisher`**.
- Namespace is authenticated by **GitHub OIDC** — the namespace must match the owning GitHub org
  (`frankxai`), so identity is cryptographic, not claimed.
- This is the anchor record; the other channels syndicate *from* it.

### 2. Syndication network
- **Glama**, **Smithery**, **mcp.so**, **PulseMCP** — submit/sync the server metadata.
- Prefer their sync-from-registry paths where they exist, so the official registry stays canonical.

### 3. Own Claude Code marketplace
- Maintain a `marketplace.json` repo so Frank's packs install with one command in Claude Code.
- Append the pack entry; commit; the marketplace repo is itself version-controlled truth.

### 4. Awesome-list PRs
- `punkpeye/awesome-mcp-servers`
- `VoltAgent` (awesome list)
- `RoggeOhta/awesome-codex-cli`
- One PR per list; link back to the official registry record.

### 5. HOL cross-tool aggregator
- Register with the HOL cross-tool aggregator for cross-CLI discoverability.

### 6. CI write-back
- After any successful publish, CI appends the registry id to `registry.yaml`'s
  `status.registered` for that pack, bumps `provenance.last_reviewed`, and regenerates the README
  matrix. **No manual bookkeeping** — the SSOT stays honest automatically.

---

## Publish + write-back contract (what `syndicate.py` must honor)

1. **Input:** a pack name present in `registry.yaml`.
2. **Preconditions:** `improve == done` AND `indexed == done` AND a clean semver tag exists AND
   `.mcp/server.json` validates against the official schema.
3. **Publish:** for each target registry not already in `status.registered`, run its publish step
   (idempotent — already-registered targets are skipped).
4. **Write-back:** append each newly-published registry id to `status.registered`; bump
   `last_reviewed`; invoke `gen_readme.py`.
5. **Audit:** append one JSONL line per publish to `syndication-log.jsonl`
   `{ts, pack, version, registry, result, url}` — append-only; the log is the truth, not the API
   response (mirrors the hermes / SIS ledger pattern).

---

## Checklist template (copy per pack)

```
Pack: <name>   Version: <semver>
[ ] improve == done (evals passing, provenance recorded)
[ ] indexed == done (production discovery receipt recorded)
[ ] .mcp/server.json validates
[ ] Official MCP Registry (mcp-publisher, OIDC namespace = frankxai)
[ ] Glama
[ ] Smithery
[ ] mcp.so
[ ] PulseMCP
[ ] Claude Code marketplace.json updated
[ ] awesome-mcp-servers PR
[ ] awesome-codex-cli PR (if Codex-relevant)
[ ] VoltAgent PR
[ ] HOL aggregator
[ ] registry.yaml status.registered written back + README regenerated
```

---

## Security note

Registry descriptions and skill frontmatter are consumed by routers *as instructions*. Before any
publish, the CI skill-description/frontmatter scan (Phase D) must pass — a poisoned description is
a supply-chain injection vector, not a cosmetic issue. Do not register a pack that fails the scan.
