# Pack Index Template — the copy-me "Indexed" pattern

*How a pack becomes **discoverable to our own agents** — the third lifecycle state. The pipeline
and the router contract live in [`index/`](index/); this doc is the pattern to reuse.*

> **"Indexed" = an agent can semantically find a pack's skills without loading them all.**
> Names + descriptions don't scale; a two-stage retriever→reranker over full skill bodies does.
> Reference: SkillRouter (arXiv 2606.03565); documented ~456× skill-token cut vs. loading everything.

---

## The four-stage pipeline

```
 SKILL.md trees ─► gen_catalog.py ─► catalog.json ─► scan_skill_frontmatter.py ─► build_index.py ─► search.py
   (repos +          (walk +           (day-one         (CI SECURITY GATE:          (e5 embeddings     (router
    plugins)          frontmatter)      discoverability   router-hijack/injection)    → pgvector)        entry point)
```

| Stage | Tool | Needs | State on this box |
|---|---|---|---|
| 1. Catalog | `index/gen_catalog.py` | stdlib + PyYAML | ✅ runs — `catalog.json` (418 skills) |
| 2. Security gate | `index/scan_skill_frontmatter.py` | stdlib | ✅ runs — 3 benign flags, 0 attacks |
| 3. Build vectors | `index/build_index.py` | Postgres + pgvector + torch + e5 (~1.1 GB) | ⏳ authored, not run |
| 4. Search | `index/search.py` | same as stage 3 | ⏳ authored, not run |

**Stages 1–2 are the day-one artifact** — a real catalog + a real security posture — and they run
anywhere. Stages 3–4 are the token-cost payoff and need a machine with headroom.

---

## The router contract (how an agent cuts skill-token cost)

The router never loads all skills. It calls `search.py`, gets the top-_k_, and loads **only** the
winner's body — that is the whole savings.

**In-process (preferred):**
```python
from index.search import search
hits = search("summarize a contract's risky clauses", k=3)   # ranked best-first
if hits:
    load_skill(hits[0].path)     # only NOW pay the token cost of one body
```

**Subprocess / JSON (language-agnostic):**
```bash
python index/search.py "<task>" -k 5 --json
```
Stable stdout contract: `{query, k, results:[{id,name,description,pack,repo,path,origin,maturity,
retriever_score,rerank_score,reranked_by}]}`. Exit `0` = results, `2` = no match, `1` = error.
Optional `--pack` / `--maturity` push metadata filters into SQL before ranking. **Guarantee:**
`results[0]` is best by `rerank_score`; a router can threshold on the score and load one body.

---

## Copy-me steps for a new pack (or the whole estate)

1. **Catalog** — add the pack's skill root(s) to the `gen_catalog.py --roots` list.
   - ⚠️ Point roots at **curated skill dirs** (`.claude/skills`, `skills/`), *not* whole repo
     roots — an unpruned `rglob` sweeps `node_modules` and nested vendored repos (Arcanea's root
     rglob finds 1235 SKILL.md vs. ~65 real). Confirm no `node_modules` under a root first.
2. **Normalize** — attribution (`repo`/`pack`/`origin`) is derived from the recorded path and host
   paths are stripped before commit (see `index/_normalize.py`; the catalog goes in a **public**
   repo — never commit absolute `C:\Users\…` paths).
3. **Security gate** — `scan_skill_frontmatter.py --catalog catalog.json --fail-on high`. Triage
   every finding; keep a small **allow-list** of confirmed benign hits (lexical collisions like
   tmux `send-keys`) so a *new* HIGH fails the build while known-benign ones don't chronic-red.
4. **Set status** — flip the pack's `registry.yaml` `indexed`: `done` if it's in the catalog with a
   clean/benign scan; `in-progress` if a HIGH finding is pending allow-list; else `todo`.
5. **Build vectors (later, on a capable box)** — see the exact command below.

---

## Build the full vector index (later)

```bash
export STARLIGHT_DB_URL="postgresql://user:pass@localhost:5432/starlight_skills"
pip install -r index/requirements.txt            # first run only; pulls torch + e5 (~1.1 GB)
createdb starlight_skills
psql "$STARLIGHT_DB_URL" -f index/schema.sql
python index/gen_catalog.py --roots <skill-roots> --out index/catalog.json   # regenerate WITH body_path locally
python index/scan_skill_frontmatter.py --catalog index/catalog.json --json index/security-scan-report.json
python index/build_index.py --catalog index/catalog.json     # incremental by content_hash; --prune to drop stale
python index/search.py "draft a sell-side teaser" -k 5        # smoke test
```

> The committed `index/catalog.json` has `body_path` stripped (host-path hygiene). `build_index.py`
> reads bodies from disk, so **regenerate the catalog locally** (which re-adds `body_path`) before
> building vectors — don't build from the stripped public copy.

---

## Security is first-class here

Skill descriptions are executed by the router *as instructions*. The stage-2 scan is not optional —
it is the defense against the **semantic supply-chain attack class** (arXiv 2605.11418). Every
catalog regen re-runs it; a HIGH finding on a skill not on the allow-list blocks indexing.
