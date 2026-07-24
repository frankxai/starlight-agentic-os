# starlight-skill-index — an MCP server that makes a skill library routable

`io.github.frankxai/starlight-skill-index` turns Frank's semantic skill index
into a set of tools any MCP-speaking AI CLI can call. It wraps the `index/`
package (a retriever→reranker over a pgvector store of e5 embeddings, a
`catalog.json` of every skill, and a frontmatter security scanner) and exposes
four tools:

| Tool | What it does |
|------|--------------|
| `search_skills(query, k=5)` | Ranked skills for a task: `[{id, name, pack, score, description}]`. |
| `get_skill(skill_id)` | Full metadata for one skill + a body-path/preview when resolvable. |
| `list_packs()` | Every pack with its skill count — a map of the library. |
| `security_report()` | Latest frontmatter scan: severity counts + flagged skill ids. |

---

## Why this exists — the token-saving router pitch

A skill library grows without bound. The naive way to route is to paste **every**
skill's name + description into the model's context so it can pick one. That is
`O(N)` tokens **on every turn**, and it stops scaling after a few dozen skills.
With 400+ skills it is simply unaffordable.

This server inverts that. The agent calls `search_skills("draft a sell-side
teaser")` and gets back a **short ranked list** — typically the top 3–5. It then
calls `get_skill` on the winner and loads **exactly one** skill body. The router
pays for a tiny query + a tiny ranked list instead of the entire catalog, and
only the chosen skill's tokens ever enter the window.

> **The contract for agents:** call `search_skills` *before* grepping the repo or
> hand-writing code for a task that might already be a skill. It is faster, ranks
> by meaning, and keeps context small. The tool descriptions are written to make
> this obvious to an LLM reading them.

---

## Modes: vector path vs. graceful fallback (honest status)

There are two ranking backends, and **every response tells you which one ran**
via a `mode` field:

- **`vector`** — the real deal: `index/search.py` runs a two-stage
  retrieve→rerank over `PostgreSQL + pgvector` with `intfloat/multilingual-e5-base`
  embeddings. Best quality. **This path is authored but NOT yet built** — it needs
  a Postgres+pgvector instance, `pip install '.[vector]'` (pulls torch + ~1 GB of
  model weights), and an index build (`index/build_index.py`). Until then you will
  not see this mode.
- **`catalog-fallback`** — pure standard library: TF-IDF cosine over each skill's
  `name + description + pack`, blended with a keyword-overlap boost. Needs nothing
  but `catalog.json`. This is what runs today, so the server is **useful before any
  embeddings exist**. It is a solid keyword-aware ranker; it is not as strong as
  the vector path on paraphrased/semantic queries.

The switch is automatic: if `STARLIGHT_DB_URL` (or `DATABASE_URL`) is set the
server tries the vector path and **degrades to the fallback on any failure**
(DB down, deps missing, empty store), reporting the reason. If no DB is
configured it goes straight to the fallback.

---

## Install & run

```bash
cd mcp-server
pip install -r requirements.txt        # core only: the MCP SDK (+ stdlib)
python server.py                       # serves over stdio (what clients spawn)
```

Optionally enable the vector path later:

```bash
pip install '.[vector]'                # torch + sentence-transformers + pgvector
export STARLIGHT_DB_URL="postgresql://user:pass@localhost:5432/starlight_skills"
# then build the index per index/README.md; the server picks it up automatically.
```

### Configuration (all environment-based, no secrets in code)

| Variable | Purpose |
|----------|---------|
| `STARLIGHT_CATALOG` | Path to `catalog.json`. Auto-discovers `../index/catalog.json` if unset. |
| `STARLIGHT_INDEX_DIR` | Dir with `search.py` / `scan_skill_frontmatter.py`. Auto-discovered. |
| `STARLIGHT_DB_URL` / `DATABASE_URL` | Postgres URL. Presence enables the vector path. **Secret.** |
| `STARLIGHT_SCAN_REPORT` | Cached `scan_report.json`; else `security_report` scans live. |
| `STARLIGHT_SKILLS_ROOT` | Base dir to resolve a skill's relative `path` to its body. |

---

## Add it to your AI CLI

Use absolute paths. Point `STARLIGHT_CATALOG` at your `catalog.json`.

### Claude Code

One-liner:

```bash
claude mcp add starlight-skill-index \
  --env STARLIGHT_CATALOG=/abs/path/index/catalog.json \
  -- python /abs/path/mcp-server/server.py
```

…or add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "starlight-skill-index": {
      "command": "python",
      "args": ["/abs/path/mcp-server/server.py"],
      "env": { "STARLIGHT_CATALOG": "/abs/path/index/catalog.json" }
    }
  }
}
```

### OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.starlight-skill-index]
command = "python"
args = ["/abs/path/mcp-server/server.py"]
env = { STARLIGHT_CATALOG = "/abs/path/index/catalog.json" }
```

### Gemini CLI

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "starlight-skill-index": {
      "command": "python",
      "args": ["/abs/path/mcp-server/server.py"],
      "env": { "STARLIGHT_CATALOG": "/abs/path/index/catalog.json" }
    }
  }
}
```

Once installed, ask your agent something like *"reconcile QuickBooks against
Stripe"* — it should call `search_skills`, then `get_skill` on the top result.

---

## Test

The fallback path is fully testable with no torch/DB/network:

```bash
pytest test_server.py -q          # with pytest
python test_server.py             # or standalone (stdlib only)
```

The suite builds a tiny inline catalog, asserts ranking/lookup/pack-count
behavior, and confirms the security scanner flags a deliberately-malicious skill.

---

## Publish to the official MCP Registry

The metadata lives in [`server.json`](./server.json) under the **verified**
namespace `io.github.frankxai/starlight-skill-index`. Publish with the official
`mcp-publisher` CLI:

```bash
# 1. Install the publisher (Homebrew, or grab the binary from the registry releases)
brew install mcp-publisher
#    (alt: download from https://github.com/modelcontextprotocol/registry/releases)

# 2. Authenticate — proves you own the io.github.frankxai namespace.
#    Opens a GitHub OAuth device flow; the 'frankxai' account must match the
#    io.github.frankxai namespace and own the repository in server.json.
mcp-publisher login github

# 3. (optional) validate / scaffold — 'init' writes a server.json template if
#    you don't already have one. You do, so this is only for validation.
mcp-publisher init

# 4. Publish ./server.json to the registry.
mcp-publisher publish
```

Ship the `starlight-skill-index` package to PyPI first (so the `pypi` package in
`server.json` resolves), e.g. `python -m build && twine upload dist/*`, then run
`mcp-publisher publish`. To cut a new version, bump `version` in both
`pyproject.toml` and `server.json` and re-run `mcp-publisher publish`.
