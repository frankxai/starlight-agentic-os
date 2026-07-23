# Strategy — Starlight Agentic OS

*The flagship reasoning. This is the document every other file in the repo serves.*

---

## Thesis

Operate the **most sophisticated, portable, and well-evaluated agent-pack + memory stack in the
world** — **sovereign, local-first, observable**. The human sets direction and approves the
irreversible gates; agentic teams (guilds) amplify. Portability is not a nice-to-have: it is the
moat. A pack that runs unchanged across every leading CLI outlives any single vendor's roadmap.

---

## Convergence finding — the portable tripod

The market has quietly converged on **three open standards that every leading CLI already
reads**. This is the single most important strategic fact in the whole program, because it means
we author *once* and run *everywhere* with zero per-CLI rewrites.

- **Memory = `AGENTS.md`.** Adopted across 60k+ repositories and stewarded by the Linux
  Foundation's Agentic AI Foundation (AAIF). `CLAUDE.md` and `GEMINI.md` are aliases to it —
  one memory file, read by all.
- **Skills = `SKILL.md`.** The Agent Skills open standard, honored by ~40 tools and
  **byte-identical across Claude Code, Codex CLI, Gemini CLI, and Cursor**. A skill authored to
  the spec is portable with no translation layer.
- **Tools = `MCP` (Model Context Protocol).** Native in all three major CLIs. Author the server
  once; generate the per-CLI config mechanically.

> **Commitment:** build on the tripod; treat everything else as swappable packaging. When a CLI,
> a memory backend, or a registry shifts, the tripod is the contract that survives.

---

## Reference stack

The specific, sovereign, mostly-self-hostable components chosen for each concern. Each is an
**ADOPT** target tracked in [`ROADMAP.md`](ROADMAP.md) Phase A.

### Memory
- **Letta** (self-hosted) — the **system of record** for agent memory.
- **Mem0 via OpenMemory MCP** — the **shared, local, cross-CLI memory bus** (one memory,
  every CLI reads it over MCP).
- **Graphiti** — temporal knowledge graph, added later when relationship/time queries justify it.

### Observability
- **OpenLLMetry** — instrumentation layer; vendor-neutral OpenTelemetry, so the sink is swappable.
- **Self-hosted Langfuse** (MIT) — the observability **sink**.
- **Native Claude Code OTel** — enable with `CLAUDE_CODE_ENABLE_TELEMETRY=1`; free, first-party.
- **Phoenix** — secondary, for eval-time tracing.

### Evals — *the skill VERSION is the contract*
- **promptfoo** — per-repo **CI gate**, with a `skill-used` assertion and thresholds:
  - dispatch ≥ **0.85**
  - trajectory ≥ **0.90**
  - integration ≥ **0.80**
- **Inspect AI** — deeper agentic evals beyond promptfoo's reach.
- **Gate on version bumps.** A skill's semver **version is the contract**: CI runs the eval suite
  whenever the version changes, so "Improve" status can never regress silently.

### CLIs (the harnesses we target)
- **Claude Code** — primary.
- **Codex CLI** — first-class.
- **Gemini CLI** — legacy target; **watch Antigravity (`agy`)** as its successor.
- **Grok** — via `superagent-ai/grok-cli`; **defer** the official Grok Build (gated beta) until GA.

---

## Portable-pack convention

Every pack follows one directory contract, so any pack is legible to any CLI and to our own
index/registry automation. Modeled on the multi-harness `wshobson/agents` layout. **Semver
everything.**

```
<pack>/
  .claude-plugin/plugin.json     # semver manifest
  AGENTS.md                      # single memory (CLAUDE.md / GEMINI.md alias to it)
  CHANGELOG.md                   # == version == tag (the eval contract boundary)
  skills/
    <skill>/
      SKILL.md                   # router-optimized description (first line = the router's input)
      scripts/  references/  assets/
  agents/                        # subagent definitions
  commands/                      # slash commands
  hooks/                         # lifecycle hooks
  .mcp/server.json               # verified MCP namespace
  pack.meta.yaml                 # provenance: source, license, checksum, indexed, registered[]
```

- **Multi-harness** by construction (the wshobson model) — one pack, many CLIs.
- `pack.meta.yaml` provenance mirrors the fields tracked centrally in [`registry.yaml`](registry.yaml);
  the pack carries its own truth and the command center aggregates it.

---

## Indexed — semantic skill discovery

Our own agents must be able to *find* the right skill without paying to load every skill body
into context. So:

- **Two-stage retrieval:** retriever → reranker, run over the **full skill bodies** (not just the
  one-line descriptions).
- **Embeddings:** `intfloat/multilingual-e5-base` (768-dim, runs **locally** — sovereign, no API).
- **Store:** **Postgres + pgvector**.
- **`catalog.json` day-one** — generate a machine-readable catalog of every indexed skill from
  the start, before the fancy retrieval exists.
- **Payoff:** a semantic router cuts skill-token cost dramatically (documented **456×** reduction
  vs. loading everything) — the difference between an index that scales and a context window that
  doesn't.

**Security — the semantic supply-chain attack class.** Skill descriptions and frontmatter are
*executed as instructions* by the router. A malicious description is a prompt-injection vector.
**Scan skill descriptions and frontmatter in CI** (see `refresh-status.yml`) — this is a distinct
threat class from ordinary dependency scanning and must be treated as first-class.

---

## Registered everywhere

A pack is not shipped until it is discoverable by other operators. Six channels, one automation:

1. **Official MCP Registry** — `server.json` + `mcp-publisher`, GitHub-OIDC-authenticated namespace.
2. **Syndicate** to Glama, Smithery, mcp.so, PulseMCP.
3. **Our own Claude Code marketplace repo** — `marketplace.json`.
4. **Awesome-list PRs** — `punkpeye/awesome-mcp-servers`, VoltAgent, `RoggeOhta/awesome-codex-cli`.
5. **HOL cross-tool aggregator.**
6. **CI automation** that writes the `registered:` field **back into `registry.yaml`** after each
   successful publish — the registry stays honest without manual bookkeeping.

Full checklist and publish contract: [`REGISTER-EVERYWHERE.md`](REGISTER-EVERYWHERE.md).

---

## Hermes scoping (Frank's correction)

The Hermes runtime issues surfaced in the Phase 3 review — the concurrency/worktree wall, the
silent junk-PR path, fail-open gaps — are **contained to Hermes-specific repos/guilds** (a likely
prior-agent error inside *that* runtime). They are **not** a property of the whole fleet. The
other machines are run by their own agentic teams, each owning its own runtime.

> **Treat Hermes as ONE guild/executor among several, not the universal executor.**

The command center tracks **all** guilds; each guild owns and hardens its own runtime. Consolidation
(Phase F in the roadmap) is about giving every guild a shared *contract and observability*, not about
forcing every machine through a single executor. This is the correction that keeps the program
plural and sovereign rather than centralizing a single point of failure.

---

## What this strategy explicitly rejects

- **A single universal executor.** Guilds are plural by design (see above).
- **Reviving claude-flow as the engine.** Keep it as cold-storage reference to mine (hive-mind
  consensus math, SPARC phase discipline); do not wire the whole alpha-external engine.
- **Vendor lock-in at any layer.** Every reference-stack choice is self-hostable or standard-based
  and swappable behind the tripod.
- **Counting activity as progress.** The four lifecycle states — not skill counts — are the metric.
  Most of the estate is `install=done` and nothing further; that gap *is* the work.
