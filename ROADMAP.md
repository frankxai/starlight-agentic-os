# Roadmap — Starlight Agentic OS

Phased **install → improve → index → register** plan. Each phase is sized to fit **one
memory-constrained session**. A phase must leave the repo in a working, committed state — later
phases never destabilize earlier ones.

Legend: 🔲 not started · 🟡 in progress · ✅ done

---

## Phase A — Adopt the tripod + reference stack  🔲

Stand up the sovereign substrate the whole program runs on.

- [ ] Confirm **AGENTS.md** as the canonical memory file across repos; alias `CLAUDE.md` / `GEMINI.md`.
- [ ] Confirm **SKILL.md** convention + `.claude-plugin/plugin.json` semver on at least one pack.
- [ ] Stand up **MCP** author-once → per-CLI config generation for one server.
- [ ] Memory: self-host **Letta** (system of record) + **Mem0 / OpenMemory MCP** (cross-CLI bus).
- [ ] Observability: **OpenLLMetry → self-hosted Langfuse**; enable native Claude Code OTel
      (`CLAUDE_CODE_ENABLE_TELEMETRY=1`).
- **Exit:** one pack demonstrably portable across Claude Code + Codex, with memory + traces flowing.

## Phase B — Populate the registry from real inventory  ✅ (this pass)

- [x] Seed `registry.yaml` from the Phase 1–3 portfolio audits (corrected maxdepth-2 counts).
- [x] Honest current status per pack (most `install=done`; improve/indexed/registered = todo).
- [x] Flag dormant vendored decoration (`claude-flow` doc-shells, 9-line stubs, `swarm-lumina`)
      as `origin=absorbed` / `improve=deprecate-candidate`.
- [x] `gen_readme.py` generates the README status matrix from the registry.
- **Exit:** SSOT exists, README auto-generates, program is legible. **← you are here.**

## Phase C — Wire evals + observability  🔲

- [ ] Add **promptfoo** per-repo CI gate with `skill-used` assertion + thresholds
      (dispatch ≥ 0.85 / trajectory ≥ 0.90 / integration ≥ 0.80).
- [ ] Gate the suite on **skill VERSION bumps** (the version is the contract).
- [ ] Route traces into **Langfuse**; add **Inspect AI** for deeper agentic evals on 1–2 flagships.
- [ ] Promote the first packs from `improve: todo` → `improve: done` once they pass the gate.
- **Exit:** at least the two centers of gravity (FrankX/ACOS, Arcanea) have a passing eval gate;
      `improve=done` count > 0 in the matrix.

## Phase D — Build the pgvector skill index + catalog  🔲

- [ ] Emit `catalog.json` day-one over all indexed skill bodies.
- [ ] Embed with `intfloat/multilingual-e5-base` (768-dim, local) into **Postgres + pgvector**.
- [ ] Two-stage retriever → reranker; wire the semantic router (target the documented 456× token cut).
- [ ] CI scan of skill descriptions/frontmatter (semantic supply-chain attack class).
- [ ] Flip `indexed: todo → done` per pack as it enters the index.
- **Exit:** our own agents can semantically discover skills; `indexed` count climbing.

## Phase E — Register everywhere + CI automation  🔲

- [ ] Official MCP Registry publish (`server.json` + `mcp-publisher`, GitHub-OIDC namespace).
- [ ] Syndicate to Glama / Smithery / mcp.so / PulseMCP.
- [ ] Stand up own Claude Code marketplace repo (`marketplace.json`).
- [ ] Awesome-list PRs (`punkpeye/awesome-mcp-servers`, VoltAgent, `RoggeOhta/awesome-codex-cli`).
- [ ] `syndicate.py` implements publish + **write-back** of `registered:` into `registry.yaml`.
- [ ] `refresh-status.yml` runs the write-back + `gen_readme.py` on schedule.
- **Exit:** first pack `registered:` non-empty and reflected in the matrix without manual edits.

## Phase F — Consolidate guilds / executors  🔲

- [ ] Give every guild a shared **task-lifecycle contract** + observability (not one universal executor).
- [ ] Apply the Phase 3 hardening **within Hermes-scoped repos only**: worktree-per-task,
      no-op detection (never open empty PRs), executor timeout, non-vacuous verify gate, atomic
      cross-machine claim, guaranteed terminal ledger transitions.
- [ ] Deprecate/delete the flagged decoration (grep for references first).
- [ ] Draw the canonical **memory-repo boundary** (second-brain-os vs starlight-memory vs second-brain).
- **Exit:** each guild owns a hardened runtime under a shared contract; dead inventory removed.

---

### Sequencing rule

Never let a later phase's ambition destabilize the tested core. Every phase adds a layer that can
be disabled to fall back to the prior phase. Phases C–E can partially overlap across packs, but a
pack advances one state at a time: **install → improve → indexed → registered**, never skipping.
