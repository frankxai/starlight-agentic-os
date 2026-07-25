# Register Playbook — the one-command-when-ready Phase E sequence

*The exact publish sequence for `starlight-skill-index` (the MCP server in [`mcp-server/`](mcp-server/)).
**Authored, NOT run** — nothing here has been executed. Fire it from a machine with `mcp-publisher`,
network, and the `frankxai` GitHub login. This is the operator checklist; the reusable contract lives
in [`REGISTER-EVERYWHERE.md`](REGISTER-EVERYWHERE.md).*

> **Preconditions (verify before firing):**
> - Pack `improve == done` (**not yet satisfied**; package tests pass, but eval, provenance
>   checksum, and live-observability receipts remain incomplete).
> - Pack `indexed == done` (**not yet satisfied**; record a production discovery receipt first).
> - `mcp-server/server.json` validates ✅ and `repository.url` points at the real repo
>   (`https://github.com/frankxai/starlight-agentic-os`, subfolder `mcp-server`) ✅.
> - The runnable artifact is reachable by the registry's declared install path (see step 0 —
>   the `server.json` currently declares a **pypi** package `starlight-skill-index@0.1.0`, which
>   must exist on PyPI *or* be switched to a github-source package before publish).

---

## Step 0 — Decide the package channel (one-time)

`server.json` declares a `pypi` package with `runtimeHint: uvx`. Two honest options:

- **(a) Publish to PyPI first** (matches the current `server.json`):
  ```bash
  cd mcp-server
  python -m build            # needs pyproject.toml (present) + `pip install build`
  python -m twine upload dist/*   # requires a PyPI account/token for 'starlight-skill-index'
  ```
- **(b) Switch to a GitHub-source package** (no PyPI needed) — edit `mcp-server/server.json`
  `packages[0]` to a `registryType: "oci"`/github source, or ship as an `mcpb` bundle. Simpler if
  you don't want a PyPI release. **Pick one before step 2.**

---

## Step 1 — Authenticate the namespace (GitHub OIDC)

```bash
mcp-publisher login github
# Opens the GitHub OAuth flow for account `frankxai`. This is what verifies the
# namespace `io.github.frankxai/...` — the registry checks the server.json name
# and repository owner against this login. No token is stored in the repo.
```

## Step 2 — Publish to the Official MCP Registry

```bash
cd mcp-server
mcp-publisher publish --file server.json
# Publishes io.github.frankxai/starlight-skill-index. This is the anchor record;
# the syndication network (step 3) syncs FROM it.
```
Verify:
```bash
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=starlight-skill-index" | jq .
```

## Step 3 — Syndicate to the network

Most sync from the official registry; where a manual submit is needed:

| Registry | Action |
|---|---|
| **Glama** (glama.ai/mcp) | Auto-discovers from the official registry + GitHub; then **claim** the server on your Glama account. |
| **Smithery** (smithery.ai) | Submit the repo; Smithery builds/hosts. Enables the Toolbox router. |
| **mcp.so** | Submit the server URL / repo. |
| **PulseMCP** | Submit for hand-review. |
| **punkpeye/awesome-mcp-servers** | Open a PR adding the row (link the official-registry record). |

Automated form (once wired): `python scripts/syndicate.py starlight-skill-index` — it must (a) refuse
unless `improve == done` and `indexed == done`, (b) publish to each target not already in
`status.registered`, (c) write the registry ids back into `registry.yaml`, (d) regenerate the README matrix, (e) append to
`syndication-log.jsonl`. Contract in [`REGISTER-EVERYWHERE.md`](REGISTER-EVERYWHERE.md).

## Step 4 — Claude Code marketplace

Publish the pack to Frank's own marketplace so it installs with one command:

```jsonc
// marketplace.json  (in the marketplace repo, or add a marketplace.json here)
{
  "name": "frankx-starlight",
  "plugins": [
    {
      "name": "starlight-skill-index",
      "source": "github:frankxai/starlight-agentic-os",
      "subfolder": "mcp-server",
      "description": "Semantic skill router (search_skills/get_skill/list_packs/security_report)."
    }
  ]
}
```
Install path for users: `/plugin marketplace add frankxai/<marketplace-repo>` → `/plugin install starlight-skill-index`.

## Step 5 — Write status back (close the loop)

After each successful channel, record it in `registry.yaml`:
```yaml
# packs: - name: starlight-skill-index
#   status: { ..., registered: [official-mcp-registry, glama, smithery, mcp.so, pulsemcp, claude-code-marketplace] }
```
then `python scripts/gen_readme.py` so the matrix reflects it. CI (`refresh-status.yml`) can do this
automatically once wired.

---

## Post-publish smoke (any MCP client)

```jsonc
// Claude Code / Codex / Gemini MCP config (see mcp-server/README.md for per-CLI snippets)
{ "mcpServers": { "starlight-skill-index": {
    "command": "uvx", "args": ["starlight-skill-index"] } } }
```
Then in-agent: call `search_skills("review a github pull request")` → expect a ranked list
(top hit today, catalog-fallback mode, is `arcanea:github-code-review`). Set `STARLIGHT_DB_URL`
to flip to the stronger vector path once the pgvector index is built.

---

*Nothing in this playbook has been executed. Run it only after both `improve: done` and
`indexed: done` receipts exist and Frank is on a networked machine with `mcp-publisher` installed
and the `frankxai` GitHub login available.*
