# Changelog

All notable changes to the Starlight Agentic OS command center. Semver.

## [Unreleased]

### Added
- Canonical `AGENTS.md` ownership and truth contract, with `CLAUDE.md` as the harness entry point.
- Fail-closed `scripts/verify_repo.py` repository gate.
- GitHub verification workflow for registry, catalog, security, MCP fallback, compilation, and
  distributable package builds.
- Content-addressed security allowlist plus regression tests. A changed finding invalidates its
  exception; stale or duplicate exceptions fail.
- Generated MCP package assets and a clean-install distribution smoke test, so the wheel remains
  useful without a source-tree `STARLIGHT_CATALOG` override.

### Corrected
- MCP package links now point to the real `starlight-agentic-os/mcp-server` source.
- README and registry now describe Phoenix as the default local observability sink and Langfuse as
  the optional heavier tier.
- Roadmap phase markers now distinguish executed catalog work from unproved vector, memory,
  observability, and publication work.
- Pack lifecycle state now remains sequential: catalog presence is staging evidence, while
  `indexed: done` requires `improve: done`. Six prematurely completed index states were reset.
- `starlight-skill-index` was reset from `improve: done` to `in-progress`; package tests are real,
  while eval, provenance-checksum, and live-observability receipts remain incomplete. CI now
  requires those exact receipt classes before any future `improve: done`.
- The original changelog said publication workflow stubs existed. They are absent from the Git
  tree; this release adds verification only and keeps publication automation closed until the
  syndication implementation is real and independently reviewed.

## [0.6.0] — 2026-07-24

Two architecture fixes + domain inventory.

### Changed — FIX 1: observability without heavy Docker
- **Arize Phoenix is now the default sink** (`pip install arize-phoenix` + `phoenix serve` — one
  process, local SQLite/DuckDB, OTLP at :6006, no ClickHouse/Redis/Postgres/MinIO). Langfuse kept
  as the optional heavy/team tier. Updated `observability/README.md`, `INSTRUMENTATION.md`,
  `otel.env.example` (OTLP endpoint now defaults to Phoenix), and the `STRATEGY.md` reference line.
- Added `observability/phoenix-quickstart.md`.

### Changed — FIX 2: MCP server no longer spawns per-subagent
- `mcp-server/server.py` gains **streamable-HTTP / SSE transport** (`--http`, `STARLIGHT_TRANSPORT`,
  `STARLIGHT_HTTP_HOST/PORT`, default `127.0.0.1:8631/mcp`) so ONE shared long-running service
  serves many clients — no per-subagent process/model duplication. Catalog + ranker warmed once as a
  lazy singleton (`warm_singletons()`); vector model cached in `sys.modules`. **stdio kept** for
  single-user local use.
- Added `mcp-server/deploy/` — shared-service deploy: Windows Task Scheduler `.xml` + systemd user
  unit + `README`. All per-CLI config snippets in `mcp-server/README.md` now point at the shared
  HTTP URL (stdio demoted to a collapsed "alternative"). 8/8 smoke tests still pass.

### Added
- `docs/domain-inventory.md` — authoritative domain → project → repo → status map from the live
  Vercel account (25 custom domains, ~60 projects). **frankx.ai + arcanea.ai homepages flagged
  APPROVED-DO-NOT-TOUCH**; their subpages + all other sites in scope for the audit swarm.
  (Note: the named `production-baseline-2026-07-20.md` was not on disk; Vercel API used as source.)

## [0.5.0] — 2026-07-24

Phase E prep — MCP skill router + portable-pack installer + observability integrated.

### Added
- `mcp-server/` — **`starlight-skill-index`** FastMCP server (search_skills / get_skill / list_packs /
  security_report) with vector→catalog graceful fallback + `server.json` for the official MCP registry
  (namespace `io.github.frankxai`). **8/8 smoke tests pass**; verified against the real 418-skill catalog.
- `portable/` — `install.sh` / `install.ps1` symlinking a pack across `~/.claude/skills`,
  `~/.agents/skills`, `~/.gemini/skills` with `AGENTS.md` aliasing + per-CLI MCP config; the
  `acos-meta` exemplar is **portable-clean (4/4)**; `PORTABLE-PACK-CONVENTION.md`.
- `observability/` — self-host Langfuse `docker-compose` + OpenLLMetry `otel.env.example` +
  `INSTRUMENTATION.md` (authored, not run — secrets via `${VAR:?}` substitution, `CHANGE_ME_*` placeholders).
- `REGISTER-PLAYBOOK.md` — the authored (not run) Phase E publish sequence.
- `registry.yaml` — new pack `starlight-skill-index` (**first `improve=done`**: passing smoke tests +
  validated server.json; publish-ready). `meta` records mcp_server / portable / observability.

### Changed
- `mcp-server/server.json` `repository.url` corrected from `starlight-skill-index` to the real repo
  `starlight-agentic-os` (subfolder `mcp-server`) so the registry can verify it under the namespace.
- README headlines the queryable skill router + portable/observability; ROADMAP Phase E → scaffolded.
- Matrix regenerated (improve column now 1 done; 28 packs).

