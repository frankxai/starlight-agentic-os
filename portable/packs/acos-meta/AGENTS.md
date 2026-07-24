# AGENTS.md — acos-meta pack (portable memory root)

> Single source of truth for agent memory across **Claude Code, Codex, Gemini, and Grok**.
> Every CLI is aliased to THIS file (Claude via `CLAUDE.md`, Gemini via
> `context.fileName`, Codex/Grok read `AGENTS.md` natively). Edit here, once.

## Identity
- **Program:** Starlight Agentic OS (ACOS) — local-first, sovereign agent stack.
- **Owner:** Frank Riemer (FrankX).
- **Pack:** `acos-meta` — ACOS describing and extending itself.

## Operating principles
1. **Portable tripod:** memory = `AGENTS.md`, skills = `skills/<name>/SKILL.md`,
   tools = `mcp/servers.json`. Nothing CLI-specific lives in the pack body.
2. **Progressive disclosure:** `SKILL.md` stays lean (< ~3k words); depth goes in
   `references/` and is fetched on demand.
3. **Local-first / sovereign:** prefer self-hosted tools and observability sinks;
   no secrets in the repo — only `${PLACEHOLDER}` env references.

## House rules for agents working in this pack
- Treat `AGENTS.md` as authoritative; if a CLI-native memory file disagrees, this wins.
- When adding a capability, add a `skills/<name>/SKILL.md` — do not inline prose here.
- When adding a tool, edit `mcp/servers.json` only; re-run the installer to re-render.
- Observability is on: expect OTel traces (native Claude Code OTel + OpenLLMetry).

## Conventions the fleet must honor
- Skill frontmatter requires `name:` and `description:` (verified in CI).
- MCP server values may use `${PACK_ROOT}`; the installer interpolates it.
- Never commit tokens; reference `${LANGFUSE_*}`, `${OTEL_*}` env vars instead.
