# Changelog

All notable changes to the Starlight Agentic OS command center. Semver.

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
