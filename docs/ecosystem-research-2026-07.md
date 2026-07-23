# Ecosystem Research — Mid-2026 Intelligence Digest

**Status:** ✅ POPULATED — four-report corpus, July 2026.
**Purpose:** the standing intelligence picture behind [`STRATEGY.md`](../STRATEGY.md). Every item
carries a real source and a verdict; this is the evidence base, `STRATEGY.md` is the decision layer.

> ### ⚠️ Confidence note — verify on GitHub before betting infrastructure on it
> Star counts throughout are approximate and drift. A few **status claims come from secondary web
> sources, not first-party confirmation**, and must be verified on GitHub / the vendor before any
> infra bet rests on them:
> - **Helicone** reportedly entered *maintenance mode* after the Mintlify acquisition (Mar 2026).
> - **promptfoo** reportedly *acquired by OpenAI* (Mar 2026), said to stay OSS.
> - **Official Grok Build CLI** reportedly a *gated closed beta* (SuperGrok / X-Premium).
> - **Google** reportedly *retired the free Gemini CLI on 2026-06-18* in favor of Antigravity CLI (`agy`).
>
> Treat these four as "true unless GitHub says otherwise." Everything else is directly grounded in
> the linked repos/specs.

**Verdict key** — INSTALL (adopt into a pack / registry now) · ADOPT (bring into the reference
stack / infra) · MINE (extract the idea, don't adopt wholesale) · SKIP (deliberately not pursuing) ·
REGISTER (publish target). Compound verdicts (e.g. INSTALL/MINE) preserved as given.

---

## Report 1 — Claude Code ecosystem

### The six primitives (the mental model everything else plugs into)
| Primitive | What it is |
|---|---|
| **Skills** | what Claude *knows* — `SKILL.md` bodies |
| **Subagents** | isolated workers (separate context windows) |
| **Hooks** | deterministic rails — **12 lifecycle events**; `PreToolUse` **exit-code-2 gating** blocks a tool call |
| **MCP** | the *hands* — external tools/data |
| **CLAUDE.md / memory** | what *persists* across turns |
| **Plugins** | the *distribution box* — note **only `SKILL.md` hot-reloads** |

### Collections
| Name | URL | Verdict | Note |
|---|---|---|---|
| anthropics/skills | github.com/anthropics/skills | **INSTALL** | canonical skill collection |
| obra/superpowers | github.com/obra/superpowers | **INSTALL / MINE** | best workflow methodology |
| wshobson/agents | github.com/wshobson/agents (~36k★) | **ADOPT** | cherry-pick; reference multi-harness pack |
| VoltAgent/awesome-claude-code-subagents | — | **MINE** | taxonomy |
| rohitg00/awesome-claude-code-toolkit | — | **MINE** | discovery |
| hesreallyhim/awesome-claude-code | — | **ADOPT** | curated hub |
| jeremylongshore/claude-code-plugins-plus-skills | — | **MINE** | `ccpi` package-manager idea is good; catalog inflated |

### Marketplaces
| Name | Verdict | Note |
|---|---|---|
| claude-plugins-official | **INSTALL** | source of truth |
| anthropics/claude-plugins-community | **ADOPT** | vetted tier |

### Orchestration
| Name | URL | Verdict | Note |
|---|---|---|---|
| ruvnet/claude-flow | github.com/ruvnet/claude-flow (~31k★, Rust rewrite "Ruflo") | **MINE — don't install** | idea-rich (SPARC / hive-mind / hooks-coordination) but heavyweight, alpha, over-abstracted; "neural" framing is marketing |
| SPARC methodology | (in claude-flow) | **ADOPT as methodology** | encode as our own skill |
| ruv-swarm | — | **MINE** | |

### Hooks
| Name | Verdict | Note |
|---|---|---|
| CodyLunders/claude-code-hooks-library (60+ hooks) | **ADOPT** | best kit |
| disler/claude-code-hooks-mastery | **MINE** | learning |
| ithiria894/awesome-claude-code-hooks | **ADOPT** | security — injection-guard + `PreToolUse` gating |

### MCP registries (Claude-side view)
| Name | Verdict | Note |
|---|---|---|
| Official MCP Registry | **ADOPT** | trust anchor |
| Smithery | **ADOPT** | best DX + hosting |
| mcp.so | **MINE** | broadest |
| punkpeye/awesome-mcp-servers | **MINE** | |

### Memory (Claude-side)
| Name | URL | Verdict | Note |
|---|---|---|---|
| thedotmack/claude-mem | — | **INSTALL / trial** | hooks lifecycle, SQLite + Chroma, `npx claude-mem install`, local-first |
| Mem0 | github.com/mem0ai | **ADOPT** | cross-tool via MCP (OpenMemory = local) |
| Zep | — | **ADOPT** | temporal, selectively |
| Letta / MemGPT | github.com/letta-ai/letta | **MINE / ADOPT** | tiered-memory architecture |
| MemPalace / Cognee / Memvid | — | **MINE** | watch |

### Observability (Claude-side)
| Name | Verdict | Note |
|---|---|---|
| Native OTel (`CLAUDE_CODE_ENABLE_TELEMETRY=1`) | **INSTALL** | foundation |
| SigNoz | **INSTALL** | self-host |
| Langfuse | **INSTALL / ADOPT** | traces + evals |
| Braintrust | **ADOPT** | evals-in-CI |
| Helicone | **SKIP-deep** | ⚠️ reported maintenance mode |
| Latitude | **ADOPT-watch** | issue→PR loop |
| General Analysis OTel+SIEM guide | **MINE** | |

### Skill evals
| Name | Verdict | Note |
|---|---|---|
| Anthropic skill-creator eval harness (EDD) | **INSTALL / ADOPT** | canonical — test prompts, code+model graders, pass@k, A/B, baseline SHA |
| jeremylongshore/j-rig-skill-binary-eval | **ADOPT** | 7-layer binary rubric: package integrity / trigger quality / functional / regression / baseline value / model variance / rollout safety |
| eval-harness skill templates | **MINE** | |

### Implications for the program
- The **primitive model is the design vocabulary**: Skills=knowledge, Subagents=workers, Hooks=rails,
  MCP=hands, memory=persistence, Plugins=box. Every pack we ship maps to these.
- **claude-flow is confirmed MINE-not-INSTALL** — matches the registry's `deprecate-candidate` flag on
  the vendored shells. Extract SPARC + hive-mind consensus; do not wire the engine.
- Hooks + `PreToolUse` exit-2 gating + injection-guard = the security substrate for the semantic
  supply-chain threat (Report 4).

---

## Report 2 — Codex CLI + Gemini CLI + Interoperability

### Codex CLI (github.com/openai/codex, Rust)
- **Memory:** `AGENTS.md` (root → nearest wins, nestable).
- **Config:** `~/.codex/config.toml` + `.codex/config.toml` (TOML).
- **Skills:** `SKILL.md` in `~/.agents/skills` — **identical to Claude**.
- **MCP:** first-class. **Plugins** = skills + MCP + connectors bundle.
- **What Codex needs to shine:** a good root `AGENTS.md` with **exact build/test/verify commands**
  (Codex runs them and self-fixes), 3–6 focused skills, MCP servers, trusted-repo config.

| Name | URL | Verdict | Note |
|---|---|---|---|
| openai/codex | github.com/openai/codex | **INSTALL** | |
| Codex skills docs | developers.openai.com/codex/skills | **ADOPT** | |
| RoggeOhta/awesome-codex-cli (150+) | — | **MINE** | best index |
| ComposioHQ/awesome-codex-skills | — | **MINE** | |
| hashgraph-online/awesome-codex-plugins | — | **MINE-cautious** | |

### ChatGPT surfaces
| Name | Verdict | Note |
|---|---|---|
| OpenAI Agents SDK | **ADOPT-if-hosted** | |
| Assistants API | **SKIP** | deprecated ~Aug 2026 |
| Custom GPTs | **SKIP-for-interop** | |
| Workspace Agents | **SKIP-watch** | |
> Only **MCP + maybe Agents SDK** matter for local interop.

### Gemini CLI (github.com/google-gemini/gemini-cli, ~105k★, Apache-2.0, Gemini 3, 1M ctx)
- **Memory:** `GEMINI.md` but **can read `AGENTS.md`** via `.gemini/settings.json` → `context.fileName`.
- **Config:** `settings.json` (JSON) for MCP. **Subagents:** markdown + YAML in `~/.gemini/agents`.
  **Extensions** = MCP + context + commands bundle.

| Name | URL | Verdict | Note |
|---|---|---|---|
| google-gemini/gemini-cli | github.com/google-gemini/gemini-cli | **INSTALL** | |
| run-gemini-cli GH Action | — | **INSTALL-if-CI** | |
| geminicli.com/extensions | — | **MINE** | |
| ankitmundada/awesome-gemini-cli-subagents | — | **MINE** | |
> **NOTE (from registry research):** Google reportedly retired the free Gemini CLI **2026-06-18** for
> Antigravity CLI **`agy`**. Treat Gemini as **legacy; watch `agy`**.

### Interop standards — *the important part*
| Standard | URL | Verdict | Role |
|---|---|---|---|
| **AGENTS.md** | agents.md (60k+ repos, Linux Foundation AAIF) | **ADOPT** | portable **memory** layer |
| **Agent Skills `SKILL.md`** | agentskills.io (~40 tools) | **ADOPT** | portable **skill** layer |
| **MCP** | modelcontextprotocol.io | **ADOPT** | universal **tool** layer |
| wshobson/agents | github.com/wshobson/agents | **INSTALL / MINE** | reference multi-harness pack |
| alirezarezvani/claude-skills | — | **MINE** | |
| VoltAgent/awesome-agent-skills | — | **MINE-cautious** | |

### The portable pack (interop mechanics)
- `AGENTS.md` = **single memory root** (`ln -s CLAUDE.md`; Gemini `context.fileName`).
- One `skills/` dir of `SKILL.md` **symlinked** into `~/.claude/skills` + `~/.agents/skills` + the
  Gemini path — **byte-identical**.
- **MCP generated from one `servers.json`.** Subagents = markdown + YAML, symlinked.
- Plugins / extensions are **wrapper only**.

### Portability gaps to design around
- Three memory *filenames*, one *content* — the symlink/alias discipline is the whole game.
- Config formats diverge (TOML vs JSON) — generate per-CLI config from one source, never hand-maintain.
- Gemini→`agy` transition is the biggest moving target; keep the Gemini path swappable.

---

## Report 3 — Memory · Observability · Evals · Grok

### Memory
| Name | URL | Verdict | Note |
|---|---|---|---|
| **Letta** | github.com/letta-ai/letta (~23k★) | **INSTALL** | sovereign runtime / **system of record** — context=RAM, archival=disk, agent self-pages |
| **Mem0** | github.com/mem0ai/mem0 (~53k★, v2.0 Apr 2026) | **INSTALL-local** / MINE-cloud | local via **OpenMemory MCP** (Qdrant + Neo4j + Ollama, no cloud) |
| Zep / Graphiti | github.com/getzep/graphiti | **ADOPT** | temporal KG, self-host; **beats Mem0 on LongMemEval 63.8 vs 49.0** (tracks *when* facts were true); ships MCP |
| cognee | github.com/topoteretes/cognee (~28k★) | **ADOPT** | turn many repos into a queryable KG |
| Memori | — | **MINE** | relational |
| Supermemory | — | **SKIP** | thin |
| SuperLocalMemory | — | **MINE** | research |

### Observability
| Name | URL | Verdict | Note |
|---|---|---|---|
| **Langfuse** | github.com/langfuse/langfuse (~28k★, MIT) | **INSTALL** | anchor — self-host free/unlimited but **heavy** (ClickHouse + Postgres + Redis) |
| **OpenLLMetry** | github.com/traceloop/openllmetry (~7k★, Apache) | **INSTALL** | instrumentation — vendor-neutral OTel; **instrument once, portable across sinks** |
| Arize Phoenix | github.com/Arize-ai/phoenix (~9k★, Elastic License) | **ADOPT** | eval deep-dives |
| AgentOps | — | **MINE** | |
| Helicone | github.com/Helicone/helicone (Apache) | **SKIP\*** | ⚠️ reported maintenance mode post-Mintlify (Mar 2026) — **verify** |
| LangSmith | — | **SKIP** | SaaS lock-in |

### Evals
| Name | URL | Verdict | Note |
|---|---|---|---|
| **promptfoo** | github.com/promptfoo/promptfoo | **INSTALL** | native Claude Skill **`skill-used`** assertion; CI gates **SkillDispatchCorrectness ≥ 0.85 / SkillInternalTrajectory ≥ 0.90 / SkillOutputIntegration ≥ 0.80**; failure classes: wrong-skill / trajectory-drift / integration-skip. ⚠️ reported OpenAI-acquired Mar 2026, stays OSS — **verify** |
| **Inspect AI** | github.com/UKGovernmentBEIS/inspect_ai | **INSTALL** | rigorous agent evals — Datasets + Solvers + Scorers |
| DeepEval | github.com/confident-ai/deepeval | **ADOPT** | pytest-style |
| Ragas | — | **ADOPT-if-RAG** | |
| Inspect Evals (200+) | — | **MINE** | |
| Braintrust | — | **MINE** | SaaS |
| OpenAI Evals | — | **MINE** | |

### Grok
| Name | URL | Verdict | Note |
|---|---|---|---|
| Grok Build (CLI) | x.ai/news/grok-build-cli | **SKIP-for-now** | ⚠️ reported beta, SuperGrok / X-Premium-gated, closed; `/goal` autonomous mode |
| superagent-ai/grok-cli | github.com/superagent-ai/grok-cli (~2.3k★, MIT, ~3.3k LOC TS) | **MINE / trial** | X + web search, subagents, Telegram remote — carry as auditable OSS fleet member for the X-search edge |

### Reference-stack decisions (locked)
> **Letta + Mem0/OpenMemory MCP** (memory) · **OpenLLMetry → self-hosted Langfuse** (observability) ·
> **promptfoo per-repo + Inspect AI** (evals) · **grok-cli as fleet member**.
> All OSS + self-hostable, open standards (MCP / OTel / YAML), **skills-as-versioned-contracts**.
- **Graphiti** is the strongest *open* item here (temporal KG, LongMemEval win) — slotted as the
  Phase-later temporal layer in `STRATEGY.md`, consistent with this finding.

---

## Report 4 — Registries + Progress Tracking

> **NOTE:** `gravitypack.yaml` is **NOT** an industry standard. The real manifests are
> `plugin.json` / `marketplace.json` (Claude), `server.json` (MCP Registry), `SKILL.md` frontmatter,
> `AGENTS.md`, and `apm.yml` (Microsoft APM). Our `registry.yaml` is an *internal SSOT*, not a claim
> to a standard.

### MCP registries to register on
| Name | URL | Verdict | Note |
|---|---|---|---|
| **Official MCP Registry** | registry.modelcontextprotocol.io (~9.6k servers) | **REGISTER-primary** | `mcp-publisher` + `server.json`, GitHub-OIDC namespace `io.github.<org>/…` |
| Glama | glama.ai/mcp (~37k metaregistry) | **REGISTER + claim** | |
| Smithery | smithery.ai (~3.3k verified + hosting + Toolbox router) | **REGISTER + ADOPT-router** | |
| mcp.so | mcp.so (~20k) | **REGISTER** | |
| PulseMCP | (~11.8k hand-reviewed) | **REGISTER** | |
| punkpeye/awesome-mcp-servers | — | **REGISTER-PR** | |
> Auto-publish via **Publish MCP Server GH Action + OIDC**.

### Claude marketplaces
| Name | Verdict | Note |
|---|---|---|
| Own repo w/ `.claude-plugin/marketplace.json` | **primary** | `/plugin marketplace add owner/repo` |
| claudepluginhub.com | aggregator | |
| HOL Registry (hol.org/registry/plugins) | aggregator | cross-tool trust scores |

### Exemplar repos to MODEL
| Name | URL | Verdict | Note |
|---|---|---|---|
| anthropics/skills | — | **MINE** | structure, license/provenance split |
| wshobson/agents | — | **ADOPT** | cross-tool packaging |
| VoltAgent/awesome-claude-code-subagents | — | **MINE** | taxonomy + catalog tool |
| microsoft/apm | github.com/microsoft/apm | **ADOPT** | `apm.yml` = package.json for agents — lockfile reproducibility |
| liqiongyu/agentpack | — | **MINE** | declarative control-plane |

### Indexed (semantic skill discovery)
- Names + descriptions **don't scale** → **two-stage retriever → reranker over full skill bodies**
  (arXiv **SkillRouter 2606.03565**).
- Reference stack: **`intfloat/multilingual-e5-base`** (768-dim, local) into **Postgres + pgvector**
  (**ADOPT** — boring, local, reproducible).
- **Semantic router → 456× token cut** (hackernoon). **catalog-as-index day-one** (VoltAgent
  subagent-catalog).
- **WATCH** Graph-of-Skills / SkillPager at >1000 skills.
- **SECURITY:** semantic **supply-chain attack via malicious description** (arXiv **2605.11418**) —
  **scan frontmatter in CI**.

### Tracking
- Dedicated **command-center repo** w/ **README status matrix (Shields badges)** ← *this repo*.
- **GitHub Projects v2** with an Install / Improve / Indexed / Registered **single-select** field.
- **Machine-readable `registry.yaml` as SSOT.**
- **CI generates README + badges** (claude-task-master#838 pattern).
- **CHANGELOG per pack + tags == `plugin.json` version.**
- **`syndicate.py` writes `registered[]` back.**

### Registration automation requirements
- These map 1:1 onto [`REGISTER-EVERYWHERE.md`](../REGISTER-EVERYWHERE.md) and the `syndicate.py`
  write-back contract — the corpus confirms the design, no changes needed.

---

## Consolidated verdict ledger

### 🟢 INSTALL-NOW (adopt into a pack / stand up now)
| Item | Feeds | Source |
|---|---|---|
| anthropics/skills | pack seed | github.com/anthropics/skills |
| obra/superpowers | process skills (already in registry) | github.com/obra/superpowers |
| thedotmack/claude-mem (trial) | memory trial | — |
| openai/codex | Codex CLI target | github.com/openai/codex |
| google-gemini/gemini-cli (legacy; watch `agy`) | Gemini CLI target | github.com/google-gemini/gemini-cli |
| wshobson/agents | reference multi-harness pack | github.com/wshobson/agents |
| **Letta** | memory system-of-record | github.com/letta-ai/letta |
| **Mem0 / OpenMemory MCP** (local) | cross-CLI memory bus | github.com/mem0ai/mem0 |
| Native OTel (`CLAUDE_CODE_ENABLE_TELEMETRY=1`) + SigNoz | observability foundation | — |
| **Langfuse** + **OpenLLMetry** | observability anchor + instrumentation | github.com/langfuse/langfuse · github.com/traceloop/openllmetry |
| **promptfoo** + **Inspect AI** | eval gate | github.com/promptfoo/promptfoo · github.com/UKGovernmentBEIS/inspect_ai |
| Anthropic skill-creator eval harness (EDD) | eval canon | — |

### 🔵 ADOPT (reference stack / infra — ROADMAP A/C/D)
AGENTS.md · SKILL.md · MCP (the tripod) · Graphiti (temporal, later) · cognee · Phoenix · DeepEval ·
Smithery Toolbox router · microsoft/apm (`apm.yml` lockfile) · `intfloat/multilingual-e5-base` +
pgvector · CodyLunders hooks-library · SPARC-as-methodology · anthropics/claude-plugins-community.

### 🟡 MINE (extract the idea only)
claude-flow (SPARC + hive-mind consensus) · ruv-swarm · ccpi package-manager idea · VoltAgent
taxonomy + catalog tool · RoggeOhta/awesome-codex-cli index · superagent-ai/grok-cli (trial as fleet
member) · disler hooks-mastery · General Analysis OTel+SIEM guide · liqiongyu/agentpack.

### 🔴 SKIP (recorded so it isn't re-litigated)
Assistants API (deprecated ~Aug 2026) · Custom GPTs / Workspace Agents (not for interop) ·
Helicone-deep (⚠️ maintenance mode) · LangSmith (SaaS lock-in) · Supermemory (thin) ·
Grok Build official CLI (⚠️ gated closed beta) — **carry grok-cli OSS instead**.

### 🏛️ REGISTER-EVERYWHERE targets (Phase E)
Official MCP Registry (primary, OIDC namespace `io.github.frankxai/…`) · Glama · Smithery · mcp.so ·
PulseMCP · punkpeye/awesome-mcp-servers PR · own `marketplace.json` repo · claudepluginhub · HOL
Registry. Auto-publish via **Publish MCP Server GH Action + OIDC**; `syndicate.py` writes `registered[]`
back. → [`REGISTER-EVERYWHERE.md`](../REGISTER-EVERYWHERE.md).

---

*Corpus captured July 2026. Re-verify the four ⚠️ secondary-source claims (Helicone, promptfoo,
Grok Build, Gemini→agy) on GitHub before any infrastructure bet rests on them.*
