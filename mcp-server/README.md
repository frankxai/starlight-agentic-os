# starlight-skill-index — an MCP server that makes a skill library routable

<!-- mcp-name: io.github.frankxai/starlight-skill-index -->

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

# Recommended: ONE shared service, many clients (see "Why shared" below).
python server.py --http                # http://127.0.0.1:8631/mcp  (one process)

# Or single-user local: stdio (one process per client).
python server.py                       # serves over stdio
```

### Why a shared HTTP server (RAM)

`stdio` spawns **a new server process per client** — every CLI *and every subagent*
forks its own copy and (on the vector path) loads its own embedding model, so RAM is
duplicated N times. Run **one** `--http` service and point every CLI at its URL:
**one process, one catalog, one model, many clients.** The catalog + fallback ranker
are a lazy singleton warmed once at startup (`warm_singletons()`); the vector model is
cached in `sys.modules`. Deploy it as an always-on service — see
[`deploy/`](deploy/) (Windows Task Scheduler + systemd). Override the port with
`STARLIGHT_HTTP_PORT`; `STARLIGHT_TRANSPORT=http|sse|stdio` also selects the mode.
Unauthenticated shared transport is fixed to `127.0.0.1`; any other
`STARLIGHT_HTTP_HOST` value fails closed.

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
| `STARLIGHT_SKILLS_ROOT` | Explicit trust root containing every skill body the server may read. Traversal and symlink escape fail closed. |

---

## Add it to your AI CLI

**Preferred — point every CLI at the ONE shared HTTP service** (start it once with
`python server.py --http`, or install it as an always-on service via [`deploy/`](deploy/)).
Many clients, one process, no per-subagent model/catalog duplication.

### Claude Code

```bash
claude mcp add --transport http starlight-skill-index http://127.0.0.1:8631/mcp
```

…or `.mcp.json`:

```json
{
  "mcpServers": {
    "starlight-skill-index": { "type": "http", "url": "http://127.0.0.1:8631/mcp" }
  }
}
```

### OpenAI Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.starlight-skill-index]
url = "http://127.0.0.1:8631/mcp"          # shared HTTP service
```

### Gemini CLI

`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "starlight-skill-index": { "httpUrl": "http://127.0.0.1:8631/mcp" }
  }
}
```

Once connected, ask your agent something like *"reconcile QuickBooks against
Stripe"* — it should call `search_skills`, then `get_skill` on the top result.

<details>
<summary><b>Alternative — stdio spawn (single-user local, spawns per client)</b></summary>

Use only if you don't want a shared service. Note this spawns one server process
per client/subagent and duplicates RAM — prefer the shared HTTP mode above.

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
Claude Code one-liner: `claude mcp add starlight-skill-index --env STARLIGHT_CATALOG=/abs/path/index/catalog.json -- python /abs/path/mcp-server/server.py`
(Codex `command`/`args`, Gemini `command`/`args` follow the same stdio shape.)
</details>

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
