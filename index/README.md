# Starlight Agentic OS — Phase D: Semantic Skill Index

A local-first, semantic index that makes a large library of `SKILL.md`
agent-skills discoverable to AI agents. Instead of stuffing every skill's
name + description into the router prompt (which does not scale and burns
tokens), a router calls `search.py` with a natural-language task and gets back
the top-_k_ most relevant skills, ranked over their **full bodies**.

> **Status (mixed).** The **stdlib path IS executed and real**; the **vector path is authored, NOT run.**

---

## Phase D execution receipt — 2026-07-24

Run on a memory-constrained box (stdlib + PyYAML only; no ML, no Postgres):

| Step | Status | Result |
|---|---|---|
| `gen_catalog.py` over 5 repos + the `.claude/plugins` dir | ✅ **executed** | `catalog.json` — **418 skills** (deduped from 493 raw) across `agentic-creator-os` (104), `arcanea` (124), `plugins` (126), `frankx` (33), `starlight-intelligence-system` (31). Host paths stripped (public repo). |
| `scan_skill_frontmatter.py` over the catalog | ✅ **executed** | `security-scan-report.json` — 418 scanned, **3 flagged (1 high, 2 medium)**; all triaged **benign** (see `security-scan-summary.md`). |
| `build_index.py` / `search.py` / `schema.sql` (embeddings + pgvector) | ⏳ **authored, NOT run** | needs PostgreSQL + pgvector + `pip install -r index/requirements.txt` (torch + ~1.1 GB e5 weights). |

`_normalize.py` is the one-off helper that derived repo/pack/origin from the paths
`gen_catalog.py` recorded and stripped absolute host paths before commit — kept in-repo
for provenance. Build the full vector index later with the run sequence below.

---

## Architecture

```
 repos of SKILL.md ──► gen_catalog.py ──► catalog.json
                                             │
                          scan_skill_frontmatter.py  (CI security gate)
                                             │
                                             ▼
 catalog.json ──► build_index.py ──► [ PostgreSQL + pgvector ]
                    (e5 "passage:" embeddings,               ▲
                     incremental by content_hash)            │
                                                             │
 agent / router ──► search.py("query") ──► retrieve (HNSW) ──┘
                        (e5 "query:")        └─► rerank over full bodies ─► top-k
```

- **Embedding model:** `intfloat/multilingual-e5-base` (768-dim), run locally
  via `sentence-transformers`. e5 requires prefixes: passages are embedded with
  `"passage: "`, queries with `"query: "`. Both are handled for you.
- **Vector store:** PostgreSQL + pgvector, HNSW cosine index.
- **Two-stage retrieval:** ANN retrieve → rerank (cross-encoder if available,
  else cosine) over full skill bodies.

---

## Files

| File | Purpose |
|------|---------|
| `schema.sql` | pgvector schema: `skills` table + HNSW ANN index. |
| `gen_catalog.py` | Walk repo roots, parse `SKILL.md` frontmatter → `catalog.json`. |
| `scan_skill_frontmatter.py` | Security scanner / CI gate for router-hijack + injection. |
| `build_index.py` | Embed bodies locally, upsert into pgvector (incremental). |
| `search.py` | `search(query, k)` retriever→reranker. Router entry point. |
| `requirements.txt` | Python dependencies. |

---

## Run sequence

Assumes PostgreSQL is running and you can connect. Set the DB URL once:

```bash
# POSIX
export STARLIGHT_DB_URL="postgresql://user:pass@localhost:5432/starlight_skills"
```
```powershell
# Windows PowerShell
$env:STARLIGHT_DB_URL = "postgresql://user:pass@localhost:5432/starlight_skills"
```

```bash
# 0. install deps (first run only; downloads model weights)
pip install -r index/requirements.txt

# 1. create the database + schema (enables pgvector, creates table + HNSW index)
createdb starlight_skills
psql "$STARLIGHT_DB_URL" -f index/schema.sql

# 2. generate the catalog from your skill repos
python index/gen_catalog.py --roots ./skills ../more-skills --out catalog.json

# 3. SECURITY GATE — scan frontmatter; non-zero exit on HIGH severity
python index/scan_skill_frontmatter.py --catalog catalog.json --json scan_report.json
#    (in CI: run this before build_index and fail the pipeline on non-zero exit)

# 4. build/refresh the index (incremental: only changed skills are re-embedded)
python index/build_index.py --catalog catalog.json         # uses STARLIGHT_DB_URL
#    add --prune to delete skills no longer present in the catalog

# 5. query it
python index/search.py "reconcile quickbooks against stripe payouts" -k 5
python index/search.py "draft a sell-side teaser" -k 5 --json
```

Credentials precedence for `--db-url`: `--db-url` flag → `STARLIGHT_DB_URL` →
`DATABASE_URL` → standard libpq `PG*` env vars. **No secret is hardcoded.**

---

## Router-integration contract

The whole point is to cut skill-token cost: the router never sees all skills,
only the handful `search.py` returns. There are two integration paths.

### 1. In-process (preferred)

```python
from search import search

hits = search("summarize a legal contract's risky clauses", k=3)
# hits: List[SkillHit]; already ranked best-first.
if hits:
    chosen = hits[0]
    load_skill(chosen.path)          # only now pay the token cost of the body
```

### 2. Subprocess / JSON (language-agnostic)

```bash
python index/search.py "<task>" -k 5 --json
```

Emits a stable JSON contract on stdout:

```json
{
  "query": "<task>",
  "k": 5,
  "results": [
    {
      "id": "finance:reconciliation",
      "name": "reconciliation",
      "description": "...",
      "pack": "finance",
      "repo": "...",
      "path": "finance/reconciliation/SKILL.md",
      "origin": "local",
      "maturity": "stable",
      "retriever_score": 0.83,     // cosine similarity from ANN stage
      "rerank_score": 6.12,        // cross-encoder logit, or cosine if fallback
      "reranked_by": "cross-encoder"
    }
  ]
}
```

Exit codes: `0` = results returned, `2` = no match, `1` = error.
Optional filters: `--pack <name>` and `--maturity <level>` push metadata
constraints down into SQL before ranking.

**Contract guarantee:** results are sorted best-first by `rerank_score`; a
router can take `results[0]` (or apply its own threshold on `rerank_score` /
`retriever_score`) and load only that skill's body.

---

## Operational notes

- **Incremental builds:** re-running `build_index.py` only re-embeds skills
  whose `content_hash` (sha256 of name+description+body) changed. Safe and cheap
  to run on every commit.
- **Long bodies:** bodies over the model window are chunked and the chunk
  embeddings are **mean-pooled** (not truncated) so whole-body signal survives.
- **Offline:** after the first model download, set `HF_HUB_OFFLINE=1` to run
  fully offline.
- **Cross-encoder optional:** if the reranker model can't load, search
  transparently falls back to cosine re-scoring (`reranked_by: "cosine"`).
- **CI gate:** `scan_skill_frontmatter.py --fail-on high` (default) blocks a
  poisoned skill from entering the index.
