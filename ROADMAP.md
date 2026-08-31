# Roadmap — Starlight Agentic OS

Phased **install → improve → index → register** plan. Each phase is sized to fit **one
memory-constrained session**. A phase must leave the repo in a working, committed state — later
phases never destabilize earlier ones.

Legend: 🔲 not started · 🟡 in progress · ✅ done

---

## Phase A — Adopt the tripod + reference stack  🟡

Stand up the sovereign substrate the whole program runs on.

- [x] Confirm **AGENTS.md** as the canonical repository memory file here.
- [x] Confirm **SKILL.md** convention on the portable `acos-meta` exemplar.
- [x] Stand up one author-once MCP server with documented per-CLI configuration.
- [ ] Propagate the AGENTS/SKILL/MCP contract across governed repositories.
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
- **Exit:** SSOT exists, README auto-generates, program is legible.

## Phase C — Wire evals + observability  🟡

- [x] Author the first **promptfoo** gate with `skill-used` assertion + thresholds
      (dispatch ≥ 0.85 / trajectory ≥ 0.90 / integration ≥ 0.80).
- [ ] Gate the suite on **skill VERSION bumps** (the version is the contract).
- [x] Author sink-neutral OpenLLMetry/OTel configuration with Phoenix as the local default.
- [ ] Execute and evidence the eval and observability paths; add **Inspect AI** for 1–2 flagships.
- [ ] Promote the first packs from `improve: todo` → `improve: done` once they pass the gate.
- **Exit:** at least the two centers of gravity (FrankX/ACOS, Arcanea) have a passing eval gate;
      `improve=done` count > 0 in the matrix.

## Phase D — Build the pgvector skill index + catalog  🟡

- [x] Emit and normalize `catalog.json` over 418 discovered skill bodies.
- [ ] Embed with `intfloat/multilingual-e5-base` (768-dim, local) into **Postgres + pgvector**.
- [x] Author the two-stage retriever → reranker and a deterministic catalog fallback.
- [x] Run the initial skill description/frontmatter supply-chain scan.
- [ ] Certify improve first, then flip `indexed: todo → done` per pack.
- **Exit:** our own agents can semantically discover skills; `indexed` count climbing.

## Phase E — Register everywhere + CI automation  🟡 (scaffolded 2026-07-24)

- [x] **MCP server authored + locally tested** — `mcp-server/starlight-skill-index` (10/10 smoke
      tests, real 418-catalog query verified). Independent certification remains the improve gate.
- [x] `server.json` authored + validated (namespace `io.github.frankxai`, repo URL fixed to real repo).
- [x] **Publish sequence authored** in [`REGISTER-PLAYBOOK.md`](REGISTER-PLAYBOOK.md) — the
      one-command-when-ready package (login → publish → syndicate → marketplace → write-back).
- [ ] **Fire it** (needs `mcp-publisher` + network + `frankxai` login): official MCP Registry publish.
- [ ] Syndicate to Glama / Smithery / mcp.so / PulseMCP; awesome-list PRs.
- [ ] Own Claude Code `marketplace.json`.
- [x] `syndicate.py` emits a read-only plan and refuses mutation.
- [ ] Implement independently reviewed publication and verified **write-back** of `registered:`.
- [ ] Run verified status refresh + `gen_readme.py` only after external inspection.
- **Exit:** `starlight-skill-index` `registered:` non-empty and reflected in the matrix without manual edits.

## Phase F — Consolidate guilds / executors  🔲

- [ ] Give every guild a shared **task-lifecycle contract** + observability (not one universal executor).
- [ ] Apply the Phase 3 hardening **within Hermes-scoped repos only**: worktree-per-task,
      no-op detection (never open empty PRs), executor timeout, non-vacuous verify gate, atomic
      cross-machine claim, guaranteed terminal ledger transitions.
- [ ] Deprecate/delete the flagged decoration (grep for references first).
- [ ] Draw the canonical **memory-repo boundary** (second-brain-os vs starlight-memory vs second-brain).
- **Exit:** each guild owns a hardened runtime under a shared contract; dead inventory removed.

## Release Fabric — official ecosystem drift  🟡 ([#7](https://github.com/frankxai/starlight-agentic-os/issues/7))

- [x] Official source watchlist + changed-only collector (`docs/ECOSYSTEM-DRIFT.md`).
- [x] Weekly Hermes review that feeds one GitHub refinement queue.
- [ ] Daily published-link checks for live releases.
- [ ] Versioned release-pack record in `registry.yaml`.

---

### Sequencing rule

Never let a later phase's ambition destabilize the tested core. Every phase adds a layer that can
be disabled to fall back to the prior phase. Phases C–E can partially overlap across packs, but a
pack advances one state at a time: **install → improve → indexed → registered**, never skipping.
