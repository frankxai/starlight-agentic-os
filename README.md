# Starlight Agentic OS

**The command center for Frank's agent-pack program.** Single source of truth for what we
**run**, **build**, **index**, and **register** across every leading agent CLI.

> **Mission** — operate the most sophisticated, well-evaluated, and portable agent-pack +
> memory stack in the world: **sovereign, local-first, observable**. The human sets direction
> and approves; agentic teams (guilds) amplify. Every pack runs unchanged across
> **Claude Code, Codex CLI, Gemini / Antigravity, and Grok**.

This repo does not hold the packs themselves — it **tracks the program**: the strategy, the
registry of every pack, the lifecycle status of each, and the automation that publishes them
to the operator registries.

---

## The one architectural commitment

Everything is built on the **portable tripod** that every leading CLI already reads. Nothing
else is load-bearing:

| Layer | Standard | Why it's the bet |
|---|---|---|
| **Memory** | `AGENTS.md` | 60k+ repos, Linux Foundation AAIF standard. `CLAUDE.md` / `GEMINI.md` alias to it. |
| **Skills** | `SKILL.md` | Agent Skills open standard, ~40 tools, **byte-identical** across Claude Code / Codex / Gemini / Cursor. |
| **Tools** | `MCP` | Native in all leading CLIs. Author the server once, generate per-CLI config. |

**Build on the tripod; everything else is swappable packaging.** If a CLI, a memory backend,
or a registry changes, the tripod is the contract that survives it. See [`STRATEGY.md`](STRATEGY.md).

---

## The four tracked lifecycle states

Every pack in the registry is tracked through four states. A pack is not "done" until it is
**Registered** — present-and-working is only the first of four.

1. **Install** — the pack is *present and working* in at least one CLI.
2. **Improve** — the pack is *hardened to the quality bar*: promptfoo evals in CI, safety
   rails, and provenance (source · license · checksum) recorded.
3. **Indexed** — the pack is *discoverable to our own agents* via the semantic skill index
   (two-stage retriever → reranker over full skill bodies).
4. **Registered** — the pack is *published to the operator registries* (official MCP Registry,
   Glama / Smithery / mcp.so / PulseMCP, our own Claude Code marketplace, and awesome-lists).

The [`registry.yaml`](registry.yaml) is the SSOT. CI (`refresh-status.yml`) writes the
`registered:` field back after each successful publish.

---

## Status matrix

<!-- STATUS-MATRIX:START -->
![packs](https://img.shields.io/badge/packs-27-blue) ![install](https://img.shields.io/badge/install-24%2F27-brightgreen) ![improve](https://img.shields.io/badge/improve-0%2F27-orange) ![indexed](https://img.shields.io/badge/indexed-0%2F27-orange) ![registered](https://img.shields.io/badge/registered-0%2F27-orange) ![deprecate](https://img.shields.io/badge/deprecate-10-yellow)

| Pack | Origin | Ver | Install | Improve | Indexed | Registered |
|---|---|---|:--:|:--:|:--:|---|
| `frankx` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `agentic-creator-os` | original | 12.0.0 | ✅ | 🟡 | ⬜ | ⬜ none |
| `arcanea` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `starlight-intelligence-system` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `hermes` | original | 0.1.0 | ✅ | 🟡 | ⬜ | ⬜ none |
| `starlight-gravity-engine` | original | 0.1.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `app-studio-team` | original | 0.1.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `gencreator-content-team` | original | 0.0.0 | 🟡 | ⬜ | ⬜ | ⬜ none |
| `marine-agent-skills` | original | 0.1.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `prompt-engine` | original | 0.0.0 | 🟡 | ⬜ | ⬜ | ⬜ none |
| `prompt-library` | forked | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `second-brain-os` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `starlight-memory` | original | 0.0.0 | 🟡 | ⬜ | ⬜ | ⬜ none |
| `sentinel` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `global-claude-core` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `v-swarm` | original | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `superpowers` | absorbed | 0.0.0 | ✅ | ⬜ | ⬜ | ⬜ none |
| `claude-flow` | absorbed | 3.5.80 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `swarm-orchestration-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `swarm-advanced-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `hive-mind-advanced-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `sparc-methodology-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `agentic-jujutsu-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `reasoningbank-agentdb-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `model-routing-skill` | absorbed | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `swarm-lumina-skill` | original | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |
| `nine-line-stub-skills` | original | 0.0.0 | ✅ | ⚠️ dep | ⬜ | ⬜ none |

_Legend: ✅ done · 🟡 partial/in-progress · ⬜ todo · ⚠️ dep = deprecate-candidate. 27 packs · 24 installed · 10 flagged for deprecation. Generated from `registry.yaml` by `scripts/gen_readme.py` — do not edit by hand._
<!-- STATUS-MATRIX:END -->

Regenerate with:

```bash
python scripts/gen_readme.py          # rewrite the block above from registry.yaml
python scripts/gen_readme.py --check  # CI gate: fail if the matrix is stale
```

---

## Repo map

| Path | Purpose |
|---|---|
| [`STRATEGY.md`](STRATEGY.md) | The flagship reasoning: thesis, convergence finding, reference stack, conventions. |
| [`ROADMAP.md`](ROADMAP.md) | Phased install → improve → index → register plan (one memory-constrained session per phase). |
| [`registry.yaml`](registry.yaml) | **SSOT** — every pack with honest lifecycle status + provenance. |
| [`PACK-QUALITY-TEMPLATE.md`](PACK-QUALITY-TEMPLATE.md) | The copy-me "Improve" pattern: evals + provenance + observability. Worked on `agentic-creator-os` / `acos-meta`. |
| [`REGISTER-EVERYWHERE.md`](REGISTER-EVERYWHERE.md) | The registries checklist + publish-automation contract. |
| [`docs/ecosystem-research-2026-07.md`](docs/ecosystem-research-2026-07.md) | Mid-2026 ecosystem intelligence digest (INSTALL / ADOPT / MINE / SKIP verdicts). |
| [`scripts/gen_readme.py`](scripts/gen_readme.py) | registry.yaml → README matrix + Shields badges. |
| [`scripts/syndicate.py`](scripts/syndicate.py) | Publish a pack to the registries + write status back (contract defined; publish TODO). |
| `.github/workflows/` | `publish.yml`, `syndicate.yml`, `refresh-status.yml` (stubs with TODOs). |

---

## Guilds, not one universal executor

The program runs across several **guilds** — each an agentic team that owns its own runtime on
its own machine(s). **Hermes is one guild/executor among several**, not the universal executor;
the runtime hardening findings from the Phase 3 review are scoped to Hermes-specific repos, not
the whole fleet. The command center tracks all guilds; each guild owns its runtime. See
[`ROADMAP.md`](ROADMAP.md) Phase F.

---

*Maintained by [frankxai](https://github.com/frankxai). MIT (this repo's tooling; tracked packs
carry their own licenses — see `registry.yaml`).*
