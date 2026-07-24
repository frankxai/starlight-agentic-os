---
name: acos-meta
description: ACOS self-description and portability skill. Documents how the Starlight portable pack works, how to add skills/tools/memory, and how one pack runs identically across Claude Code, Codex, Gemini, and Grok. Use when building new ACOS capabilities, wiring a new CLI, or verifying pack portability.
---

# ACOS Meta (portable exemplar)

This is the reference skill that proves a pack is portable. It ships with the
minimal tripod so `verify-portability.sh` passes and the installer has something
concrete to link.

## The portable tripod
| Leg    | File(s)                     | Rendered/aliased to each CLI |
|--------|-----------------------------|------------------------------|
| Memory | `AGENTS.md`                 | `CLAUDE.md`, Gemini `context.fileName`, Codex/Grok native |
| Skills | `skills/<name>/SKILL.md`    | symlinked into each CLI skills dir |
| Tools  | `mcp/servers.json`          | Claude `.mcp.json`, Gemini `settings.json`, Codex `config.toml` |

## Add a capability
1. Create `skills/<new-name>/SKILL.md` with `name:` + `description:` frontmatter.
2. Keep it lean; put depth in `references/` (progressive disclosure).
3. Run `verify-portability.sh` — it fails CI if frontmatter is malformed.

## Add a tool
1. Edit `mcp/servers.json` (one canonical definition, `mcpServers` object).
2. Re-run `install.sh --pack <this-pack>` to re-render per-CLI configs.

## Wire a new CLI
Add its skills dir + memory alias + MCP target to the installer's target roots.
The four interop moves (see `PORTABLE-PACK-CONVENTION.md`) cover Claude, Codex,
Gemini, and Grok today.

## Verify
```
bash verify-portability.sh ./packs/acos-meta   # exit 0 = portable-clean
```

See `references/portability-notes.md` for the full symlink table and rationale.