### Not run (documented)
- MCP publish (`mcp-publisher`), syndication, marketplace, PyPI package, Langfuse/OTel stack, and the
  pgvector vector path — all need network/infra. Fire via `REGISTER-PLAYBOOK.md`.

## [0.4.0] — 2026-07-24

Phase D — semantic skill index (stdlib path executed; vector path authored).

### Added
- `index/` — the semantic-index implementation (schema.sql, build_index.py, search.py,
  scan_skill_frontmatter.py, gen_catalog.py, requirements.txt, README) copied from the specialist
  agent's output, plus `_normalize.py` (attribution + host-path stripping helper).
- `index/catalog.json` — **REAL day-one catalog: 418 skills** deduped from 493 raw, across
  `arcanea` (124), `agentic-creator-os` (104), `.claude/plugins` (126), `frankx` (33),
  `starlight-intelligence-system` (31). Host paths stripped for the public repo.
- `index/security-scan-report.json` + `index/security-scan-summary.md` — **REAL scan: 418 scanned,
  3 flagged (1 high, 2 medium), 0 genuine attacks** (all triaged benign — see summary).
- `PACK-INDEX-TEMPLATE.md` — the copy-me "Indexed" pattern (catalog → scan → build → search).

### Changed
- `registry.yaml` — `indexed` set for catalogued packs: `done` for `agentic-creator-os`, `arcanea`,
  `frankx`, `starlight-intelligence-system`, `app-studio-team`; `in-progress` for `superpowers`
  (benign HIGH false-positive pending CI allow-list). `meta.index` records the catalog. Matrix
  regenerated (indexed column now 5 done + 1 in-progress).
- README repo-map lists `PACK-INDEX-TEMPLATE.md` and `index/`.

### Not run (documented)
- The embedding + pgvector path (`build_index.py` / `search.py` / `schema.sql`) — needs Postgres +
  pip (torch + ~1.1 GB e5 weights). Exact build command in `PACK-INDEX-TEMPLATE.md` and `index/README.md`.

## [0.3.0] — 2026-07-23

Phase C (scoped) — establish the quality-bar template on one exemplar.

### Added
- `PACK-QUALITY-TEMPLATE.md` — the copy-me "Improve" pattern (evals + provenance +
  observability), worked on exemplar pack `agentic-creator-os`, worked skill `acos-meta`.

### Changed
- `registry.yaml` — `agentic-creator-os` `status.improve` → `in-progress` with an `improve_note`
  pointing at its eval config; README matrix regenerated (ACOS now 🟡 in Improve).
- README repo-map lists `PACK-QUALITY-TEMPLATE.md`.

### Companion pack changes (in `frankxai/agentic-creator-os`, branch `phase-c/quality-bar-acos-meta`)
- `evals/promptfooconfig.yaml` — promptfoo skill gate for `acos-meta` (2 positive + 1 negative
  golden cases; dispatch ≥0.85 / trajectory ≥0.90 / integration ≥0.80). Authored, **not executed**.
- `.github/workflows/skill-evals.yml` — runs the gate on skill-version bumps + enforces thresholds.
- `pack.meta.yaml` — provenance + lifecycle + gated-skills.

## [0.2.0] — 2026-07-23

### Added
- `docs/ecosystem-research-2026-07.md` — populated with the full four-report mid-2026 corpus
  (Claude Code ecosystem · Codex+Gemini interop · memory/observability/evals+Grok · registries),
  every NAME—URL—verdict preserved, plus consolidated INSTALL/ADOPT/MINE/SKIP/REGISTER ledgers and
  a confidence note flagging the four secondary-source claims (Helicone maintenance mode, promptfoo
  OpenAI acquisition, official Grok Build beta, Gemini→Antigravity `agy`) to verify on GitHub.

## [0.1.0] — 2026-07-23

Initial scaffold — the command-center charter, strategy, and seeded registry.

### Added
- `README.md` — command-center charter, the tripod commitment, the four lifecycle states,
  auto-generated status-matrix block.
- `STRATEGY.md` — flagship reasoning: thesis, convergence finding (AGENTS.md / SKILL.md / MCP),
  reference stack (Letta · Mem0 · OpenLLMetry · Langfuse · promptfoo · pgvector), portable-pack
  convention, indexed/registered plan, Hermes-as-one-guild scoping.
- `registry.yaml` — SSOT seeded from the Phase 1–3 portfolio audits (corrected maxdepth-2 counts);
  27 packs with honest lifecycle status; dormant vendored decoration flagged as deprecate-candidates.
- `ROADMAP.md` — Phases A–F, one memory-constrained session each.
- `REGISTER-EVERYWHERE.md` — six-channel registry checklist + publish/write-back contract.
- `docs/ecosystem-research-2026-07.md` — scaffold awaiting the four-report corpus.
- `scripts/gen_readme.py` — registry.yaml → README matrix + Shields badges (CI `--check` mode).
- `scripts/syndicate.py` — publish + write-back contract (stub; publish steps TODO).
- `.github/workflows/{publish,syndicate,refresh-status}.yml` — automation stubs with TODOs.
- `LICENSE` (MIT), `.gitignore`.

[0.1.0]: https://github.com/frankxai/starlight-agentic-os/releases/tag/v0.1.0
