# Weekly ecosystem drift check

Status: implemented collector + scheduled review  
Owner: Starlight Agentic OS (lifecycle / syndication)  
Parent: [#7](https://github.com/frankxai/starlight-agentic-os/issues/7)  
Architecture: [SIS PR #120](https://github.com/frankxai/Starlight-Intelligence-System/pull/120) §8 Continuous refinement

## Decision

Do not create another radar, registry, or marketplace source of truth.

Official plugin, MCP, skill, and marketplace docs are watched here. GitHub repository attention remains in `awesome-repo-control-plane`. This loop only answers:

> Did an official host contract, marketplace schema, or submission rule change in a way that should refine Starlight Foundry adapters, evidence, or listings?

## Cadence

| Loop | Who | When |
|---|---|---|
| Collect | `scripts/ecosystem_drift_collect.py` (no LLM) | Every weekly tick, before the agent |
| Review | Hermes job `weekly-ecosystem-drift-check` | Monday 07:00 Europe/Berlin, only if the fingerprint changed |
| Marketplace/status verification for live releases | still open on #7 | daily, not this job |

The first observation is a baseline. Later ticks emit changed-only packets. Transient fetch failures do not wake the agent; two consecutive failures become a coverage gap.

## Sources

Canonical watchlist: [`registry/ecosystem-drift/watchlist.json`](../registry/ecosystem-drift/watchlist.json)

Official surfaces only:

- OpenAI Plugins / Apps SDK / MCP Apps
- Claude Code plugin marketplaces + `anthropics/claude-plugins-official`
- Gemini CLI extensions
- Grok remote MCP + `xai-org/plugin-marketplace`
- Manus custom MCP
- Hermes docs
- MCP spec, registry OpenAPI, MCP Apps
- GitHub Copilot CLI plugins + Copilot MCP
- Agent Skills spec

Community directories are discovery, not authority.

## Local state

Runtime state is **not** git:

```text
%LOCALAPPDATA%/hermes/cache/ecosystem-drift/state.json
%LOCALAPPDATA%/hermes/cache/ecosystem-drift/packet.json
```

Commands:

```bash
python scripts/ecosystem_drift_collect.py --fingerprint
python scripts/ecosystem_drift_collect.py --changed-only
python -m unittest tests.test_ecosystem_drift_collect
```

## Refinement queue

A digest change is not an adoption decision.

The weekly agent:

1. Reads the changed-only packet.
2. Judges materiality against the watchlist (`breaking`, `schema`, `auth`, `submission`, `deprecation`, …).
3. Searches `frankxai/starlight-agentic-os` for an open `[ecosystem-drift]` issue for that source.
4. Opens or comments on **one** issue per material event. Does not open rewrite PRs.
5. Comments on [#7](https://github.com/frankxai/starlight-agentic-os/issues/7) only when at least one material item was queued.
6. Stays silent when the change is chrome, an unchanged fingerprint, or a first baseline.

Human gates remain: credentials, billing, OAuth, legal attestation, marketplace owner submission.

## Non-goals

- Cloning vendor repos
- Auto-installing plugins
- Publishing listings
- Duplicating the GitHub technology radar
- Treating `llms.txt` as pricing/terms authority
