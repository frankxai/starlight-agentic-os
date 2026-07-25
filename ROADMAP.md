# Roadmap — Starlight Agentic OS

Phased **install → improve → index → register** plan. Each phase is sized to fit **one
memory-constrained session**. A phase must leave the repo in a working, committed state — later
phases never destabilize earlier ones.

Legend: 🔲 not started · 🟡 in progress · ✅ done

---

## Phase A — Adopt the tripod + reference stack  🟡

Stand up the sovereign substrate the whole program runs on.

- [x] Confirm **AGENTS.md** as the canonical repository contract here; alias `CLAUDE.md`.
- [x] Confirm **SKILL.md** convention + portable exemplar on at least one pack.
- [x] Stand up **MCP** author-once → per-CLI config generation for one server.
- [ ] Memory: self-host **Letta** (system of record) + **Mem0 / OpenMemory MCP** (cross-CLI bus).
- [ ] Prove a real **OpenLLMetry → Arize Phoenix** trace; retain Langfuse as the optional heavy tier
      and enable native Claude Code OTel (`CLAUDE_CODE_ENABLE_TELEMETRY=1`).
- **Exit:** one pack demonstrably portable across Claude Code + Codex, with memory + traces flowing.

## Phase B — Populate the registry from real inventory  ✅ (this pass)

- [x] Seed `registry.yaml` from the Phase 1–3 portfolio audits (corrected maxdepth-2 counts).
- [x] Honest current status per pack (most `install=done`; improve/indexed/registered = todo).
- [x] Flag dormant vendored decoration (`claude-flow` doc-shells, 9-line stubs, `swarm-lumina`)
      as `origin=absorbed` / `improve=deprecate-candidate`.
- [x] `gen_readme.py` generates the README status matrix from the registry.
- **Exit:** SSOT exists, README auto-generates, program is legible.

## Phase C — Wire evals + observability  🟡

- [ ] Add **promptfoo** per-repo CI gate with `skill-used` assertion + thresholds
      (dispatch ≥ 0.85 / trajectory ≥ 0.90 / integration ≥ 0.80).
- [ ] Gate the suite on **skill VERSION bumps** (the version is the contract).
- [ ] Route traces into **Arize Phoenix** by default (Langfuse optional for team retention); add
      **Inspect AI** for deeper agentic evals on 1–2 flagships.
- [ ] Promote the first packs from `improve: todo` → `improve: done` once they pass the gate.
- **Exit:** at least the two centers of gravity (FrankX/ACOS, Arcanea) have a passing eval gate;
      `improve=done` count > 0 in the matrix.

## Phase D — Build the pgvector skill index + catalog  🟡

- [x] Emit `catalog.json` as a day-one staging inventory over candidate skill bodies.
- [ ] Embed with `intfloat/multilingual-e5-base` (768-dim, local) into **Postgres + pgvector**.
- [ ] Two-stage retriever → reranker; wire the semantic router (target the documented 456× token cut).
- [x] CI scan skill descriptions/frontmatter with exact, content-addressed exceptions.
- [ ] Flip `indexed: todo → done` only after each pack is improved and has a production-index
      receipt. Catalog staging alone does not advance lifecycle state.
- **Exit:** our own agents can semantically discover skills; `indexed` count climbing.

## Phase E — Register everywhere + CI automation  🟡 (scaffolded 2026-07-24)

- [x] **MCP server built + package-validated** — source tests and a clean-install 418-catalog
      wheel receipt pass.
- [ ] Complete the MCP pack's flagship eval, provenance checksum, and live observability receipt
      before promoting `improve: in-progress → done`.
- [x] `server.json` authored + validated (namespace `io.github.frankxai`, repo URL fixed to real repo).
- [x] **Publish sequence authored** in [`REGISTER-PLAYBOOK.md`](REGISTER-PLAYBOOK.md) — the
      one-command-when-ready package (login → publish → syndicate → marketplace → write-back).
- [ ] **Fire it** (needs `mcp-publisher` + network + `frankxai` login): official MCP Registry publish.
- [ ] Syndicate to Glama / Smithery / mcp.so / PulseMCP; awesome-list PRs.
- [ ] Own Claude Code `marketplace.json`.
- [ ] `syndicate.py` implements publish + **write-back** of `registered:` into `registry.yaml`.
- [ ] `refresh-status.yml` runs the write-back + `gen_readme.py` on schedule.
- **Exit:** `starlight-skill-index` `registered:` non-empty and reflected in the matrix without manual edits.

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

Current frontier: the catalog-backed staging router and verification baseline are real; no pack
has completed the governed production-index lifecycle yet. Vector search, live memory, live
observability receipts, external registration, and fleet-wide eval adoption remain incomplete.
The registry—not roadmap prose—decides each pack's state.
